# 📡 API Endpoints Documentation

Complete reference for all Fuel Route Optimizer API endpoints.

**Base URL**: `http://127.0.0.1:8000/api/`  
**Version**: 2.0 (Optimized with Dynamic Programming)

---

## Endpoints Overview

| Endpoint | Method | Purpose | Response Time |
|----------|--------|---------|---------------|
| `/health/` | GET | Service health check | < 100ms |
| `/route/` | POST | Calculate optimal fuel route | 1-3 seconds |

---

## 1. Health Check

### `GET /api/health/`

Check if the API is running and get database statistics.

#### Request

```http
GET /api/health/ HTTP/1.1
Host: 127.0.0.1:8000
```

**No parameters required**

#### Response (200 OK)

```json
{
    "status": "healthy",
    "service": "fuel-route-optimizer",
    "version": "2.0",
    "database": {
        "total_stations": 6966,
        "geocoded_stations": 6934,
        "pending_geocoding": 32
    }
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Always "healthy" if API is running |
| `service` | string | Service identifier |
| `version` | string | API version (2.0 = optimized DP algorithm) |
| `database.total_stations` | integer | Total fuel stations in database |
| `database.geocoded_stations` | integer | Stations with lat/lon coordinates |
| `database.pending_geocoding` | integer | Stations awaiting geocoding |

#### Use Cases

- **Monitoring**: Check if service is alive in production
- **Deployment**: Verify successful deployment
- **Debugging**: Confirm database is populated with geocoded stations

---

## 2. Optimal Route Calculation

### `POST /api/route/`

Calculate the most cost-effective fuel stops for a route using dynamic programming.

#### Request

```http
POST /api/route/ HTTP/1.1
Host: 127.0.0.1:8000
Content-Type: application/json

{
    "start": "New York, NY",
    "end": "Los Angeles, CA"
}
```

#### Request Body Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `start` | string | ✅ Yes | Starting location (city, state or full address) | "New York, NY" |
| `end` | string | ✅ Yes | Destination location (city, state or full address) | "Los Angeles, CA" |

**Constraints**:
- Both locations must be in the United States
- Use standard state abbreviations (NY, CA, TX, etc.)
- Format: "City, STATE" or full address

#### Response (200 OK)

##### Short Route Example (< 500 miles, no fuel stops)

```json
{
    "route": {
        "distance_miles": 95.3,
        "duration_hours": 1.6,
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [-74.006, 40.7128],
                [-75.1652, 39.9526]
            ]
        }
    },
    "fuel_stops": [],
    "total_fuel_cost": 0,
    "total_gallons": 9.53,
    "optimization_method": "dynamic_programming",
    "processing_time_seconds": 0.85,
    "api_version": "v2",
    "explanation": "Route is within vehicle range (500 miles). No fuel stops needed."
}
```

##### Long Route Example (> 500 miles, multiple fuel stops)

```json
{
    "route": {
        "distance_miles": 2789.4,
        "duration_hours": 40.2,
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [-74.006, 40.7128],
                [-73.935, 40.730],
                // ... 200+ coordinate pairs
                [-118.243, 34.052]
            ]
        }
    },
    "fuel_stops": [
        {
            "opis_truckstop_id": 54321,
            "name": "PILOT TRAVEL CENTER #325",
            "address": "I-80, EXIT 120",
            "city": "Clearfield",
            "state": "PA",
            "latitude": 41.0272,
            "longitude": -78.4392,
            "price_per_gallon": 3.189,
            "gallons_needed": 50.0,
            "cost": 159.45,
            "miles_from_start": 452.3,
            "cumulative_cost": 159.45
        },
        {
            "opis_truckstop_id": 67890,
            "name": "FLYING J TRAVEL PLAZA #154",
            "address": "US-40, EXIT 11",
            "city": "Terre Haute",
            "state": "IN",
            "latitude": 39.4667,
            "longitude": -87.4139,
            "price_per_gallon": 3.099,
            "gallons_needed": 50.0,
            "cost": 154.95,
            "miles_from_start": 901.7,
            "cumulative_cost": 314.40
        },
        // ... 3-5 more stops for cross-country routes
    ],
    "total_fuel_cost": 867.23,
    "total_gallons": 278.94,
    "candidate_stations_count": 342,
    "stations_along_route": 156,
    "optimization_method": "dynamic_programming",
    "processing_time_seconds": 2.3,
    "api_version": "v2"
}
```

#### Response Fields

**Route Object**:

| Field | Type | Description |
|-------|------|-------------|
| `distance_miles` | float | Total route distance in miles |
| `duration_hours` | float | Estimated driving time (excluding stops) |
| `geometry.type` | string | Always "LineString" (GeoJSON format) |
| `geometry.coordinates` | array | Array of [longitude, latitude] pairs defining route |

**Fuel Stop Object** (each item in `fuel_stops` array):

| Field | Type | Description |
|-------|------|-------------|
| `opis_truckstop_id` | integer | Unique station identifier from dataset |
| `name` | string | Station name (e.g., "PILOT TRAVEL CENTER") |
| `address` | string | Street address or exit information |
| `city` | string | City name |
| `state` | string | Two-letter state code |
| `latitude` | float | Station latitude (WGS84) |
| `longitude` | float | Station longitude (WGS84) |
| `price_per_gallon` | float | Retail diesel price (USD) |
| `gallons_needed` | float | Fuel to purchase at this stop (usually 50 for full refill) |
| `cost` | float | Total cost for this fuel stop (gallons × price) |
| `miles_from_start` | float | Distance from route start to this station |
| `cumulative_cost` | float | Running total of fuel costs up to this stop |

**Metadata Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `total_fuel_cost` | float | Sum of all fuel stop costs (globally optimal) |
| `total_gallons` | float | Total fuel needed for entire route |
| `candidate_stations_count` | integer | Stations in route states (pre-filtering) |
| `stations_along_route` | integer | Stations within 15 miles of route (post-filtering) |
| `optimization_method` | string | "dynamic_programming" (guarantees global optimum) |
| `processing_time_seconds` | float | Server processing time |
| `api_version` | string | "v2" (optimized version) |
| `explanation` | string | Human-readable explanation (for short routes) |

#### Error Responses

##### 400 Bad Request - Invalid Input

```json
{
    "error": "Validation failed",
    "details": {
        "start": ["This field is required."]
    }
}
```

**Causes**:
- Missing `start` or `end` parameter
- Empty string values
- Invalid JSON format

##### 400 Bad Request - Geocoding Failed

```json
{
    "error": "Could not geocode start location: Unknown City, ZZ"
}
```

**Causes**:
- Location not found by geocoding service
- Typo in city/state name
- Location outside USA

##### 400 Bad Request - Routing Failed

```json
{
    "error": "Could not calculate route between locations"
}
```

**Causes**:
- No road route exists between locations
- OSRM service temporarily unavailable
- Locations too far apart for routing engine

##### 500 Internal Server Error

```json
{
    "error": "An unexpected error occurred",
    "details": "Database connection failed"
}
```

**Causes**:
- Database offline
- External API timeout (OSRM/Nominatim)
- Server misconfiguration

---

## Algorithm Details

### Dynamic Programming Optimization

The `/route/` endpoint uses a **dynamic programming** algorithm to find the globally optimal fuel stops:

1. **Route Calculation** (1 API call):
   - Uses OSRM (Open Source Routing Machine) to get route geometry and distance
   - Free service, no API key required

2. **Geocoding** (2 API calls):
   - Converts start/end locations to coordinates using Nominatim (OpenStreetMap)
   - Rate-limited to 1 request/second
   - Free service, no API key required

3. **Station Filtering**:
   - Query database for stations in route states (fast indexed lookup)
   - Geometric filtering: Only stations within 15 miles perpendicular distance from route
   - Reduces 6,966 stations to ~100-200 candidates

4. **DP Graph Construction**:
   - Creates graph where each station is a node
   - Edges exist if distance ≤ 500 miles (vehicle range)
   - Edge cost = fuel price × gallons needed

5. **Shortest Path Calculation**:
   - DP recurrence: `dp[i] = min(dp[j] + cost(j→i))` for all valid j
   - Guarantees globally optimal solution (not greedy approximation)
   - O(n²) complexity, typically < 1 second for 200 candidates

6. **Backtracking**:
   - Reconstructs optimal path from DP table
   - Returns ordered list of fuel stops with costs

### Constraints Enforced

- **Vehicle Range**: 500 miles maximum between stops
- **Fuel Efficiency**: 10 miles per gallon (constant)
- **Tank Capacity**: Assumes 50-gallon tank (refill strategy)
- **Fuel Type**: Diesel (retail prices from dataset)

---

## Rate Limits & Performance

### API Rate Limits

**This API** (Django server):
- No rate limiting currently enforced
- Recommended: 60 requests/minute for production

**External APIs** (constraints we follow):
- **Nominatim**: 1 request/second (respected by our geocoding cache)
- **OSRM**: No documented limit (public demo server)

### Performance Benchmarks

| Route Type | Distance | Stations Filtered | Processing Time | API Calls |
|------------|----------|-------------------|-----------------|-----------|
| Short (< 500 mi) | 95 miles | 0 fuel stops | 0.5-1 second | 3 |
| Medium (500-1000 mi) | 800 miles | 1-2 fuel stops | 1-1.5 seconds | 3 |
| Long (> 2000 mi) | 2,800 miles | 5-6 fuel stops | 2-3 seconds | 3 |

**Note**: First request may be slower due to cold start. Subsequent requests benefit from geocoding cache.

---

## Using the API

### cURL Examples

**Health Check**:
```bash
curl http://127.0.0.1:8000/api/health/
```

**Short Route**:
```bash
curl -X POST http://127.0.0.1:8000/api/route/ \
  -H "Content-Type: application/json" \
  -d '{"start": "New York, NY", "end": "Philadelphia, PA"}'
```

**Long Route**:
```bash
curl -X POST http://127.0.0.1:8000/api/route/ \
  -H "Content-Type: application/json" \
  -d '{"start": "New York, NY", "end": "Los Angeles, CA"}'
```

### Python Example

```python
import requests

# Calculate route
response = requests.post(
    'http://127.0.0.1:8000/api/route/',
    json={
        'start': 'New York, NY',
        'end': 'Los Angeles, CA'
    }
)

if response.status_code == 200:
    data = response.json()
    print(f"Total fuel cost: ${data['total_fuel_cost']:.2f}")
    print(f"Fuel stops: {len(data['fuel_stops'])}")
    for stop in data['fuel_stops']:
        print(f"  - {stop['name']} in {stop['city']}, {stop['state']}: ${stop['cost']:.2f}")
else:
    print(f"Error: {response.json()['error']}")
```

### JavaScript (Fetch) Example

```javascript
async function calculateRoute(start, end) {
    const response = await fetch('http://127.0.0.1:8000/api/route/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ start, end })
    });
    
    if (response.ok) {
        const data = await response.json();
        console.log(`Fuel cost: $${data.total_fuel_cost}`);
        console.log(`Stops: ${data.fuel_stops.length}`);
        return data;
    } else {
        const error = await response.json();
        console.error('Error:', error.error);
    }
}

calculateRoute('New York, NY', 'Los Angeles, CA');
```

---

## External APIs Used

### 1. OSRM (Routing)

- **Purpose**: Calculate driving routes between locations
- **Cost**: Free, no API key required
- **URL**: `https://router.project-osrm.org`
- **Rate Limit**: No documented limit (use responsibly)
- **Documentation**: https://project-osrm.org/

### 2. Nominatim (Geocoding)

- **Purpose**: Convert "City, State" to latitude/longitude
- **Cost**: Free, no API key required
- **Provider**: OpenStreetMap Foundation
- **Rate Limit**: 1 request/second
- **Documentation**: https://nominatim.org/

---

## Database Schema

Fuel stations are stored in SQLite with the following model:

```python
class FuelStation(models.Model):
    opis_truckstop_id = models.IntegerField(unique=True)
    truckstop_name = models.CharField(max_length=200)
    address = models.CharField(max_length=300)
    city = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=2, db_index=True)
    retail_price = models.FloatField(db_index=True)
    latitude = models.FloatField(null=True, db_index=True)
    longitude = models.FloatField(null=True, db_index=True)
    geocoded = models.BooleanField(default=False)
```

**Indexes**:
- `state`: Fast filtering by state
- `retail_price`: Efficient price-based sorting
- `latitude, longitude`: Spatial queries
- Compound index: `(city, state, address)` for uniqueness

---

## Best Practices

### For Production Use

1. **Add Rate Limiting**: Use `django-ratelimit` to prevent abuse
2. **Add Caching**: Cache route calculations for common routes (Redis)
3. **Use Environment Variables**: Don't hardcode API URLs
4. **Enable CORS**: If building a web frontend
5. **Set up Logging**: Use Django's logging for request tracking
6. **Monitor External APIs**: Track OSRM/Nominatim availability
7. **Add Authentication**: Require API keys for access

### Optimization Tips

- **Pre-calculate Popular Routes**: Cache NYC→LA, etc.
- **Index Tuning**: Add GiST spatial index for lat/lon in PostgreSQL
- **Connection Pooling**: Use persistent connections to database
- **CDN for Maps**: Serve route geometries via CDN if building UI

---

## Support & Troubleshooting

### Common Issues

**Issue**: "Could not geocode location"  
**Solution**: Check spelling, use "City, STATE" format, ensure US location

**Issue**: Slow first request  
**Solution**: Normal—geocoding cache cold start. Subsequent requests faster.

**Issue**: "No stations found along route"  
**Solution**: Run `python manage.py load_fuel_stations --geocode-only` to ensure database is populated

**Issue**: Empty `fuel_stops` array  
**Solution**: Route may be < 500 miles (no stops needed) or passes through areas with no stations in dataset

---

## Changelog

### Version 2.0 (Current)
- ✅ Dynamic programming optimization (globally optimal)
- ✅ Pre-geocoded database (6,966 stations)
- ✅ Geometric route filtering (15-mile corridor)
- ✅ Exactly 3 API calls per request
- ✅ Comprehensive error handling
- ✅ Health endpoint with database stats

### Version 1.0 (Deprecated)
- ❌ Greedy optimization (local optimum only)
- ❌ On-demand geocoding (20+ API calls)
- ❌ Radius-based filtering (less accurate)
- ❌ CSV-based data (no database)

---

**Last Updated**: February 12, 2026  
**Maintained By**: Backend Development Team  
**Django Version**: 6.0.2  
**DRF Version**: 3.16.1
