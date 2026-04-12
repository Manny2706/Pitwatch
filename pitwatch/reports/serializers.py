from rest_framework import serializers

from pitwatch.reports.models import Report
from .views import get_cluster_metadata
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
