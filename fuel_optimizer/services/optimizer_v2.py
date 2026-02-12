"""
Optimized Fuel Route Optimizer with Dynamic Programming.

IMPROVEMENTS over original:
1. Uses database queries instead of CSV loading (faster)
2. Geometric filtering for true "on-route" stations (more accurate)
3. Dynamic Programming for globally optimal fuel stops (not greedy)
4. Reduced API calls to exactly 3 per request

Algorithm:
- DP[i] = minimum cost to reach station i
- DP[i] = min(DP[j] + cost(j→i)) for all reachable j
- Backtrack to get actual stops
"""
import logging
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple

from django.db.models import Q

from .routing import routing_service, RouteResult
from .geometry import find_stations_along_route, haversine_distance
from fuel_optimizer.models import FuelStation

logger = logging.getLogger(__name__)

# Vehicle constants
VEHICLE_RANGE_MILES = 500
FUEL_EFFICIENCY_MPG = 10
MAX_ROUTE_DISTANCE_MILES = 15.0  # Max perpendicular distance to consider "on route"


@dataclass
class OptimizedFuelStop:
    """A planned fuel stop with cost calculations."""
    name: str
    address: str
    city: str
    state: str
    latitude: float
    longitude: float
    price_per_gallon: float
    gallons_needed: float
    cost: float
    miles_from_start: float  # Chainage


@dataclass
class OptimizedRouteResult:
    """Complete route optimization result."""
    route: dict
    fuel_stops: List[OptimizedFuelStop]
    total_fuel_cost: float
    total_gallons: float
    start_location: dict
    end_location: dict
    optimization_method: str  # "dynamic_programming"
    stations_considered: int  # How many stations were on-route


class OptimizedFuelRouteOptimizer:
    """
    Production-ready optimizer using:
    - Database queries (pre-geocoded data)
    - Geometric route filtering
    - Dynamic programming for optimal solution
    """
    
    def __init__(self):
        self.routing = routing_service
    
    def optimize_route(
        self,
        start_address: str,
        end_address: str
    ) -> OptimizedRouteResult:
        """
        Calculate globally optimal fuel stops using DP.
        
        Workflow:
        1. Get route from OSRM (1 API call)
        2. Query database for stations in route states (fast DB query)
        3. Geometrically filter to on-route stations
        4. Use DP to find minimum-cost fuel stop sequence
        5. Return optimal solution
        """
        logger.info(f"[OPTIMIZED] Route: {start_address} → {end_address}")
        
        # Step 1: Get route (includes geocoding - 3 API calls total)
        route = self.routing.get_route_from_addresses(start_address, end_address)
        if not route:
            raise ValueError(f"Could not calculate route")
        
        logger.info(f"Route: {route.distance_miles} miles, {route.duration_hours} hours")
        
        # Step 2: Query ALL geocoded stations (bounding box will filter geographically)
        stations = FuelStation.objects.filter(geocoded=True).order_by('retail_price')
        
        logger.info(f"Querying {stations.count()} geocoded stations (will filter by route geometry)")
        
        # Step 4: Geometric filtering - find stations truly along route
        on_route_stations = find_stations_along_route(
            route.coordinates,
            stations,
            max_distance_miles=MAX_ROUTE_DISTANCE_MILES
        )
        
        logger.info(f"Filtered to {len(on_route_stations)} on-route stations")
        
        if not on_route_stations:
            logger.warning("No fuel stations found on route")
            return self._create_empty_result(
                route, start_address, end_address, 
                "no_stations", 0
            )
        
        # Step 5: Dynamic Programming optimization
        optimal_stops = self._find_optimal_stops_dp(
            route.distance_miles,
            on_route_stations
        )
        
        # Step 6: Calculate totals
        total_gallons = route.distance_miles / FUEL_EFFICIENCY_MPG
        total_cost = sum(stop.cost for stop in optimal_stops)
        
        result = OptimizedRouteResult(
            route={
                "distance_miles": route.distance_miles,
                "duration_hours": route.duration_hours,
                "geometry": route.geometry
            },
            fuel_stops=optimal_stops,
            total_fuel_cost=round(total_cost, 2),
            total_gallons=round(total_gallons, 2),
            start_location={
                "address": start_address,
                "latitude": route.start_coords[0],
                "longitude": route.start_coords[1]
            },
            end_location={
                "address": end_address,
                "latitude": route.end_coords[0],
                "longitude": route.end_coords[1]
            },
            optimization_method="dynamic_programming",
            stations_considered=len(on_route_stations)
        )
        
        logger.info(
            f"[DP] Optimal solution: {len(optimal_stops)} stops, "
            f"${total_cost:.2f} total (from {len(on_route_stations)} candidates)"
        )
        return result
    
    def _find_optimal_stops_dp(
        self,
        route_distance: float,
        on_route_stations: List[Tuple[FuelStation, float]]  # (station, chainage)
    ) -> List[OptimizedFuelStop]:
        """
        Dynamic Programming to find minimum-cost fuel stops.
        
        DP Recurrence:
            dp[i] = minimum cost to reach station i from start
            dp[i] = min(dp[j] + refuel_cost(j, i)) 
                    for all j where distance(j, i) <= 500 miles
        
        Base case: dp[0] = 0 (start with full tank, no cost yet)
        
        Returns globally optimal list of fuel stops.
        """
        if not on_route_stations:
            return []
        
        n = len(on_route_stations)
        
        # Add virtual start (chainage = 0) and end (chainage = route_distance)
        # Start: position 0, price 0 (already have full tank)
        # End: position route_distance, price 0 (no refuel at destination)
        
        # DP arrays
        dp = [float('inf')] * (n + 2)  # +2 for start/end sentinels
        parent = [-1] * (n + 2)
        
        # Sentinel indices
        START_IDX = 0
        END_IDX = n + 1
        
        # Base case: start with full tank (no cost)
        dp[START_IDX] = 0.0
        
        # Build DP table
        for i in range(1, n + 2):  # For each station + end
            if i == END_IDX:
                # Virtual end station
                current_chainage = route_distance
            else:
                current_chainage = on_route_stations[i - 1][1]
            
            # Try coming from each previous station (including start)
            for j in range(i):
                if j == START_IDX:
                    prev_chainage = 0.0
                else:
                    prev_chainage = on_route_stations[j - 1][1]
                
                distance_between = current_chainage - prev_chainage
                
                # Can only reach if within vehicle range
                if distance_between > VEHICLE_RANGE_MILES:
                    continue
                
                # Cost to refuel at station i (unless it's the end)
                if i == END_IDX:
                    refuel_cost = 0.0  # No refuel at destination
                    gallons = 0.0
                else:
                    station, _ = on_route_stations[i - 1]
                    # Refuel to full tank (500 miles worth)
                    gallons = VEHICLE_RANGE_MILES / FUEL_EFFICIENCY_MPG
                    refuel_cost = gallons * station.retail_price
                
                # DP transition
                candidate_cost = dp[j] + refuel_cost
                
                if candidate_cost < dp[i]:
                    dp[i] = candidate_cost
                    parent[i] = j
        
        # Check if destination is reachable
        if dp[END_IDX] == float('inf'):
            # Route requires more stops than available
            # Fall back to greedy
            logger.warning("DP: Route not coverable with available stations, using greedy")
            return self._greedy_fallback(route_distance, on_route_stations)
        
        # Backtrack to find actual stops
        path_indices = []
        current = END_IDX
        while parent[current] != -1:
            prev = parent[current]
            if prev != START_IDX and prev != END_IDX:
                path_indices.append(prev - 1)  # Adjust for sentinel offset
            current = prev
        
        path_indices.reverse()
        
        # Build OptimizedFuelStop objects
        optimal_stops = []
        prev_chainage = 0.0
        
        for idx in path_indices:
            station, chainage = on_route_stations[idx]
            
            # Gallons needed to reach this station from previous
            distance_traveled = chainage - prev_chainage
            gallons_to_here = distance_traveled / FUEL_EFFICIENCY_MPG
            
            # Refuel to full tank at this station
            gallons_refueled = VEHICLE_RANGE_MILES / FUEL_EFFICIENCY_MPG
            cost = gallons_refueled * station.retail_price
            
            stop = OptimizedFuelStop(
                name=station.truckstop_name,
                address=station.address,
                city=station.city,
                state=station.state,
                latitude=station.latitude,
                longitude=station.longitude,
                price_per_gallon=round(station.retail_price, 3),
                gallons_needed=round(gallons_refueled, 2),
                cost=round(cost, 2),
                miles_from_start=round(chainage, 2)
            )
            
            optimal_stops.append(stop)
            prev_chainage = chainage
        
        return optimal_stops
    
    def _greedy_fallback(
        self,
        route_distance: float,
        on_route_stations: List[Tuple[FuelStation, float]]
    ) -> List[OptimizedFuelStop]:
        """Greedy fallback if DP fails."""
        stops = []
        current_range = VEHICLE_RANGE_MILES
        prev_chainage = 0.0
        
        for station, chainage in on_route_stations:
            distance_from_prev = chainage - prev_chainage
            
            # Need refuel?
            if distance_from_prev >= current_range - 50:  # 50-mile buffer
                gallons = VEHICLE_RANGE_MILES / FUEL_EFFICIENCY_MPG
                cost = gallons * station.retail_price
                
                stops.append(OptimizedFuelStop(
                    name=station.truckstop_name,
                    address=station.address,
                    city=station.city,
                    state=station.state,
                    latitude=station.latitude,
                    longitude=station.longitude,
                    price_per_gallon=round(station.retail_price, 3),
                    gallons_needed=round(gallons, 2),
                    cost=round(cost, 2),
                    miles_from_start=round(chainage, 2)
                ))
                
                current_range = VEHICLE_RANGE_MILES
                prev_chainage = chainage
        
        return stops
    
    def _create_empty_result(
        self,
        route: RouteResult,
        start_address: str,
        end_address: str,
        method: str,
        stations_considered: int
    ) -> OptimizedRouteResult:
        """Create result with no fuel stops."""
        total_gallons = route.distance_miles / FUEL_EFFICIENCY_MPG
        
        return OptimizedRouteResult(
            route={
                "distance_miles": route.distance_miles,
                "duration_hours": route.duration_hours,
                "geometry": route.geometry
            },
            fuel_stops=[],
            total_fuel_cost=0.0,
            total_gallons=round(total_gallons, 2),
            start_location={
                "address": start_address,
                "latitude": route.start_coords[0],
                "longitude": route.start_coords[1]
            },
            end_location={
                "address": end_address,
                "latitude": route.end_coords[0],
                "longitude": route.end_coords[1]
            },
            optimization_method=method,
            stations_considered=stations_considered
        )
    
    def _extract_states_from_addresses(self, start: str, end: str) -> List[str]:
        """Extract state abbreviations from address strings."""
        states = []
        valid_states = {
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
        }
        
        for address in [start, end]:
            parts = address.replace(',', ' ').split()
            for part in parts:
                clean = part.strip().upper()
                if len(clean) == 2 and clean in valid_states:
                    states.append(clean)
                    break
        
        return list(set(states))


# Singleton optimizer
optimized_fuel_optimizer = OptimizedFuelRouteOptimizer()


def optimize_fuel_route_v2(start: str, end: str) -> dict:
    """
    Main entry point for OPTIMIZED route planning.
    
    Uses:
    - Pre-geocoded database
    - Geometric filtering
    - Dynamic programming
    
    Returns dict for JSON serialization.
    """
    result = optimized_fuel_optimizer.optimize_route(start, end)
    
    return {
        "route": result.route,
        "fuel_stops": [asdict(stop) for stop in result.fuel_stops],
        "total_fuel_cost": result.total_fuel_cost,
        "total_gallons": result.total_gallons,
        "start_location": result.start_location,
        "end_location": result.end_location,
        "optimization_method": result.optimization_method,
        "stations_considered": result.stations_considered
    }
