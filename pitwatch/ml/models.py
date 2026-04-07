from django.conf import settings
from django.db import models


class InferenceJob(models.Model):
	STATUS_QUEUED = "queued"
	STATUS_RUNNING = "running"
	STATUS_SUCCESS = "success"
	STATUS_FAILED = "failed"

	STATUS_CHOICES = [
		(STATUS_QUEUED, "Queued"),
		(STATUS_RUNNING, "Running"),
		(STATUS_SUCCESS, "Success"),
		(STATUS_FAILED, "Failed"),
	]

	task_id = models.CharField(max_length=255, unique=True)
	submitted_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="inference_jobs",
		null=True,
		blank=True,
	)
	image_name = models.CharField(max_length=255, blank=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED)
	pothole = models.BooleanField(null=True, blank=True)
	confidence = models.FloatField(null=True, blank=True)
	error_message = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]
		indexes = [
			models.Index(fields=["status"]),
			models.Index(fields=["submitted_by", "status"]),
			models.Index(fields=["created_at"]),
		]

	def __str__(self):
		return f"InferenceJob(task_id={self.task_id}, status={self.status})"


class PotholeReport(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="pothole_reports",
	)
	task_id = models.CharField(max_length=255, unique=True)
	image_name = models.CharField(max_length=255, blank=True)
	confidence = models.FloatField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at"]
		indexes = [
			models.Index(fields=["user", "created_at"]),
		]

	def __str__(self):
		return f"PotholeReport(task_id={self.task_id}, user={self.user_id})"
