
import os
import json
import face_recognition
import cv2
import numpy as np
from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators import gzip
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from .models import AuthorizedPerson, SecurityEvent
from django.views.generic import TemplateView
from datetime import datetime
from django.shortcuts import get_object_or_404


# Configuración de objetos peligrosos (usando YOLO)
YOLO_CONFIG = {
    "weights": os.path.join(settings.BASE_DIR, "camera", "yolov3-tiny.weights"),
    "cfg": os.path.join(settings.BASE_DIR, "camera", "yolov3-tiny.cfg"),
    "classes": os.path.join(settings.BASE_DIR, "camera", "coco.names"),
    "dangerous_classes": ['knife', 'gun', 'scissors', 'bottle']  # Clases de objetos peligrosos
}

# Cargar modelo YOLO
net = cv2.dnn.readNet(YOLO_CONFIG["weights"], YOLO_CONFIG["cfg"])

with open(YOLO_CONFIG["classes"], "r") as f:
    classes = [line.strip() for line in f.readlines()]

def get_authorized_encodings():
    authorized = AuthorizedPerson.objects.filter(is_active=True)
    encodings = []
    users = []
    
    for person in authorized:
        encoding = json.loads(person.face_encoding)
        encodings.append(np.array(encoding))
        users.append(person.user.username)
    
    return encodings, users

def detect_dangerous_objects(frame):
    height, width = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
    net.setInput(blob)
    outs = net.forward(net.getUnconnectedOutLayersNames())

    dangerous_objects = []
    class_ids = []
    confidences = []
    boxes = []

    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > 0.5 and classes[class_id] in YOLO_CONFIG["dangerous_classes"]:
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)
                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)

    indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
    
    for i in range(len(boxes)):
        if i in indexes:
            label = str(classes[class_ids[i]])
            dangerous_objects.append({
                "label": label,
                "confidence": confidences[i],
                "box": boxes[i]
            })
    
    return dangerous_objects


def gen_frames():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    # Configuración para mejor rendimiento
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # Reducir resolución
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 15)  # Limitar FPS
    
    # Cargar modelos (una sola vez al inicio)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    
    frame_counter = 0
    
    while True:
        success, frame = cap.read()
        if not success:
            break
        
        frame_counter += 1
        
        # Reducir tamaño para procesamiento
        small_frame = cv2.resize(frame, (320, 240))
        
        # Procesamiento alternado para mejor rendimiento
        if frame_counter % 3 == 0:  # Solo procesar 1 de cada 3 frames
            # Detección de rostros
            gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            # Detección de objetos (cada 6 frames)
            if frame_counter % 6 == 0:
                blob = cv2.dnn.blobFromImage(small_frame, 1/255.0, (320, 320), swapRB=True, crop=False)
                net.setInput(blob)
                outs = net.forward(net.getUnconnectedOutLayersNames())
                
                # Procesar detecciones
                for out in outs:
                    for detection in out:
                        scores = detection[5:]
                        class_id = np.argmax(scores)
                        confidence = scores[class_id]
                        if confidence > 0.5 and classes[class_id] in YOLO_CONFIG["dangerous_classes"]:
                            # Escalar coordenadas al tamaño original
                            box = detection[0:4] * np.array([frame.shape[1], frame.shape[0], frame.shape[1], frame.shape[0]])
                            (x, y, w, h) = box.astype("int")
                            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                            label = f"{classes[class_id]}: {confidence:.2f}"
                            cv2.putText(frame, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)
            
            # Dibujar rostros (escalar coordenadas)
            for (x, y, w, h) in faces:
                x, y, w, h = x*2, y*2, w*2, h*2  # Escalar al tamaño original
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
        
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])  # Reducir calidad JPEG
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        

@gzip.gzip_page
def video_feed(request):
    return StreamingHttpResponse(gen_frames(), content_type="multipart/x-mixed-replace;boundary=frame")

@csrf_exempt
def register_face(request):
    if request.method == 'POST' and request.user.is_authenticated:
        try:
            image_file = request.FILES['image']
            image = face_recognition.load_image_file(image_file)
            face_encodings = face_recognition.face_encodings(image)
            
            if len(face_encodings) == 0:
                return JsonResponse({'status': 'error', 'message': 'No se detectó ningún rostro en la imagen'})
            
            encoding = face_encodings[0].tolist()
            
            AuthorizedPerson.objects.update_or_create(
                user=request.user,
                defaults={'face_encoding': json.dumps(encoding), 'is_active': True}
            )
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

def get_events(request):
    events = SecurityEvent.objects.order_by('-timestamp')[:50]
    data = [{
        'event_type': event.get_event_type_display(),
        'details': event.details,
        'timestamp': event.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'resolved': event.resolved
    } for event in events]
    
    return JsonResponse({'events': data})

@csrf_exempt
def mark_event_resolved(request, event_id):
    if request.method == 'POST':
        try:
            event = SecurityEvent.objects.get(id=event_id)
            event.resolved = True
            event.save()
            return JsonResponse({'status': 'success'})
        except SecurityEvent.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Evento no encontrado'}, status=404)
    
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)





def get_security_events(request):
    events = SecurityEvent.objects.all().order_by('-timestamp')[:50]  # Últimos 50 eventos
    events_data = []
    
    for event in events:
        events_data.append({
            'id': event.id,
            'event_type': event.event_type,
            'event_type_display': event.get_event_type_display(),
            'details': event.details,
            'timestamp': event.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'resolved': event.resolved,
            'image_url': event.get_image_url(),
            'user': event.related_user.username if event.related_user else 'Sistema'
        })
    
    return JsonResponse({'events': events_data})

@csrf_exempt
def mark_event_as_resolved(request, event_id):
    if request.method == 'POST':
        event = get_object_or_404(SecurityEvent, id=event_id)
        event.resolved = True
        event.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=405)

#  Vista basada en clases  
class CameraView(TemplateView):
    template_name = 'camera/camera.html'


class AlertaView(TemplateView):
    template_name = 'camera/alerta.html'