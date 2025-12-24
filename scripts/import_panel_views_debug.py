import importlib, traceback

importlib.invalidate_caches()
try:
    m = importlib.import_module('panel.views')
    print('Imported panel.views ok:', hasattr(m, 'dashboard'))
except Exception:
    traceback.print_exc()
    raise
