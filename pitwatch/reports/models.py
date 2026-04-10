from django.conf import settings
from django.db import models


class Report(models.Model):
    STATUS_PENDING = "pending"
    STATUS_RESOLVED = "resolved"
    STATUS_REJECTED = "rejected"
    STATUS_IN_PROGRESS = "in_progress"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RESOLVED, "Resolved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_IN_PROGRESS, "In Progress"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["latitude", "longitude"]),
            models.Index(fields=["resolved_at"]),
        ]


    def __str__(self):
        return self.title