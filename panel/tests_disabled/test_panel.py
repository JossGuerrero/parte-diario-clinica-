from django.test import TestCase, Client
from django.contrib.auth import get_user_model


class PanelSmokeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        # index page requires superuser; create one for the test
        self.user = User.objects.create_superuser(username='admin', password='adminpass')
        self.client = Client()
        self.client.force_login(self.user)

    def test_smoke(self):
        # Placeholder test moved from panel/tests.py to avoid discovery conflicts
        self.assertTrue(True)

    def test_index_renders(self):
        """GET /panel/ should render the index page without errors."""
        res = self.client.get('/panel/')
        self.assertEqual(res.status_code, 200)
        # ensure key strings are present
        self.assertIn('Parte diario', res.content.decode('utf-8'))

