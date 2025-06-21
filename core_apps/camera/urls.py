
from django.urls import path,include
from . import views
from .views import CameraView,AlertaView
from .views import get_security_events, mark_event_as_resolved


name = 'camera'
urlpatterns = [

    path('', CameraView.as_view(), name='camera'),
    path('alerta/', AlertaView.as_view(), name='alerta'),

    path('video_feed/', views.video_feed, name='video_feed'),
    path('register_face/', views.register_face, name='register_face'),
    path('get_events/', views.get_events, name='get_events'),
    path('mark_event_resolved/<int:event_id>/', views.mark_event_resolved, name='mark_event_resolved'),
    
    path('security-events/', get_security_events, name='get_security_events'),
    path('security-events/<int:event_id>/resolve/', mark_event_as_resolved, name='mark_event_resolved'),

]