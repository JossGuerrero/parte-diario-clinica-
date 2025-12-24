from django.urls import path
from . import views
from django.views.decorators.cache import cache_page

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_index, name='index'),
    path('api/atenciones-mes/', views.atenciones_por_mes, name='atenciones_mes'),
    path('api/atenciones-edad/', views.atenciones_por_edad, name='atenciones_edad'),
    path('api/valor-consulta/', views.valor_recaudado_consulta, name='valor_consulta'),
    path('api/valor-medicina/', views.valor_recaudado_medicina, name='valor_medicina'),
    path('api/atenciones-institucion/', views.atenciones_por_institucion, name='atenciones_institucion'),
    path('api/atenciones-genero/', views.atenciones_por_genero, name='atenciones_genero'),
    path('api/data/', cache_page(60)(views.dashboard_data), name='data'),
    path('export/parte-diario/', views.export_parte_diario, name='export_parte_diario'),
    path('export/detalle/', views.export_detalle, name='export_detalle'),
]
