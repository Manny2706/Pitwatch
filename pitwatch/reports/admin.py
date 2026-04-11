from django.contrib import admin

from .models import Report

# allow admins to view and manage reports in the admin interface, and edit report details, including status and severity. This helps admins efficiently track and resolve pothole reports.
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
	list_display = (
		"id",
		"title",
		"user",
		"status",
		"latitude",
		"longitude",
		"created_at",
		"resolved_at",
		"road_authority",
		"road_authority_email",
		"pothole_severity",
  
	)
	list_filter = ("status", "created_at", "resolved_at")
	search_fields = ("title", "description", "user__username", "user__email")
	ordering = ("-created_at",)
	raw_id_fields = ("user",)
	editable_fields = ("status", "pothole_severity", "road_authority", "road_authority_email")
