import logging
import os

from django.db import connection
from django.db.models import Count
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Report
from .utils.road_authority import get_road_authority, send_authority_notification, send_emergency_notification

logger = logging.getLogger(__name__)

POTHOLE_CLUSTER_RADIUS_METERS = int(os.getenv("POTHOLE_CLUSTER_RADIUS_METERS", "130"))
POTHOLE_CLUSTER_THRESHOLD = int(os.getenv("POTHOLE_CLUSTER_THRESHOLD", "8"))


def get_report_within_distance(latitude, longitude, meters=10):
    if latitude is None or longitude is None:
        return None

    query = """
        SELECT id
        FROM reports_report
        WHERE latitude IS NOT NULL
          AND longitude IS NOT NULL
          AND ST_DWithin(
              ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography,
              ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
              %s
          )
        ORDER BY created_at DESC
        LIMIT 1
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [longitude, latitude, meters])
        row = cursor.fetchone()

    if not row:
        return None

    return Report.objects.filter(id=row[0]).first()


def get_pothole_cluster_count(latitude, longitude, meters=POTHOLE_CLUSTER_RADIUS_METERS):
    if latitude is None or longitude is None:
        return 0

    query = """
        SELECT COUNT(*)
        FROM reports_report
        WHERE latitude IS NOT NULL
          AND longitude IS NOT NULL
          AND status <> %s
          AND ST_DWithin(
              ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography,
              ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
              %s
          )
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [Report.STATUS_REJECTED, longitude, latitude, meters])
        row = cursor.fetchone()

    return int(row[0]) if row and row[0] is not None else 0


def get_cluster_metadata(report):
    metadata = getattr(report, "_cluster_metadata", None)
    if metadata is None:
        cluster_count = get_pothole_cluster_count(report.latitude, report.longitude)
        is_high_severity = cluster_count > POTHOLE_CLUSTER_THRESHOLD
        metadata = {
            "cluster_count": cluster_count,
            "cluster_severity": "high" if is_high_severity else "normal",
            "is_high_severity": is_high_severity,
        }
        report._cluster_metadata = metadata
    return metadata


def is_within_radius(lat1, lng1, lat2, lng2, meters):
    query = """
        SELECT ST_DWithin(
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
            %s
        )
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [lng1, lat1, lng2, lat2, meters])
        row = cursor.fetchone()
    return bool(row and row[0])


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            "id",
            "user",
            "title",
            "description",
            "status",
            "latitude",
            "longitude",
            "road_authority",
            "road_authority_email",
            "created_at",
            "resolved_at",
            "road_authority",
            "road_authority_email",
            "pothole_severity",
        ]
        read_only_fields = ["id", "user", "created_at"]


class AdminReportSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    cluster_count = serializers.SerializerMethodField()
    cluster_severity = serializers.SerializerMethodField()
    is_high_severity = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            "id",
            "user",
            "title",
            "description",
            "status",
            "latitude",
            "longitude",
            "road_authority",
            "road_authority_email",
            "created_at",
            "cluster_count",
            "cluster_severity",
            "is_high_severity",
            "pothole_severity",
        ]

    def get_user(self, obj):
        if not obj.user:
            return None
        return {
            "id": obj.user_id,
            "username": obj.user.username,
            "email": obj.user.email,
            "is_staff": obj.user.is_staff,
        }

    def get_cluster_count(self, obj):
        return get_cluster_metadata(obj)["cluster_count"]

    def get_cluster_severity(self, obj):
        return get_cluster_metadata(obj)["cluster_severity"]

    def get_is_high_severity(self, obj):
        return get_cluster_metadata(obj)["is_high_severity"]


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

        latitude = serializer.validated_data.get("latitude")
        longitude = serializer.validated_data.get("longitude")
        existing_report = get_report_within_distance(latitude, longitude, meters=10)
        if existing_report:
            return Response(
                {
                    "detail": "A report already exists within 10 meters of this location.",
                    "report": ReportSerializer(existing_report).data,
                    
                },
                status=status.HTTP_200_OK,
            )

        road_authority_data = get_road_authority(latitude, longitude)
        report = serializer.save(
            user=request.user,
            road_authority=road_authority_data.get("authority"),
            road_authority_email=road_authority_data.get("authority_email"),
        )

        notification_sent = False
        try:
            notification_sent = bool(send_authority_notification(report, road_authority_data))
        except Exception:
            logger.exception("Failed to send pothole report notification for report_id=%s", report.id)

        response_data = ReportSerializer(report).data
        response_data["notification_sent"] = notification_sent
        return Response(response_data, status=status.HTTP_201_CREATED)


class AdminReportListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, version=None):
        if not request.user.is_superuser:
            return Response(
                {"detail": "Unauthorized. Superuser access required."},
                status=status.HTTP_403_FORBIDDEN,
            )
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

        reports = list(Report.objects.select_related("user").all().order_by("-created_at"))
        normal_reports = []
        high_severity_reports = []

        for report in reports:
            metadata = get_cluster_metadata(report)
            if metadata["is_high_severity"]:
                high_severity_reports.append(report)
            else:
                normal_reports.append(report)

        start = (page - 1) * page_size
        end = start + page_size

        total_count = len(reports)
        normal_count = len(normal_reports)
        unique_high_severity_zones = []

        for report in high_severity_reports:
            if report.latitude is None or report.longitude is None:
                continue

            is_duplicate_zone = False
            for zone in unique_high_severity_zones:
                if is_within_radius(
                    report.latitude,
                    report.longitude,
                    zone["latitude"],
                    zone["longitude"],
                    POTHOLE_CLUSTER_RADIUS_METERS,
                ):
                    is_duplicate_zone = True
                    break

            if not is_duplicate_zone:
                zone_cluster_count = get_pothole_cluster_count(report.latitude, report.longitude)
                unique_high_severity_zones.append(
                    {
                        "latitude": report.latitude,
                        "longitude": report.longitude,
                        "pothole_count": zone_cluster_count,
                    }
                )

        high_severity_count = len(unique_high_severity_zones)

        items = normal_reports[start:end]
        data = AdminReportSerializer(items, many=True).data
        return Response(
            {
                "count": normal_count,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "results": data,
                "high_severity_count": high_severity_count,
                "high_severity_zones": unique_high_severity_zones,
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

        cluster_count = get_pothole_cluster_count(lat, lng)
        if cluster_count > POTHOLE_CLUSTER_THRESHOLD:
            warning = "High"
        elif cluster_count > 0:
            warning = "Moderate"
        else:
            warning = "None"
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
        return Response(
            {
                "warning": warning,
                "cluster_count": cluster_count,
                "threshold": POTHOLE_CLUSTER_THRESHOLD,
                "results": data,
            },
            status=status.HTTP_200_OK,
        )


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
    
class EmergencyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, version=None):
        access_token = request.data.get("access_token")
        recipient_mail = (
            request.data.get("recipient_email")
            or request.data.get("recipient_mail")
            or request.data.get("email")
            or ""
        )
        recipient_mail = str(recipient_mail).strip()
        if access_token:
            jwt_authenticator = JWTAuthentication()
            try:
                validated_token = jwt_authenticator.get_validated_token(access_token)
                user = jwt_authenticator.get_user(validated_token)
            except Exception:
                user = None
        else:
            user = None

        latitude_raw = request.data.get("latitude")
        longitude_raw = request.data.get("longitude")
        title = request.data.get("title", "Emergency Report") or "Emergency Report"
        description = request.data.get("description", "Emergency report") or "Emergency report"

        if latitude_raw is None or longitude_raw is None:
            return Response({"detail": "latitude and longitude are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            latitude = float(latitude_raw)
            longitude = float(longitude_raw)
        except (TypeError, ValueError):
            return Response({"detail": "latitude and longitude must be valid numbers."}, status=status.HTTP_400_BAD_REQUEST)

        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            return Response({"detail": "latitude/longitude out of range."}, status=status.HTTP_400_BAD_REQUEST)

        if recipient_mail:
            try:
                validate_email(recipient_mail)
            except ValidationError:
                return Response({"detail": "recipient_email is invalid."}, status=status.HTTP_400_BAD_REQUEST)

        # Build a transient report object for notification payload only.
        report = Report(
            user=user,
            title=title,
            description=description,
            status=Report.STATUS_PENDING,
            latitude=latitude,
            longitude=longitude,
            road_authority="Emergency Contact",
            road_authority_email=recipient_mail or None,
        )
        report.created_at = timezone.now()

        notification_sent = False
        notification_error = None
        # Send mail to recipient if provided with location/details.
        if recipient_mail:
            authority_data = {
                "authority": "Emergency Contact",
                "authority_email": recipient_mail,
                "city": "N/A",
                "tags": {},
            }
            try:
                notification_sent = bool(send_emergency_notification(report, authority_data))
                if not notification_sent:
                    notification_error = (
                        "Notification was not sent. Check BREVO_API_KEY and BREVO_SENDER_EMAIL configuration."
                    )
            except Exception as exc:
                notification_error = str(exc)
                logger.exception("Failed to send emergency notification")
        else:
            notification_error = "Notification was not sent because recipient_email was not provided."

        response_data = {
            "title": report.title,
            "description": report.description,
            "status": report.status,
            "latitude": report.latitude,
            "longitude": report.longitude,
            "recipient_email": recipient_mail,
            "notification_sent": notification_sent,
            "saved": False,
        }
        if notification_error:
            response_data["notification_error"] = notification_error
            response_data["notification_message"] = "Emergency report accepted, but notification failed."
        elif notification_sent:
            response_data["notification_message"] = "Emergency notification sent successfully."
        return Response(response_data, status=status.HTTP_200_OK)