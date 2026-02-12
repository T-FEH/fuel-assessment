"""
API Views for Fuel Route Optimizer - Version 2 (Optimized).

Django REST Framework Views for the optimized fuel route calculation.

This implementation uses:
- Dynamic Programming for globally optimal fuel stops
- Pre-geocoded database with spatial indexing
- Geometric route filtering (perpendicular distance)
- Exactly 3 API calls per request

FastAPI Comparison:
- FastAPI: @app.post("/route") → async def calculate_route(request: RouteRequest)
- DRF: class RouteView(APIView) → def post(self, request)

Key differences:
1. DRF views are classes with methods for each HTTP verb
2. request.data is like FastAPI's parsed request body
3. Serializers replace Pydantic for validation
4. Response() instead of direct return
5. raise_exception=True is like FastAPI's automatic 422 errors
"""
import logging
import time

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import RouteRequestSerializer
from .services.optimizer_v2 import optimize_fuel_route_v2

logger = logging.getLogger(__name__)


class RouteView(APIView):
    """
    PRODUCTION-READY route optimization endpoint.
    
    POST /api/route/
    
    Features:
    - Pre-geocoded database (6,966 fuel stations)
    - Geometric route filtering (15-mile corridor)
    - Dynamic programming for global optimum
    - Exactly 3 API calls: 2 for geocoding + 1 for routing
    
    Algorithm:
    - Uses Dijkstra-like DP to find minimum cost path
    - Considers vehicle constraints (500-mile range, 10 mpg)
    - Returns optimal sequence of fuel stops with total cost
    """
    
    def post(self, request):
        """Calculate optimal fuel stops for a route using DP algorithm."""
        start_time = time.time()
        
        # Validate request
        serializer = RouteRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation failed", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        start = serializer.validated_data['start']
        end = serializer.validated_data['end']
        
        logger.info(f"Route request: {start} → {end}")
        
        try:
            # Call optimized service
            result = optimize_fuel_route_v2(start, end)
            
            elapsed = time.time() - start_time
            logger.info(f"Optimized in {elapsed:.2f}s using {result['optimization_method']}")
            
            # Add metadata
            result['processing_time_seconds'] = round(elapsed, 2)
            result['api_version'] = 'v2'
            
            return Response(result, status=status.HTTP_200_OK)
            
        except ValueError as e:
            logger.warning(f"Route calculation failed: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return Response(
                {"error": "An unexpected error occurred", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class HealthView(APIView):
    """
    Health check endpoint for monitoring and deployment.
    
    GET /api/health/
    
    Returns service status and geocoded station count.
    """
    
    def get(self, request):
        """Return health status."""
        from .models import FuelStation
        
        total = FuelStation.objects.count()
        geocoded = FuelStation.objects.filter(geocoded=True).count()
        
        return Response({
            "status": "healthy",
            "service": "fuel-route-optimizer",
            "version": "2.0",
            "database": {
                "total_stations": total,
                "geocoded_stations": geocoded,
                "pending_geocoding": total - geocoded
            }
        })

