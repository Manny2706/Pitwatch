from django.contrib import admin
from django.urls import include, path

from dashboard.views import DashboardSummaryView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/<str:version>/accounts/", include("accounts.urls")),
    path("api/<str:version>/reports/", include("reports.urls")),
    path("api/<str:version>/dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
]