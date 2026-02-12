"""
Geometric utilities for route analysis.

Provides functions to:
1. Decode polyline from OSRM
2. Calculate perpendicular distance from point to route
3. Find stations along the route geometrically
"""
import numpy as np
from typing import List, Tuple


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points in miles.
    
    Uses the Haversine formula for accuracy over Earth's surface.
    """
    R = 3959.0  # Earth's radius in miles
    
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    delta_lat = np.radians(lat2 - lat1)
    delta_lon = np.radians(lon2 - lon1)
    
    a = (np.sin(delta_lat / 2) ** 2 + 
         np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon / 2) ** 2)
    c = 2 * np.arcsin(np.sqrt(a))
    
    return R * c


def point_to_segment_distance(
    point_lat: float,
    point_lon: float,
    seg_start_lat: float,
    seg_start_lon: float,
    seg_end_lat: float,
    seg_end_lon: float
) -> float:
    """
    Calculate perpendicular distance from a point to a line segment in miles.
    
    This is the key function for determining if a station is "along the route".
    
    Args:
        point_lat, point_lon: Coordinates of the point (fuel station)
        seg_start_lat, seg_start_lon: Start of line segment (route segment) 
        seg_end_lat, seg_end_lon: End of line segment
        
    Returns:
        Perpendicular distance in miles
    """
    # Convert to radians for calculation
    px, py = np.radians(point_lon), np.radians(point_lat)
    ax, ay = np.radians(seg_start_lon), np.radians(seg_start_lat)
    bx, by = np.radians(seg_end_lon), np.radians(seg_end_lat)
    
    # Vector from A to B (segment)
    ab_x = bx - ax
    ab_y = by - ay
    
    # Vector from A to P (point)
    ap_x = px - ax
    ap_y = py - ay
    
    # Calculate projection parameter t
    ab_dot_ab = ab_x ** 2 + ab_y ** 2
    
    if ab_dot_ab == 0:
        # Segment is a point
        return haversine_distance(point_lat, point_lon, seg_start_lat, seg_start_lon)
    
    t = (ap_x * ab_x + ap_y * ab_y) / ab_dot_ab
    
    # Clamp t to [0, 1] to stay on segment
    t = max(0, min(1, t))
    
    # Find closest point on segment
    closest_x = ax + t * ab_x
    closest_y = ay + t * ab_y
    
    # Convert back to degrees
    closest_lat = np.degrees(closest_y)
    closest_lon = np.degrees(closest_x)
    
    # Calculate distance
    return haversine_distance(point_lat, point_lon, closest_lat, closest_lon)


def find_stations_along_route(
    route_coordinates: List[Tuple[float, float]],  # List of (lon, lat) from OSRM
    stations: List,  # QuerySet orlist of FuelStation objects
    max_distance_miles: float = 15.0
) -> List[Tuple[object, float]]:
    """
    Find all fuel stations within max_distance of the route polyline.
    
    This is the GEOMETRIC APPROACH (more accurate than radius search).
    
    For each station:
        1. Check distance to each route segment
        2. If any segment is within max_distance, station is "on route"
        3. Calculate chainage (distance along route to nearest point)
    
    Args:
        route_coordinates: List of (longitude, latitude) pairs from routing API
        stations: List/QuerySet of FuelStation objects with lat/lon
        max_distance_miles: Maximum perpendicular distance to consider "on route"
        
    Returns:
        List of (station, chainage_miles) tuples sorted by chainage
    """
    on_route_stations = []
    
    # Pre-calculate cumulative distances along route
    cumulative_distances = [0.0]
    for i in range(len(route_coordinates) - 1):
        lon1, lat1 = route_coordinates[i]
        lon2, lat2 = route_coordinates[i + 1]
        segment_distance = haversine_distance(lat1, lon1, lat2, lon2)
        cumulative_distances.append(cumulative_distances[-1] + segment_distance)
    
    # Check each station
    for station in stations:
        if not station.geocoded or station.latitude is None:
            continue
        
        min_distance = float('inf')
        best_chainage = 0.0
        
        # Check distance to each route segment
        for i in range(len(route_coordinates) - 1):
            lon1, lat1 = route_coordinates[i]
            lon2, lat2 = route_coordinates[i + 1]
            
            distance = point_to_segment_distance(
                station.latitude, station.longitude,
                lat1, lon1,
                lat2, lon2
            )
            
            if distance < min_distance:
                min_distance = distance
                # Chainage is cumulative distance to start of this segment
                best_chainage = cumulative_distances[i]
        
        # If station is within max_distance of route, include it
        if min_distance <= max_distance_miles:
            on_route_stations.append((station, best_chainage))
    
    # Sort by chainage (distance from start)
    on_route_stations.sort(key=lambda x: x[1])
    
    return on_route_stations


def calculate_cumulative_distance_at_point(
    route_coordinates: List[Tuple[float, float]],
    target_lat: float,
    target_lon: float
) -> float:
    """
    Calculate how far along the route a specific point is (chainage).
    
    Returns:
        Distance in miles from route start to the nearest point on route
    """
    cumulative = 0.0
    min_distance = float('inf')
    best_chainage = 0.0
    
    for i in range(len(route_coordinates) - 1):
        lon1, lat1 = route_coordinates[i]
        lon2, lat2 = route_coordinates[i + 1]
        
        # Distance for this segment
        segment_distance = haversine_distance(lat1, lon1, lat2, lon2)
        
        # Check if target point is near this segment
        distance = point_to_segment_distance(
            target_lat, target_lon,
            lat1, lon1,
            lat2, lon2
        )
        
        if distance < min_distance:
            min_distance = distance
            best_chainage = cumulative
        
        cumulative += segment_distance
    
    return best_chainage
