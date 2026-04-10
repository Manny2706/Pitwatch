from django.core.cache import cache
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken

from accounts.authentication import CookieJWTAuthentication
from reports.models import Report

class DashboardSummaryView(APIView):
    permission_classes = [AllowAny]

    def _authenticate_from_header(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return None, Response(
                {"detail": "Authorization header missing or invalid."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        raw_token = auth_header.split(" ", 1)[1].strip()
        authenticator = CookieJWTAuthentication()

        try:
            validated_token = authenticator.get_validated_token(raw_token)
            user = authenticator.get_user(validated_token)
        except (InvalidToken, AuthenticationFailed):
            return None, Response(
                {"detail": "Invalid or expired access token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return user, None

    def get(self, request, version=None):
        user, error_response = self._authenticate_from_header(request)
        if error_response:
            return error_response

        if not user.is_superuser:
            return Response(
                {"detail": "Unauthorized. Superuser access required."},
                status=status.HTTP_403_FORBIDDEN,
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