import os
import sys
from pathlib import Path
# ensure project root on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Hospital.settings')
import django
django.setup()
from django.test import Client

c = Client()
print('GET /')
r = c.get('/', follow=False)
print('status', r.status_code, 'Location:', r.get('Location'))

print('\nGET /login/')
rl = c.get('/login/')
print('status', rl.status_code)

print('\nPOST /login/ (admin)')
rp = c.post('/login/', {'username': 'admin', 'password': 'Admin@123'}, follow=False)
print('status', rp.status_code, 'Location:', rp.get('Location'))

# show a short snippet of response to diagnose
print('\nResponse snippet:')
print(rp.content.decode('utf-8')[:800])

# extra debug: check user record and authenticate programmatically
from django.contrib.auth import get_user_model, authenticate
User = get_user_model()
user = User.objects.filter(username='admin').first()
print('\nUser exists:', bool(user))
if user:
    print('is_superuser:', user.is_superuser, 'is_active:', user.is_active)
    print('check_password(Admin@123):', user.check_password('Admin@123'))
    auth = authenticate(username='admin', password='Admin@123')
    print('authenticate returned:', auth)

# follow the redirect
if rp.status_code in (301,302):
    loc = rp.get('Location')
    rpanel = c.get(loc)
    print('\nGET after login ->', loc, 'status', rpanel.status_code)
    print('Panel content length:', len(rpanel.content))
else:
    print('\nLogin did not redirect; response code:', rp.status_code)
