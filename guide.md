# 📘 PitWatch – PostGIS (Neon) + Django (No GDAL) Implementation Guide

---

## 🧠 Overview

This guide shows how to integrate **PostGIS (NeonDB)** with a **Django + DRF backend** **WITHOUT using GeoDjango or GDAL**.

### 🎯 Why This Approach?

* ✅ No GDAL setup (simpler on Windows)
* ✅ Faster development
* ✅ Full PostGIS power via SQL
* ✅ Ideal for API-based systems like PitWatch

---

## 🏗️ Architecture

```id="d4r8m1"
Frontend (React / Map)
        ↓
Django REST Framework API
        ↓
Raw SQL / Django ORM
        ↓
NeonDB (PostgreSQL + PostGIS)
```

---

## ⚙️ Step 1: NeonDB Setup

### Enable PostGIS

Run in Neon SQL Editor:

```sql id="zz9k02"
CREATE EXTENSION postgis;
```

Verify:

```sql id="bt5r5c"
SELECT PostGIS_Version();
```

---

## 🐍 Step 2: Backend Setup

### Install Dependencies

```bash id="8n7kq2"
pip install django djangorestframework psycopg2-binary
```

---

## ⚙️ Step 3: Configure Database

```python id="gk3r8k"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "your_db",
        "USER": "your_user",
        "PASSWORD": "your_password",
        "HOST": "ep-xxx.neon.tech",
        "PORT": "5432",
        "OPTIONS": {
            "sslmode": "require",
        },
    }
}
```

---

## 🧱 Step 4: Create Model (NO GeoDjango)

```python id="q2m9rf"
from django.db import models

class PitReport(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
```

---

## 🛠️ Step 5: Run Migrations

```bash id="mx0p2v"
python manage.py makemigrations
python manage.py migrate
```

---

## 🧪 Step 6: Insert Test Data

```bash id="xztl4y"
python manage.py shell
```

```python id="m7r8ab"
from reports.models import PitReport

PitReport.objects.create(
    title="Road Pit",
    description="Large pothole",
    latitude=28.66,
    longitude=77.45
)
```

---

## 🔍 Step 7: Nearby Search API (Core Feature)

### views.py

```python id="c1v7pz"
from django.db import connection
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(["GET"])
def nearby_reports(request):
    lat = float(request.GET.get("lat"))
    lng = float(request.GET.get("lng"))

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, title,
            ST_Distance(
                ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
            ) AS distance
            FROM reports_pitreport
            ORDER BY distance
            LIMIT 10;
        """, [lng, lat])

        rows = cursor.fetchall()

    data = [
        {
            "id": r[0],
            "title": r[1],
            "distance_m": float(r[2])
        }
        for r in rows
    ]

    return Response(data)
```

---

## 🌐 Step 8: URL Routing

```python id="pj9qk3"
from django.urls import path
from .views import nearby_reports

urlpatterns = [
    path("nearby/", nearby_reports),
]
```

---

## 📡 Example API Call

```id="xt0s9n"
GET /api/nearby/?lat=28.66&lng=77.45
```

---

## ⚡ Step 9: Radius Filtering (Important)

```sql id="2q8m1z"
WHERE ST_DWithin(
    ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography,
    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
    5000
)
```

👉 5000 = 5km radius

---

## 🚀 Step 10: Add Index for Performance

```sql id="7y6c4x"
CREATE INDEX pitreport_geo_idx
ON reports_pitreport
USING GIST (
    ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
);
```

---

## 🧩 Step 11: Frontend Integration

* Use Leaflet / Mapbox
* Fetch `/api/nearby/`
* Plot markers using lat/lng
* Optional:

  * clustering
  * heatmaps

---

## ⚠️ Common Issues

| Issue             | Fix                   |
| ----------------- | --------------------- |
| Slow queries      | Add GIST index        |
| Wrong distance    | Use `::geography`     |
| SSL error         | Add `sslmode=require` |
| Incorrect results | Ensure lng, lat order |

---

## 🧠 Best Practices

* Always store lat/lng as float
* Use PostGIS functions for calculations
* Limit query results (pagination)
* Validate input coordinates

---

## 🔥 Future Improvements

* Add filtering (status, severity)
* Pagination + sorting
* Caching (Redis)
* Real-time updates (Kafka optional)
* Geo clustering on frontend

---

## ✅ Final Checklist

* [ ] Neon DB ready
* [ ] PostGIS enabled
* [ ] Django connected
* [ ] Model created
* [ ] API working
* [ ] Index added

---

## 🎯 Conclusion

You now have a **clean, scalable, GDAL-free backend**:

* ✅ NeonDB (serverless PostgreSQL)
* ✅ PostGIS (geo queries)
* ✅ Django + DRF (API layer)
* ❌ No GeoDjango
* ❌ No GDAL headaches

Perfect for **PitWatch** 🚀

---
