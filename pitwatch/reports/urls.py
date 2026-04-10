from django.urls import path

from .views import AdminReportListView, NearbyReportsView, ReportListCreateView, ReportStatusUpdateView, GetCount

urlpatterns = [
    path("", ReportListCreateView.as_view(), name="reports-list-create"),
    path("counts/", GetCount.as_view(), name="reports-counts"),
    path("admin/all/", AdminReportListView.as_view(), name="reports-admin-all"),
    path("nearby/", NearbyReportsView.as_view(), name="reports-nearby"),
    path("<int:report_id>/status/", ReportStatusUpdateView.as_view(), name="reports-status-update"),
]