# 🛠 ONNX Model Integration with Django (PitWatch)

## 📌 Overview

This guide explains how to integrate an ONNX pothole detection model into a Django (DRF) backend.

The model:

* Takes an image as input
* Returns a probability (0–1) indicating pothole presence

---

## 🧠 System Flow

Client (React / Mobile)
→ Upload Image
→ Django API
→ ONNX Inference
→ Response (pothole + confidence)
→ (Optional) Save to PostGIS

---

## ⚙️ Step 1: Install Dependencies

```bash
pip install onnxruntime opencv-python numpy pillow
```

---

## 📂 Step 2: Project Structure

```
your_project/
 ├── your_app/
 │    ├── services/
 │    │    └── model.py
 │    ├── views.py
 │    ├── urls.py
 ├── model/
 │    └── pothole_model.onnx
```

---

## 🧩 Step 3: Model Loader (services/model.py)

```python
import onnxruntime as ort
import numpy as np
import cv2

session = ort.InferenceSession("model/pothole_model.onnx")

input_name = session.get_inputs()[0].name
output_name = session.get_outputs()[0].name


def preprocess_image(image):
    image = cv2.resize(image, (224, 224))
    image = image / 255.0
    image = np.transpose(image, (2, 0, 1))
    image = np.expand_dims(image, axis=0).astype(np.float32)
    return image


def predict(image):
    input_tensor = preprocess_image(image)
    outputs = session.run([output_name], {input_name: input_tensor})
    probability = float(outputs[0][0])
    return probability
```

---

## 🔌 Step 4: API Endpoint (views.py)

```python
from rest_framework.decorators import api_view
from rest_framework.response import Response
import numpy as np
import cv2
from .services.model import predict


@api_view(['POST'])
def detect_pothole(request):
    file = request.FILES.get('image')

    if not file:
        return Response({"error": "No image uploaded"}, status=400)

    file_bytes = np.asarray(bytearray(file.read()), dtype=np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    probability = predict(image)

    return Response({
        "pothole": probability > 0.5,
        "confidence": probability
    })
```

---

## 🌐 Step 5: URL Configuration (urls.py)

```python
from django.urls import path
from .views import detect_pothole

urlpatterns = [
    path('detect/', detect_pothole),
]
```

---

## 🧪 Step 6: Testing API

```bash
curl -X POST http://127.0.0.1:8000/api/detect/ \
  -F "image=@test.jpg"
```

Response:

```json
{
  "pothole": true,
  "confidence": 0.82
}
```

---

## ⚡ Performance Optimizations

### ✅ Load Model Once

* Do NOT load model inside request
* Keep global session object

### ✅ Threshold Tuning

```python
pothole = probability > 0.5
```

* 0.6 → more strict
* 0.4 → more sensitive

### ✅ Resize Based on Model

Check input shape:

```python
print(session.get_inputs()[0].shape)
```

---

## 🗄 Step 7: Save to Database (Optional)

Only store valid potholes:

```python
if probability > 0.6:
    save_to_db()
```

Recommended fields:

* image
* latitude
* longitude
* confidence
* timestamp

---

## 🌍 Step 8: PostGIS Integration (Future)

* Store geolocation using PointField
* Query nearby potholes
* Cluster pothole regions

---

## 🚀 Deployment Notes

### Render (Free Tier)

* Service sleeps after inactivity
* Use uptime ping (GitHub Actions / cron)

### Requirements.txt

```
onnxruntime
opencv-python
numpy
pillow
```

---

## ❗ Common Errors

### Shape mismatch

* Ensure correct resize (224x224 or model-specific)

### Wrong color format

* OpenCV uses BGR
* Model may expect RGB

Fix:

```python
image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
```

---

## 🔮 Next Improvements

* Add bounding box detection (if model supports)
* Add async queue (Celery) for scaling
* Integrate map visualization
* Add clustering using PostGIS

---

## ✅ Summary

You now have:

* ONNX model integrated into Django
* API for pothole detection
* Optimized inference pipeline

Next step: connect with frontend + map system 🚀
