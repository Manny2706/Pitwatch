from django.urls import path

from .views import detect_pothole, detect_status, my_pothole_reports, submit_detect_pothole

urlpatterns = [
    path("detect/", detect_pothole, name="ml-detect-pothole"),
    path("detect/submit/", submit_detect_pothole, name="ml-detect-submit"),
    path("detect/status/<str:task_id>/", detect_status, name="ml-detect-status"),
    path("detect/my-reports/", my_pothole_reports, name="ml-my-pothole-reports"),
]
