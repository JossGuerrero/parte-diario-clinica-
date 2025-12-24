import re
import unittest
from pathlib import Path

TEMPLATE_PATH = Path(__file__).resolve().parents[1] / 'templates' / 'dashboard' / 'index.html'

class DashboardFrontendStaticTests(unittest.TestCase):
    def setUp(self):
        self.src = TEMPLATE_PATH.read_text(encoding='utf-8')

    def test_filters_change_handler_does_not_auto_refresh(self):
        """Filter change handlers must only save filters and NOT call refresh()."""
        # look for the change handler registration block
        self.assertIn("['desde','hasta','filter-institucion','filter-genero','filter-edad']", self.src)
        # ensure the handler only calls saveFilters() and not refresh()
        self.assertRegex(self.src, r"el\.addEventListener\('change',\s*\(\)\s*=>\s*\{\s*saveFilters\(\);\s*\}\)\s*;")
        self.assertNotIn('saveFilters(); refresh();', self.src)

    def test_clear_button_does_not_call_refresh(self):
        """Clear button handler should reset filters and save state but NOT trigger a refresh()."""
        # find the btn-clear handler
        m = re.search(r"\$id\('btn-clear'\)\.addEventListener\('click',\s*function\(e\)\{([\s\S]*?)\}\)\s*;", self.src)
        self.assertIsNotNone(m, 'btn-clear handler not found in template')
        handler_body = m.group(1)
        self.assertIn("localStorage.removeItem(STORAGE_KEY)", handler_body)
        self.assertIn("defaultDates();", handler_body)
        # it must not call refresh()
        self.assertNotIn('refresh();', handler_body)
        # it should persist the cleared filters
        self.assertIn('saveFilters();', handler_body)

    def test_compute_uses_server_totales(self):
        """Frontend summary rendering must prefer server-side 'totales' object."""
        self.assertIn('const tot = data.totales', self.src)

    def test_export_link_uses_same_filters(self):
        """Export link should be constructed from the same filters and point to export/detalle."""
        self.assertIn("/dashboard/export/detalle/", self.src)
        # ensure export query string keys use the same names as the API
        self.assertIn("exportQs.set('inicio'", self.src)
        self.assertIn("exportQs.set('fin'", self.src)
        self.assertIn("exportQs.set('institucion'", self.src)

    def test_sin_registros_message_present(self):
        """Template should include the 'Sin registros' message for empty results."""
        self.assertIn("Sin registros en el período seleccionado", self.src)

    def find_repo_root(self):
        p = Path(__file__).resolve()
        for _ in range(10):
            if (p / 'manage.py').exists():
                return p
            p = p.parent
        raise RuntimeError('Repo root (manage.py) not found')

    def test_demo_flag_disabled_in_base_template(self):
        """Base template should explicitly disable demo visualizations by default."""
        root = self.find_repo_root()
        base_tpl = root / 'panel' / 'templates' / 'index_master.html'
        self.assertTrue(base_tpl.exists(), f'Base template not found at {base_tpl}')
        base_src = base_tpl.read_text(encoding='utf-8')
        self.assertIn('window.ENABLE_DEMO = false', base_src)

    def test_custom_js_gates_demo_initializers(self):
        """Main custom.js should gate demo initializers using a DEMO flag."""
        root = self.find_repo_root()
        js = root / 'panel' / 'static' / 'FrWork' / 'admin_lte' / 'build' / 'js' / 'custom.js'
        self.assertTrue(js.exists(), f'custom.js not found at {js}')
        txt = js.read_text(encoding='utf-8')
        self.assertIn('var DEMO = window.ENABLE_DEMO;', txt)
        self.assertIn('if (DEMO) {', txt)

if __name__ == '__main__':
    unittest.main()
