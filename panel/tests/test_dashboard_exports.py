from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from panel.models import DailyEqctacliSummary
from datetime import date

class DashboardExportTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        # create two days of summary
        DailyEqctacliSummary.objects.create(date=date(2025,12,22), num_atenciones=10, total_consulta=100.00, total_medicina=50.00, num_citas=2)
        DailyEqctacliSummary.objects.create(date=date(2025,12,23), num_atenciones=20, total_consulta=200.00, total_medicina=75.00, num_citas=3)
        self.client = Client()
        self.client.force_login(self.user)

    def test_dashboard_api_json(self):
        res = self.client.get('/panel/api/dashboard/?desde=2025-12-22&hasta=2025-12-23')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('labels', data)
        self.assertIn('datasets', data)
        self.assertIn('rows', data)
        self.assertEqual(len(data['labels']), 2)

    def test_export_csv(self):
        res = self.client.get('/panel/api/dashboard/export_csv/?desde=2025-12-22&hasta=2025-12-23')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'text/csv')
        content = res.content.decode('utf-8')
        self.assertIn('periodo,atenciones,total_consulta,total_medicina', content)
        self.assertIn('2025-12-22', content)

    def test_export_xlsx(self):
        res = self.client.get('/panel/api/dashboard/export_xlsx/?desde=2025-12-22&hasta=2025-12-23')
        self.assertEqual(res.status_code, 200)
        self.assertIn('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', res['Content-Type'])
        self.assertTrue(len(res.content) > 0)
        self.assertTrue(res.content.startswith(b'PK'))

    def test_export_pdf(self):
        res = self.client.get('/panel/api/dashboard/export_pdf/?desde=2025-12-22&hasta=2025-12-23')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/pdf')
        self.assertTrue(len(res.content) > 0)
        self.assertTrue(res.content.startswith(b'%PDF'))
