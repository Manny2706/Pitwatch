from django.db import connection
from django.db.models import Count
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ["id", "user", "title", "description", "status", "latitude", "longitude", "created_at","resolved_at"]
        read_only_fields = ["id", "user", "created_at"]


class AdminReportSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = ["id", "user", "title", "description", "status", "latitude", "longitude", "created_at"]

    def get_user(self, obj):
        if not obj.user:
            return None
        return {
            "id": obj.user_id,
            "username": obj.user.username,
            "email": obj.user.email,
            "is_staff": obj.user.is_staff,
        }


class ReportListCreateView(APIView):
    def get(self, request, version=None):
        qs = Report.objects.exclude(status=Report.STATUS_REJECTED).filter(user=request.user).order_by("-created_at")
        page_size = int(request.query_params.get("page_size", 25))
        page = int(request.query_params.get("page", 1))
        start = (page - 1) * page_size
        end = start + page_size

        total = qs.count()
        items = qs[start:end]
        data = ReportSerializer(items, many=True).data
        return Response(
            {
                "count": total,
                "page": page,
                "page_size": page_size,
                "results": data,
            }
        )

    def post(self, request, version=None):
        serializer = ReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = serializer.save(user=request.user)
        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)


class AdminReportListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, version=None):
        page_size_raw = request.query_params.get("page_size", 25)
        page_raw = request.query_params.get("page", 1)

        try:
            page_size = max(1, min(int(page_size_raw), 100))
            page = max(1, int(page_raw))
        except ValueError:
            return Response(
                {"detail": "page and page_size must be valid integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = Report.objects.select_related("user").all().order_by("-created_at")
        start = (page - 1) * page_size
        end = start + page_size

        total = qs.count()
        items = qs[start:end]
        data = AdminReportSerializer(items, many=True).data
        return Response(
            {
                "count": total,
                "page": page,
                "page_size": page_size,
                "results": data,
            },
            status=status.HTTP_200_OK,
        )


class NearbyReportsView(APIView):
    def get(self, request, version=None):
        lat_raw = request.query_params.get("lat")
        lng_raw = request.query_params.get("lng")
        radius_km_raw = request.query_params.get("radius_km")
        limit_raw = request.query_params.get("limit", "10")

        if lat_raw is None or lng_raw is None:
            return Response({"detail": "lat and lng are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            lat = float(lat_raw)
            lng = float(lng_raw)
            limit = max(1, min(int(limit_raw), 100))
            radius_km = float(radius_km_raw) if radius_km_raw is not None else None
        except ValueError:
            return Response({"detail": "Invalid numeric params."}, status=status.HTTP_400_BAD_REQUEST)

        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            return Response({"detail": "lat/lng out of range."}, status=status.HTTP_400_BAD_REQUEST)

        if radius_km is None:
            query = """
                SELECT id, title, status, created_at,
                       ST_Distance(
                           ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography,
                           ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                       ) AS distance_m
                FROM reports_report
                WHERE latitude IS NOT NULL
                  AND longitude IS NOT NULL
                  AND status <> %s
                ORDER BY distance_m
                LIMIT %s
            """
            params = [lng, lat, Report.STATUS_REJECTED, limit]
        else:
            radius_m = radius_km * 1000
            query = """
                SELECT id, title, status, created_at,
                       ST_Distance(
                           ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography,
                           ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                       ) AS distance_m
                FROM reports_report
                WHERE latitude IS NOT NULL
                  AND longitude IS NOT NULL
                  AND status <> %s
                  AND ST_DWithin(
                      ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography,
                      ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                      %s
                  )
                ORDER BY distance_m
                LIMIT %s
            """
            params = [lng, lat, Report.STATUS_REJECTED, lng, lat, radius_m, limit]

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        data = [
            {
                "id": r[0],
                "title": r[1],
                "status": r[2],
                "created_at": r[3],
                "distance_m": float(r[4]),
            }
            for r in rows
        ]
        return Response(data, status=status.HTTP_200_OK)


class ReportStatusUpdateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, report_id, version=None):
        if not request.user.is_superuser:
            return Response(
                {"detail": "Unauthorized. Superuser access required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        report = Report.objects.filter(id=report_id).first()
        if not report:
            return Response({"detail": "Report not found."}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get("status")
        if not new_status:
            return Response({"detail": "status is required."}, status=status.HTTP_400_BAD_REQUEST)

        allowed_statuses = [choice[0] for choice in Report.STATUS_CHOICES]
        if new_status not in allowed_statuses:
            return Response(
                {
                    "detail": "Invalid status.",
                    "allowed_statuses": allowed_statuses,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        report.status = new_status
        
        if new_status == Report.STATUS_RESOLVED:
            report.resolved_at = timezone.now()
        else:
            report.resolved_at = None
        report.save(update_fields=["status", "resolved_at"])
        return Response(ReportSerializer(report).data, status=status.HTTP_200_OK)


class GetCount(APIView):
    # This endpoint is for the users to get counts of reports by status by them self
    permission_classes = [AllowAny]

    def get(self, request, version=None):
        qs = Report.objects.all()
        if request.user.is_authenticated:
            qs = qs.filter(user=request.user)

        counts = qs.values("status").annotate(count=Count("id"))
        data = {item["status"]: item["count"] for item in counts}
        return Response(data, status=status.HTTP_200_OK)    