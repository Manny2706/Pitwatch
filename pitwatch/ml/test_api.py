from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from rest_framework.test import APIClient, APITestCase


class DetectPotholeRouteApiTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.endpoint = "/api/v1/ml/detect/"

    def test_route_rejects_missing_image(self):
        response = self.client.post(self.endpoint, data={}, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "No image uploaded"})

    def test_route_rejects_invalid_image(self):
        broken_file = SimpleUploadedFile("broken.jpg", b"not-a-valid-image", content_type="image/jpeg")

        response = self.client.post(self.endpoint, data={"image": broken_file}, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    @patch("ml.views.predict_from_file", return_value=0.91)
    def test_route_returns_prediction_payload(self, mock_predict):
        image_like_file = SimpleUploadedFile("sample.jpg", b"fake-image-bytes", content_type="image/jpeg")

        response = self.client.post(self.endpoint, data={"image": image_like_file}, format="multipart")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"pothole": True, "confidence": 0.91})
        self.assertTrue(mock_predict.called)


class SubmitAndStatusEdgeCaseApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.submit_endpoint = "/api/v1/ml/detect/submit/"
        self.status_endpoint_template = "/api/v1/ml/detect/status/{task_id}/"
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="edgecase-user",
            email="edgecase@example.com",
            password="StrongPass123!",
        )

    def test_submit_requires_authentication(self):
        response = self.client.post(self.submit_endpoint, data={}, format="multipart")
        self.assertEqual(response.status_code, 401)

    def test_submit_rejects_missing_image_for_authenticated_user(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.submit_endpoint, data={}, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "No image uploaded"})

    def test_submit_rejects_empty_image_file(self):
        self.client.force_authenticate(user=self.user)
        empty_image = SimpleUploadedFile("empty.jpg", b"", content_type="image/jpeg")

        response = self.client.post(self.submit_endpoint, data={"image": empty_image}, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "No image uploaded"})

    @patch("ml.views.run_pothole_inference.delay", side_effect=Exception("broker unavailable"))
    def test_submit_returns_503_when_task_enqueue_fails(self, _mock_delay):
        self.client.force_authenticate(user=self.user)
        image_file = SimpleUploadedFile("sample.jpg", b"fake-image-bytes", content_type="image/jpeg")

        response = self.client.post(self.submit_endpoint, data={"image": image_file}, format="multipart")

        self.assertEqual(response.status_code, 503)
        self.assertIn("Failed to queue task", response.json().get("error", ""))

    def test_status_returns_404_for_unknown_task_id(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.status_endpoint_template.format(task_id="missing-task"))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": "Task not found", "task_id": "missing-task"})
