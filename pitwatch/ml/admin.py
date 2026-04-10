from django.contrib import admin

from .models import InferenceJob, PotholeReport


@admin.register(InferenceJob)
class InferenceJobAdmin(admin.ModelAdmin):
	list_display = (
		"task_id",
		"submitted_by",
		"status",
		"pothole",
		"confidence",
		"image_name",
		"created_at",
		"updated_at",
	)
	list_filter = ("status", "created_at", "updated_at")
	search_fields = ("task_id", "image_name", "submitted_by__username", "submitted_by__email")
	ordering = ("-created_at",)
	raw_id_fields = ("submitted_by",)


@admin.register(PotholeReport)
class PotholeReportAdmin(admin.ModelAdmin):
	list_display = ("task_id", "user", "confidence", "image_name", "created_at")
	list_filter = ("created_at",)
	search_fields = ("task_id", "image_name", "user__username", "user__email")
	ordering = ("-created_at",)
	raw_id_fields = ("user",)
