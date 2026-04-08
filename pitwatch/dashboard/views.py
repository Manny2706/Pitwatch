from django.core.cache import cache
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import CookieJWTAuthentication
from reports.models import Report


class CookieOnlyJWTAuthentication(CookieJWTAuthentication):
    def authenticate(self, request):
        raw_token = request.COOKIES.get("access_token")
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token


class DashboardSummaryView(APIView):
    authentication_classes = [CookieOnlyJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, version=None):
        if not request.user.is_superuser:
            return Response(
                {"detail": "Unauthorized. Superuser access required."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

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