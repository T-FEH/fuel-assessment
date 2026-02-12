# Django Fuel Route Optimizer - Copilot Instructions

## Project Overview
Building a Django REST API that calculates optimal fuel stops along a route in the USA. The API takes start/finish locations, returns a route map with cost-effective fuel stops based on vehicle range (500 miles) and fuel efficiency (10 mpg).

## Your Background
- **Strong**: Python, FastAPI
- **Learning**: Django (this project will teach you Django concepts by comparing to FastAPI patterns you know)

---

## Django vs FastAPI Quick Reference

### Project Structure Comparison
```
FastAPI                          Django
├── main.py                      ├── manage.py           # CLI tool (like uvicorn entrypoint)
├── routers/                     ├── fuel_optimizer/     # "App" (like a router module)
│   └── routes.py                │   ├── views.py        # Endpoints (like route handlers)
│                                │   ├── urls.py         # URL routing (like APIRouter)
│                                │   ├── models.py       # ORM models (same as SQLAlchemy)
│                                │   └── serializers.py  # Pydantic-like validation
├── schemas.py                   └── config/             # Project settings
└── config.py                        ├── settings.py     # App config (like .env + config.py)
                                     └── urls.py         # Root URL router
```

### Key Concept Mappings

| FastAPI Concept | Django Equivalent | Notes |
|-----------------|-------------------|-------|
| `@app.get("/path")` | `path("path/", views.my_view)` in urls.py | URLs defined separately from views |
| `async def endpoint()` | `def view(request)` or `class APIView` | DRF provides class-based views |
| Pydantic models | Django REST Framework Serializers | Validation + serialization |
| `Depends()` | Django middleware or DRF permissions | Dependency injection pattern |
| `uvicorn main:app` | `python manage.py runserver` | Dev server command |
| SQLAlchemy ORM | Django ORM | Very similar, Django's is built-in |
| `FastAPI()` instance | `INSTALLED_APPS` in settings.py | App registration |

### Request/Response Pattern
```python
# FastAPI
@app.post("/route")
async def calculate_route(data: RouteRequest) -> RouteResponse:
    return {"route": [...]}

# Django REST Framework
class RouteView(APIView):
    def post(self, request):
        serializer = RouteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"route": [...]})
```

---

## Project Requirements Checklist

### API Specifications
- [ ] **Input**: Start location, finish location (both USA)
- [ ] **Output**: 
  - Route map (GeoJSON or polyline)
  - Optimal fuel stop locations along route
  - Total fuel cost calculation
- [ ] **Constraints**:
  - Vehicle range: 500 miles max
  - Fuel efficiency: 10 miles per gallon
  - Multiple fuel stops if route > 500 miles

### Performance Requirements
- [ ] Fast response times (optimize data queries)
- [ ] Minimize external API calls (1 ideal, 2-3 acceptable)
- [ ] Use spatial indexing for fuel station lookup

### Technical Requirements
- [ ] Latest stable Django (5.x)
- [ ] Django REST Framework for API
- [ ] Use provided fuel prices CSV data
- [ ] Free routing API: **OSRM** (Open Source Routing Machine) - unlimited, no API key needed

---

## Tech Stack

### Core Dependencies
```toml
[project]
dependencies = [
    "django>=5.0",
    "djangorestframework>=3.14",
    "pandas>=2.0",           # CSV processing
    "numpy>=1.24",           # Calculations
    "requests>=2.31",        # OSRM API calls
    "scipy>=1.11",           # Spatial calculations (KDTree)
    "python-dotenv>=1.0",    # Environment variables
]

[project.optional-dependencies]
dev = [
    "ruff>=0.1",
    "pytest-django>=4.5",
]
```

### Free Routing API: OSRM
**Why OSRM?**
- Completely free, no API key required
- Open source, can self-host if needed
- Returns route geometry + distances
- Demo server: `https://router.project-osrm.org`

**Single API Call Strategy**:
```python
# One call gets: route geometry, total distance, waypoints
url = f"https://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}"
params = {"overview": "full", "geometries": "geojson", "steps": "true"}
```

---

## Architecture Design

### Data Flow
```
1. Request (start, end) 
   ↓
2. Geocode locations (if needed) - could use Nominatim (free)
   ↓
3. Get route from OSRM (1 API call)
   ↓
4. Sample points along route every ~400 miles
   ↓
5. Find cheapest fuel stations near each sample point (local data)
   ↓
6. Calculate total fuel cost
   ↓
7. Return route + fuel stops + cost
```

### Fuel Station Optimization Strategy
```python
# Pre-load all stations with coordinates into spatial index (KDTree)
# For each ~400 mile interval on route:
#   1. Get point on route at that distance
#   2. Find stations within 10-mile radius using KDTree (O(log n))
#   3. Select cheapest station in radius
#   4. Add to fuel stops list
```

### Performance Optimizations
1. **Pre-compute spatial index**: Load CSV → KDTree at startup
2. **Single OSRM call**: Get full route geometry once
3. **NumPy vectorized operations**: Fast distance calculations
4. **In-memory data**: No database needed for fuel stations (8K rows is tiny)

---

## Django Project Structure

```
fuel_assessment/
├── manage.py
├── pyproject.toml
├── .env
├── data/
│   └── fuel_prices.csv          # Provided data
├── config/                       # Django project config
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── fuel_optimizer/               # Django app
    ├── __init__.py
    ├── apps.py
    ├── urls.py
    ├── views.py
    ├── serializers.py
    ├── services/
    │   ├── __init__.py
    │   ├── routing.py           # OSRM integration
    │   ├── fuel_stations.py     # Station data + spatial index
    │   └── optimizer.py         # Core optimization logic
    └── tests/
        └── test_api.py
```

---

## Step-by-Step Implementation Guide

### Phase 1: Django Setup (Compare to FastAPI)
```bash
# FastAPI: pip install fastapi uvicorn
# Django equivalent:
uv add django djangorestframework

# FastAPI: Create main.py with FastAPI()
# Django: Create project structure
uv run django-admin startproject config .
uv run python manage.py startapp fuel_optimizer
```

### Phase 2: Configure Django (settings.py)
```python
# Like FastAPI's app configuration, but in settings.py
INSTALLED_APPS = [
    # ... django defaults ...
    'rest_framework',       # Like adding APIRouter
    'fuel_optimizer',       # Your app (like including a router)
]

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',  # JSON responses
    ]
}
```

### Phase 3: Create API Views (views.py)
```python
# FastAPI pattern you know:
# @app.post("/route")
# async def get_route(request: RouteRequest): ...

# Django REST Framework equivalent:
from rest_framework.views import APIView
from rest_framework.response import Response

class RouteView(APIView):
    def post(self, request):
        # request.data is like FastAPI's parsed body
        start = request.data.get('start')
        end = request.data.get('end')
        # ... process and return
        return Response({"route": route_data})
```

### Phase 4: URL Routing (urls.py)
```python
# FastAPI: Decorators on functions
# Django: Explicit URL patterns

# fuel_optimizer/urls.py
from django.urls import path
from .views import RouteView

urlpatterns = [
    path('route/', RouteView.as_view(), name='route'),
]

# config/urls.py (root router)
from django.urls import path, include

urlpatterns = [
    path('api/', include('fuel_optimizer.urls')),
]
```

---

## Key Django Concepts to Learn

### 1. Apps vs Projects
- **Project** (`config/`): Settings, root URLs - like your FastAPI main.py
- **App** (`fuel_optimizer/`): Feature module - like a FastAPI router

### 2. Views (Your Endpoints)
```python
# Function-based (simple, like FastAPI)
def my_view(request):
    return JsonResponse({"data": "value"})

# Class-based (more features, recommended for APIs)
class MyView(APIView):
    def get(self, request):
        return Response({"data": "value"})
    
    def post(self, request):
        return Response({"created": True})
```

### 3. Serializers (Like Pydantic)
```python
from rest_framework import serializers

class RouteRequestSerializer(serializers.Serializer):
    start = serializers.CharField(max_length=200)
    end = serializers.CharField(max_length=200)
    
    def validate_start(self, value):
        # Custom validation (like Pydantic validators)
        if not value:
            raise serializers.ValidationError("Start required")
        return value
```

### 4. Django ORM (If needed later)
```python
# Very similar to SQLAlchemy
class FuelStation(models.Model):
    name = models.CharField(max_length=200)
    latitude = models.FloatField()
    longitude = models.FloatField()
    price = models.DecimalField(max_digits=5, decimal_places=3)
```

---

## API Contract

### Endpoint: POST /api/route/

**Request:**
```json
{
    "start": "New York, NY",
    "end": "Los Angeles, CA"
}
```

**Response:**
```json
{
    "route": {
        "distance_miles": 2789.5,
        "duration_hours": 40.2,
        "geometry": {
            "type": "LineString",
            "coordinates": [[...]]
        }
    },
    "fuel_stops": [
        {
            "name": "PILOT TRAVEL CENTER #123",
            "address": "I-80, EXIT 45",
            "city": "Toledo",
            "state": "OH",
            "price_per_gallon": 3.25,
            "gallons_needed": 50,
            "cost": 162.50,
            "miles_from_start": 450
        }
    ],
    "total_fuel_cost": 812.50,
    "total_gallons": 278.95
}
```

---

## Development Workflow

### Commands You'll Use Often
```bash
# Start dev server (like: uvicorn main:app --reload)
uv run python manage.py runserver

# Create new app (like creating a new router module)
uv run python manage.py startapp appname

# Django shell (interactive Python with Django loaded)
uv run python manage.py shell

# Run tests
uv run pytest
```

### Environment Variables (.env)
```bash
DEBUG=True
SECRET_KEY=your-secret-key-here
# No API keys needed - OSRM is free!
```

---

## Testing Strategy

### Test the API
```python
# tests/test_api.py
from rest_framework.test import APITestCase

class RouteAPITest(APITestCase):
    def test_route_calculation(self):
        response = self.client.post('/api/route/', {
            'start': 'New York, NY',
            'end': 'Philadelphia, PA'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('fuel_stops', response.data)
        self.assertIn('total_fuel_cost', response.data)
```

---

## Common Gotchas (FastAPI → Django)

1. **No async by default**: Django views are sync. DRF works great synchronously.
2. **URL trailing slashes**: Django expects `/api/route/` not `/api/route`
3. **CSRF protection**: Disable for API-only apps or use DRF's auth
4. **Request data access**: `request.data` (DRF) vs `request.POST` (vanilla Django)
5. **JSON responses**: Use `Response()` from DRF, not `JsonResponse()`

---

## Coding Standards

- **Linting**: Ruff (same as your FastAPI projects)
- **Type hints**: Use throughout for Pyright/mypy
- **Docstrings**: Google style for all functions
- **Error handling**: DRF exceptions for API errors
- **Logging**: Use Django's built-in logging

```python
import logging
logger = logging.getLogger(__name__)

class RouteView(APIView):
    def post(self, request):
        logger.info(f"Route request: {request.data}")
        try:
            result = calculate_route(...)
            return Response(result)
        except ValidationError as e:
            logger.warning(f"Validation failed: {e}")
            raise
```

---

## Ready to Start?

Follow this order:
1. Initialize project with uv
2. Set up Django project structure
3. Load fuel station data with spatial index
4. Implement OSRM routing service
5. Build optimization logic
6. Create API endpoint
7. Test with Postman

Each step will include FastAPI comparisons to help you understand Django patterns!
