from django.urls import path

from .views import NearbyReportsView, ReportListCreateView

urlpatterns = [
    path("", ReportListCreateView.as_view(), name="reports-list-create"),
    path("nearby/", NearbyReportsView.as_view(), name="reports-nearby"),
]