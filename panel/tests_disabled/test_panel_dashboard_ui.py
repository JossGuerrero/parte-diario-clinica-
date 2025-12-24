import unittest
from pathlib import Path

class PanelDashboardUITests(unittest.TestCase):
    def setUp(self):
        self.tpl = Path(__file__).resolve().parents[1] / 'templates' / 'panel' / 'dashboard.html'
        self.src = self.tpl.read_text(encoding='utf-8')

    def test_no_auto_fetch_on_load(self):
        self.assertNotIn('fetchData();', self.src)

    def test_render_charts_hides_on_empty(self):
        self.assertIn("Sin registros para el periodo seleccionado", self.src)
        self.assertIn("document.getElementById('chartAtenciones').style.display = 'none'", self.src)

if __name__ == '__main__':
    unittest.main()
