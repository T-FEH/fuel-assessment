"""
URL configuration for config project.
This is like FastAPI's main app where you include routers.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Include fuel_optimizer URLs (like: app.include_router(router, prefix="/api"))
    path('api/', include('fuel_optimizer.urls')),
]
