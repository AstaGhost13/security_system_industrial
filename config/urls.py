from django.contrib import admin
from django.urls import path,include
from core_apps.common.views import IndexView,DashboardView


urlpatterns = [
    path('admin/', admin.site.urls),

    path('', IndexView.as_view(), name='index'),  # Ruta para la página de inicio
    path('dashboard/', DashboardView.as_view(), name='dashboard'),  # Ruta para el dashboard

    path('camera/', include('core_apps.camera.urls'))
    
]
