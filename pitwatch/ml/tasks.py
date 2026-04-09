import base64

from celery import shared_task

from .models import InferenceJob, PotholeReport
from .services.model import predict_from_bytes

from reports.models import Report


@shared_task(bind=True, name="ml.run_pothole_inference")
def run_pothole_inference(self, image_b64: str, latitude: float = None, longitude: float = None) -> dict:
    job = InferenceJob.objects.filter(task_id=self.request.id).first()
    if job:
        job.status = InferenceJob.STATUS_RUNNING
        job.save(update_fields=["status", "updated_at"])

    try:
        raw_bytes = base64.b64decode(image_b64)
        probability = predict_from_bytes(raw_bytes)
        result = {
            "pothole": probability > 0.5,
            "confidence": probability,
        }

        if job:
            job.status = InferenceJob.STATUS_SUCCESS
            job.pothole = result["pothole"]
            job.confidence = result["confidence"]
            job.error_message = ""
            job.save(update_fields=["status", "pothole", "confidence", "error_message", "updated_at"])

            if result["pothole"] and job.submitted_by_id:
                PotholeReport.objects.update_or_create(
                    task_id=job.task_id,
                    defaults={
                        "user_id": job.submitted_by_id,
                        "image_name": job.image_name,
                        "confidence": result["confidence"],
                    },
                )
                Report.objects.create(
                    user_id=job.submitted_by_id,
                    title=f"Pothole detected: {job.image_name or job.task_id}",
                    description=(
                        f"Auto-created from ML inference task {job.task_id}. "
                        f"Confidence: {result['confidence']:.3f}"
                    ),
                    status=Report.STATUS_PENDING,
                    latitude=latitude,
                    longitude=longitude,
                )

        return result
    except Exception as exc:
        if job:
            job.status = InferenceJob.STATUS_FAILED
            job.error_message = str(exc)
            job.save(update_fields=["status", "error_message", "updated_at"])
        raise
