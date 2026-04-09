import base64

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from reports.models import Report

from .models import InferenceJob
from .services.model import InvalidImageError, PredictionError, predict_from_file
from .tasks import run_pothole_inference


@api_view(["POST"])
@permission_classes([AllowAny])
def detect_pothole(request, version=None):
    image_file = request.FILES.get("image")
    if not image_file:
        return Response({"error": "No image uploaded"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        probability = predict_from_file(image_file)
    except InvalidImageError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except PredictionError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(
        {
            "pothole": probability > 0.5,
            "confidence": probability,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_detect_pothole(request, version=None):
    image_file = request.FILES.get("image")
    if not image_file:
        return Response({"error": "No image uploaded"}, status=status.HTTP_400_BAD_REQUEST)

    lat_raw = request.data.get("lat", request.data.get("latitude"))
    lng_raw = request.data.get("lng", request.data.get("longitude"))

    latitude = None
    longitude = None
    if lat_raw not in (None, ""):
        try:
            latitude = float(lat_raw)
        except (TypeError, ValueError):
            return Response({"error": "Invalid lat/latitude"}, status=status.HTTP_400_BAD_REQUEST)

    if lng_raw not in (None, ""):
        try:
            longitude = float(lng_raw)
        except (TypeError, ValueError):
            return Response({"error": "Invalid lng/longitude"}, status=status.HTTP_400_BAD_REQUEST)

    if latitude is not None and not (-90 <= latitude <= 90):
        return Response({"error": "Latitude out of range"}, status=status.HTTP_400_BAD_REQUEST)
    if longitude is not None and not (-180 <= longitude <= 180):
        return Response({"error": "Longitude out of range"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        image_bytes = image_file.read()
        image_b64 = base64.b64encode(image_bytes).decode("ascii")
        task = run_pothole_inference.delay(image_b64, latitude, longitude)
        InferenceJob.objects.create(
            task_id=task.id,
            submitted_by=request.user,
            image_name=image_file.name or "",
            status=InferenceJob.STATUS_QUEUED,
        )
    except Exception as exc:
        return Response({"error": f"Failed to queue task: {exc}"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(
        {
            "status": "queued",
            "task_id": task.id,
            "message": "Image received",
        },
        status=status.HTTP_202_ACCEPTED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def detect_status(request, task_id, version=None):
    job = InferenceJob.objects.filter(task_id=task_id, submitted_by=request.user).first()
    if not job:
        return Response({"error": "Task not found", "task_id": task_id}, status=status.HTTP_404_NOT_FOUND)

    payload = {
        "task_id": task_id,
        "status": job.status,
        "image_name": job.image_name,
    }

    if job.status == InferenceJob.STATUS_SUCCESS:
        payload["result"] = {
            "pothole": job.pothole,
            "confidence": job.confidence,
        }
    elif job.status == InferenceJob.STATUS_FAILED:
        payload["error"] = job.error_message

    return Response(payload, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_pothole_reports(request, version=None):
    reports = Report.objects.filter(user=request.user).order_by("-created_at")
    data = [
        {
            "id": report.id,
            "title": report.title,
            "description": report.description,
            "status": report.status,
            "latitude": report.latitude,
            "longitude": report.longitude,
            "created_at": report.created_at,
        }
        for report in reports
    ]
    return Response({"count": len(data), "results": data}, status=status.HTTP_200_OK)
