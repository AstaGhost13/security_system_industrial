from django.contrib import admin
from django.urls import path,include
from core_apps.common.views import IndexView


urlpatterns = [
    path('admin/', admin.site.urls),

    path('', IndexView.as_view(), name='index'),  # Ruta para la página de inicio
    path('camera/', include('core_apps.camera.urls')),# Ruta para la camara
    
]
