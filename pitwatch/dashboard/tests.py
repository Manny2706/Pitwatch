from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from reports.models import Report


class DashboardSummaryAccessTests(APITestCase):
	def setUp(self):
		self.client = APIClient()
		self.endpoint = "/api/v1/dashboard/summary/"
		user_model = get_user_model()

		self.user = user_model.objects.create_user(
			username="regular-user",
			email="regular@example.com",
			password="StrongPass123!",
		)
		self.admin_user = user_model.objects.create_superuser(
			username="admin-user",
			email="admin@example.com",
			password="StrongPass123!",
		)

	def test_summary_requires_authentication(self):
		response = self.client.get(self.endpoint)
		self.assertEqual(response.status_code, 401)

	def test_summary_forbids_non_admin_user(self):
		self.client.force_authenticate(user=self.user)
		response = self.client.get(self.endpoint)
		self.assertEqual(response.status_code, 403)

	def test_summary_allows_admin_user(self):
		Report.objects.create(title="P1", status=Report.STATUS_PENDING)
		Report.objects.create(title="P2", status=Report.STATUS_RESOLVED)

		self.client.force_authenticate(user=self.admin_user)
		response = self.client.get(self.endpoint)

		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertEqual(payload["totals"]["total_reports"], 2)
		self.assertEqual(payload["totals"]["pending"], 1)
		self.assertEqual(payload["totals"]["resolved"], 1)
		self.assertEqual(payload["totals"]["rejected"], 0)
