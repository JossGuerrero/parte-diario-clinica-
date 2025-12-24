import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'Hospital.settings'
import django
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
print('superuser exists:', User.objects.filter(is_superuser=True).exists())
print('users sample:', list(User.objects.values_list('username', flat=True)[:10]))
if not User.objects.filter(username='testadmin').exists():
    User.objects.create_superuser('testadmin','testadmin@example.com','Test@123')
    print('created testadmin')
else:
    print('testadmin already exists')

from django.test import Client
c = Client()
resp = c.get('/')
print('GET / ->', resp.status_code, 'redirect:', resp.url)
resp = c.post('/login/', {'username': 'testadmin', 'password':'Test@123'}, follow=True)
print('POST /login/ ->', resp.status_code)
resp = c.get('/')un boton que suba el archivo 

print('After login GET / ->', resp.status_code)
resp = c.get('/logout/', follow=True)
print('GET /logout/ ->', resp.status_code, 'redirect_chain:', resp.redirect_chain[:3])
resp = c.get('/')
print('After logout GET / ->', resp.status_code, 'redirect:', resp.url)
