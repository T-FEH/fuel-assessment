"""
OSRM Routing Service.

Integrates with Open Source Routing Machine (OSRM) for route calculation.
OSRM is completely free with no API key required.

Key features:
- Single API call for complete route
- Returns GeoJSON geometry + distance + duration
- Demo server: router.project-osrm.org

FastAPI comparison:
- This would be similar to an external API client dependency
- In FastAPI: Depends(get_osrm_client)
- Here: Singleton service with methods
"""
import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import requests
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


@dataclass
class RoutePoint:
    """A point along the route with distance from start."""
    latitude: float
    longitude: float
    distance_from_start_miles: float


@dataclass
class RouteResult:
    """Result from OSRM route calculation."""
    distance_miles: float
    duration_hours: float
    geometry: dict  # GeoJSON LineString
    coordinates: list[tuple[float, float]]  # List of (lon, lat) points
    start_coords: tuple[float, float]  # (lat, lon)
    end_coords: tuple[float, float]  # (lat, lon)


class OSRMRoutingService:
    """
    Service for route calculation using OSRM public API.
    
    OSRM (Open Source Routing Machine) provides:
    - Free unlimited API access
    - Fast route calculation
    - GeoJSON geometry output
    - Distance and duration estimates
    """
    
    OSRM_BASE_URL = "https://router.project-osrm.org/route/v1"
    
    def __init__(self):
        # Geocoder for converting addresses to coordinates
        self._geocoder = Nominatim(user_agent="fuel_route_optimizer_v1")
        self._rate_limited_geocode = RateLimiter(
            self._geocoder.geocode,
            min_delay_seconds=1.0,
            max_retries=2
        )
        
    def geocode_address(self, address: str) -> Optional[tuple[float, float]]:
        """
        Convert an address string to coordinates.
        
        Args:
            address: Address string (e.g., "New York, NY" or "123 Main St, Boston, MA")
            
        Returns:
            Tuple of (latitude, longitude) or None if geocoding fails
        """
        try:
            # Add USA to help with geocoding
            query = f"{address}, USA"
            location = self._rate_limited_geocode(query)
            
            if location:
                logger.info(f"Geocoded '{address}' to ({location.latitude}, {location.longitude})")
                return (location.latitude, location.longitude)
            else:
                logger.warning(f"Could not geocode address: {address}")
                return None
                
        except Exception as e:
            logger.error(f"Geocoding error for '{address}': {e}")
            return None
    
    def get_route(
        self, 
        start_lat: float, 
        start_lon: float, 
        end_lat: float, 
        end_lon: float
    ) -> Optional[RouteResult]:
        """
        Get route between two coordinate points.
        
        Makes a SINGLE call to OSRM API to get:
        - Route geometry (for mapping)
        - Total distance and duration
        - Waypoint coordinates
        
        Args:
            start_lat, start_lon: Starting point coordinates
            end_lat, end_lon: Ending point coordinates
            
        Returns:
            RouteResult with route details or None if routing fails
        """
        # OSRM expects coordinates as: lon,lat;lon,lat
        url = f"{self.OSRM_BASE_URL}/driving/{start_lon},{start_lat};{end_lon},{end_lat}"
        
        params = {
            "overview": "full",      # Full route geometry
            "geometries": "geojson", # GeoJSON format
            "steps": "false",        # We don't need turn-by-turn
            "annotations": "false"   # No extra annotations needed
        }
        
        try:
            logger.info(f"Calling OSRM API for route: ({start_lat},{start_lon}) -> ({end_lat},{end_lon})")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("code") != "Ok":
                logger.error(f"OSRM error: {data.get('message', 'Unknown error')}")
                return None
            
            route = data["routes"][0]
            
            # Distance in meters -> miles
            distance_miles = route["distance"] / 1609.344
            
            # Duration in seconds -> hours
            duration_hours = route["duration"] / 3600
            
            # GeoJSON geometry
            geometry = route["geometry"]
            
            # Coordinates array from geometry
            coordinates = geometry.get("coordinates", [])
            
            result = RouteResult(
                distance_miles=round(distance_miles, 2),
                duration_hours=round(duration_hours, 2),
                geometry=geometry,
                coordinates=coordinates,
                start_coords=(start_lat, start_lon),
                end_coords=(end_lat, end_lon)
            )
            
            logger.info(f"Route calculated: {result.distance_miles} miles, {result.duration_hours} hours")
            return result
            
        except requests.RequestException as e:
            logger.error(f"OSRM API error: {e}")
            return None
        except (KeyError, IndexError) as e:
            logger.error(f"Error parsing OSRM response: {e}")
            return None
    
    def get_route_from_addresses(
        self, 
        start_address: str, 
        end_address: str
    ) -> Optional[RouteResult]:
        """
        Get route between two address strings.
        
        Geocodes addresses first, then calls OSRM.
        This makes 2 geocoding calls + 1 OSRM call = 3 API calls total.
        
        Args:
            start_address: Starting location string
            end_address: Ending location string
            
        Returns:
            RouteResult or None if geocoding/routing fails
        """
        # Geocode start location
        start_coords = self.geocode_address(start_address)
        if not start_coords:
            raise ValueError(f"Could not geocode start location: {start_address}")
        
        # Geocode end location
        end_coords = self.geocode_address(end_address)
        if not end_coords:
            raise ValueError(f"Could not geocode end location: {end_address}")
        
        # Get route
        return self.get_route(
            start_lat=start_coords[0],
            start_lon=start_coords[1],
            end_lat=end_coords[0],
            end_lon=end_coords[1]
        )
    
    def sample_points_along_route(
        self, 
        route: RouteResult, 
        interval_miles: float = 400.0
    ) -> list[RoutePoint]:
        """
        Sample points along the route at regular intervals.
        
        Used to determine where fuel stops should be placed.
        These points are where we'll search for nearby fuel stations.
        
        Args:
            route: RouteResult from get_route()
            interval_miles: Distance between sample points (default 400 miles)
            
        Returns:
            List of RoutePoint objects at each interval
        """
        if not route.coordinates:
            return []
        
        coords = route.coordinates  # List of [lon, lat]
        points = []
        
        # Calculate cumulative distances along the route
        cumulative_distance = 0.0
        next_sample_distance = interval_miles
        
        for i in range(len(coords) - 1):
            lon1, lat1 = coords[i]
            lon2, lat2 = coords[i + 1]
            
            # Haversine distance between consecutive points
            segment_distance = self._haversine_miles(lat1, lon1, lat2, lon2)
            cumulative_distance += segment_distance
            
            # Check if we've passed a sample point
            while cumulative_distance >= next_sample_distance:
                # Interpolate to find exact position
                # Simple approach: use the endpoint of this segment
                points.append(RoutePoint(
                    latitude=lat2,
                    longitude=lon2,
                    distance_from_start_miles=next_sample_distance
                ))
                next_sample_distance += interval_miles
        
        logger.info(f"Sampled {len(points)} points along {route.distance_miles} mile route")
        return points
    
    def get_states_along_route(self, route: RouteResult) -> list[str]:
        """
        Determine which US states the route passes through.
        
        Uses reverse geocoding on sample points to identify states.
        This helps filter fuel stations to only those in relevant states.
        
        Args:
            route: RouteResult from get_route()
            
        Returns:
            List of state abbreviations (e.g., ["NY", "PA", "OH"])
        """
        states = set()
        
        # Sample fewer points for state detection (every ~200 miles)
        coords = route.coordinates
        step = max(1, len(coords) // 20)  # About 20 sample points
        
        for i in range(0, len(coords), step):
            lon, lat = coords[i]
            try:
                location = self._geocoder.reverse(
                    f"{lat}, {lon}",
                    language="en",
                    addressdetails=True
                )
                if location and location.raw.get('address'):
                    # Try different keys for state
                    address = location.raw['address']
                    state = address.get('state') or address.get('ISO3166-2-lvl4', '')
                    
                    # Convert state name to abbreviation
                    if state:
                        abbrev = self._state_to_abbrev(state)
                        if abbrev:
                            states.add(abbrev)
            except Exception as e:
                logger.debug(f"Could not reverse geocode ({lat}, {lon}): {e}")
                continue
        
        result = sorted(list(states))
        logger.info(f"Route passes through states: {result}")
        return result
    
    @staticmethod
    def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate the great-circle distance between two points in miles."""
        R = 3959.0  # Earth's radius in miles
        
        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        delta_lat = np.radians(lat2 - lat1)
        delta_lon = np.radians(lon2 - lon1)
        
        a = (np.sin(delta_lat / 2) ** 2 + 
             np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon / 2) ** 2)
        c = 2 * np.arcsin(np.sqrt(a))
        
        return R * c
    
    @staticmethod
    def _state_to_abbrev(state_name: str) -> Optional[str]:
        """Convert state name to two-letter abbreviation."""
        states = {
            'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
            'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
            'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
            'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
            'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
            'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
            'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
            'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
            'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
            'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
            'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
            'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
            'wisconsin': 'WI', 'wyoming': 'WY', 'district of columbia': 'DC'
        }
        
        # Handle already-abbreviated or ISO format
        if len(state_name) == 2:
            return state_name.upper()
        if state_name.startswith('US-'):
            return state_name[3:].upper()
            
        return states.get(state_name.lower())


# Singleton instance
routing_service = OSRMRoutingService()
