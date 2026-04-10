from django.contrib import admin

from .models import Report


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
	)
	list_filter = ("status", "created_at", "resolved_at")
	search_fields = ("title", "description", "user__username", "user__email")
	ordering = ("-created_at",)
	raw_id_fields = ("user",)
