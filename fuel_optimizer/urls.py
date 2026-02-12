"""
URL patterns for fuel_optimizer app - Version 2 (Optimized).

Django URL routing configuration for the production-ready API.

All endpoints use the optimized V2 implementation with:
- Dynamic Programming optimization
- Pre-geocoded database
- Geometric route filtering

Django vs FastAPI routing pattern:
- FastAPI: @app.post("/route") decorator directly on function
- Django: Separate URL configuration mapping paths to views
"""
from django.urls import path
from .views import RouteView, HealthView

app_name = 'fuel_optimizer'

urlpatterns = [
    # Main optimized route calculation endpoint
    # POST /api/route/ → RouteView.post()
    # Uses DP algorithm with pre-geocoded database
    path('route/', RouteView.as_view(), name='route'),
    
    # Health check for monitoring
    # GET /api/health/ → HealthView.get()
    path('health/', HealthView.as_view(), name='health'),
]

