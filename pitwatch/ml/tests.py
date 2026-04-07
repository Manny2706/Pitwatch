from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory
from unittest.mock import patch

from .views import detect_pothole


class DetectPotholeApiTests(SimpleTestCase):
	def setUp(self):
		self.factory = APIRequestFactory()
		self.endpoint = "/api/v1/ml/detect/"

	def test_detect_requires_image_file(self):
		request = self.factory.post(self.endpoint, data={}, format="multipart")
		response = detect_pothole(request, version="v1")

		self.assertEqual(response.status_code, 400)
		self.assertEqual(response.data, {"error": "No image uploaded"})

	def test_detect_rejects_invalid_image(self):
		broken_file = SimpleUploadedFile("broken.jpg", b"not-a-valid-image", content_type="image/jpeg")
		request = self.factory.post(self.endpoint, data={"image": broken_file}, format="multipart")
		response = detect_pothole(request, version="v1")

		self.assertEqual(response.status_code, 400)
		self.assertIn("error", response.data)

	@patch("ml.views.predict_from_file", return_value=0.82)
	def test_detect_returns_prediction_payload(self, mock_predict):
		image_like_file = SimpleUploadedFile(
			"test.jpg",
			b"minimal-image-bytes",
			content_type="image/jpeg",
		)
		request = self.factory.post(self.endpoint, data={"image": image_like_file}, format="multipart")
		response = detect_pothole(request, version="v1")

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data, {"pothole": True, "confidence": 0.82})
		self.assertTrue(mock_predict.called)
