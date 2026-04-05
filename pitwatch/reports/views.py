from django.db import connection
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ["id", "title", "description", "status", "latitude", "longitude", "created_at"]
        read_only_fields = ["id", "created_at"]


class ReportListCreateView(APIView):
    def get(self, request, version=None):
        qs = Report.objects.all().order_by("-created_at")
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
        report = serializer.save()
        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)


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
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                ORDER BY distance_m
                LIMIT %s
            """
            params = [lng, lat, limit]
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
                  AND ST_DWithin(
                      ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography,
                      ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                      %s
                  )
                ORDER BY distance_m
                LIMIT %s
            """
            params = [lng, lat, lng, lat, radius_m, limit]

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