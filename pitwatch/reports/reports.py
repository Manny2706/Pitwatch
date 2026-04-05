from celery import shared_task
from django.utils import timezone

from .models import Report


@shared_task(ignore_result=True)
def auto_reject_old_reports(days=30):
    cutoff = timezone.now() - timezone.timedelta(days=days)
    return Report.objects.filter(
        status=Report.STATUS_PENDING,
        created_at__lt=cutoff,
    ).update(status=Report.STATUS_REJECTED)