"""
Fuel Optimizer Services - Version 2 (Optimized).

Core business logic services for production-ready route optimization:
- routing: OSRM integration for route calculation (3 API calls total)
- geometry: Geometric utilities for route filtering
- optimizer_v2: Dynamic programming optimization with global optimum
"""
from .optimizer_v2 import optimize_fuel_route_v2
from .routing import routing_service
from .geometry import find_stations_along_route

__all__ = ['optimize_fuel_route_v2', 'routing_service', 'find_stations_along_route']