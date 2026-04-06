from django.core.cache import cache
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from reports.models import Report


class DashboardSummaryView(APIView):
    def get(self, request, version=None):
        cache_key = "dashboard:summary:v1"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        totals = Report.objects.aggregate(
            total_reports=Count("id"),
            resolved=Count("id", filter=Q(status=Report.STATUS_RESOLVED)),
            pending=Count("id", filter=Q(status=Report.STATUS_PENDING)),
            rejected=Count("id", filter=Q(status=Report.STATUS_REJECTED)),
        )

        since = timezone.now() - timezone.timedelta(days=7)
        daily_qs = (
            Report.objects.filter(created_at__gte=since)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        payload = {
            "totals": totals,
            "trend_last_7_days": list(daily_qs),
        }
        cache.set(cache_key, payload, 300)
        return Response(payload)