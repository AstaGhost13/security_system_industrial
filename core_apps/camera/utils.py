from django.conf import settings
from datetime import datetime
from core_apps.camera.models import SecurityEvent

import os
import cv2
import numpy as np

def save_event_image(frame, event_type):
    """Guarda la imagen del evento y devuelve la ruta relativa"""
    try:
        # Crear directorio si no existe
        events_dir = os.path.join(settings.MEDIA_ROOT, 'security_events')
        os.makedirs(events_dir, exist_ok=True)
        
        # Generar nombre de archivo único
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{event_type}_{timestamp}.jpg"
        filepath = os.path.join('security_events', filename)
        full_path = os.path.join(settings.MEDIA_ROOT, filepath)
        
        # Guardar imagen
        cv2.imwrite(full_path, frame)
        
        return filepath
    except Exception as e:
        print(f"Error al guardar imagen de evento: {e}")
        return None

def create_security_event(event_type, details, frame=None, user=None):
    """Crea un nuevo evento de seguridad"""
    try:
        image_path = save_event_image(frame, event_type) if frame is not None else None
        
        event = SecurityEvent.objects.create(
            event_type=event_type,
            details=details,
            image_path=image_path,
            related_user=user
        )
        return event
    except Exception as e:
        print(f"Error al crear evento de seguridad: {e}")
        return None