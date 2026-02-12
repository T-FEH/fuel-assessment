# 🎥 Loom Video Demo Script - Fuel Route Optimizer API

**Duration**: 5 minutes max  
**Tool**: Postman (or Insomnia/Thunder Client)  
**Goal**: Demonstrate production-ready Django API with dynamic programming optimization

---

## Pre-Demo Checklist

✅ Server running: `uv run python manage.py runserver`  
✅ Postman open with prepared requests  
✅ Screen recording ready (Loom)  
✅ Fuel stations geocoded: `uv run python manage.py load_fuel_stations --geocode-only` (if needed)

---

## 🎬 Demo Script with Speaking Points

### **Intro (30 seconds)**

**[Screen: VS Code with project open]**

> "Hi, I'm presenting my Django Fuel Route Optimizer API built for the backend developer assessment.  
> This API calculates the most cost-effective fuel stops for long-distance truck routes across the USA.  
> I'll show you the working API, explain the algorithm, and walk through the code structure."

**Key Points to Mention**:
- Built with Django 6.0 and Django REST Framework
- Uses dynamic programming for optimal fuel stop selection
- Pre-geocoded database with 6,966 fuel stations
- Exactly 3 external API calls per request (OSRM for routing, Nominatim for geocoding)

---

### **Test 1: Health Check (20 seconds)**

**[Screen: Postman]**

> "First, let me verify the API is running with a health check."

**Request**:
- Method: **GET**
- URL: `http://127.0.0.1:8000/api/health/`
- Click **Send**

**Expected Response**:
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

**Say**: 
> "Perfect! The API is healthy, and we have 6,934 geocoded fuel stations in our database ready to use."

---

### **Test 2: Short Route (No Fuel Stops) (45 seconds)**

**[Screen: Postman - New Request Tab]**

> "Let's test a short route first—New York to Philadelphia, about 95 miles. Since our truck has a 500-mile range, no fuel stops should be needed."

**Request**:
- Method: **POST**
- URL: `http://127.0.0.1:8000/api/route/`
- Headers: `Content-Type: application/json`
- Body:
```json
{
    "start": "New York, NY",
    "end": "Philadelphia, PA"
}
```
- Click **Send**

**Expected Response**:
```json
{
    "route": {
        "distance_miles": 95.3,
        "duration_hours": 1.6,
        "geometry": { ... }
    },
    "fuel_stops": [],
    "total_fuel_cost": 0,
    "total_gallons": 9.53,
    "optimization_method": "dynamic_programming",
    "processing_time_seconds": 0.85,
    "api_version": "v2"
}
```

**Say**:
> "As expected, no fuel stops needed—the route is only 95 miles. The API responded in under a second.  
> Notice it calculated 9.53 gallons needed at 10 MPG, but since we start with a full tank, we don't need to refuel."

---

### **Test 3: Long Route (Multiple Fuel Stops) (90 seconds)**

**[Screen: Postman - New Request Tab]**

> "Now the interesting part: a cross-country route from New York to Los Angeles—about 2,800 miles.  
> The algorithm will find the optimal fuel stops to minimize total cost using dynamic programming."

**Request**:
- Method: **POST**
- URL: `http://127.0.0.1:8000/api/route/`
- Headers: `Content-Type: application/json`
- Body:
```json
{
    "start": "New York, NY",
    "end": "Los Angeles, CA"
}
```
- Click **Send**

**Expected Response** (abbreviated):
```json
{
    "route": {
        "distance_miles": 2789.4,
        "duration_hours": 40.2
    },
    "fuel_stops": [
        {
            "name": "PILOT TRAVEL CENTER",
            "city": "Clearfield",
            "state": "PA",
            "price_per_gallon": 3.189,
            "gallons_needed": 50.0,
            "cost": 159.45,
            "miles_from_start": 452.3
        },
        {
            "name": "FLYING J TRAVEL PLAZA",
            "city": "Terre Haute",
            "state": "IN",
            "price_per_gallon": 3.099,
            "gallons_needed": 50.0,
            "cost": 154.95,
            "miles_from_start": 901.7
        }
        // ... more stops
    ],
    "total_fuel_cost": 867.23,
    "total_gallons": 278.94,
    "optimization_method": "dynamic_programming",
    "processing_time_seconds": 2.3,
    "api_version": "v2"
}
```

**Say** (while scrolling through response):
> "Excellent! The API found 6 optimal fuel stops across the 2,800-mile route.  
> Total fuel cost is $867—that's the globally optimal solution, not just a greedy approximation.  
> Notice it selected cheaper stations in Indiana ($3.09/gal) over more expensive options.  
> The algorithm processed this in 2.3 seconds with only 3 external API calls."

---

### **Code Walkthrough (90 seconds)**

**[Screen: VS Code - Project Structure]**

> "Let me quickly show you the code structure."

**Show files** (briefly hover/open):

1. **`fuel_optimizer/views.py`**:
   > "Here's the main API endpoint—standard Django REST Framework view with validation and error handling."

2. **`fuel_optimizer/services/optimizer_v2.py`**:
   > "This is the core optimization logic using dynamic programming.  
   > It builds a graph of fuel stops, calculates minimum cost paths, and backtracks to find the optimal sequence.  
   > Similar to Dijkstra's algorithm but optimized for the fuel stop problem."

3. **`fuel_optimizer/services/geometry.py`**:
   > "Geometric filtering—finds stations within 15 miles of the route using perpendicular distance calculations.  
   > This is much more accurate than radius-based searches."

4. **`fuel_optimizer/models.py`**:
   > "Database model with pre-geocoded fuel stations. Indexed on price and location for fast queries."

5. **`fuel_optimizer/management/commands/load_fuel_stations.py`**:
   > "Django management command that loads the CSV and geocodes all stations once—using Nominatim free API."

---

### **Closing - Requirements Met (45 seconds)**

**[Screen: README or requirements document]**

> "Let me confirm all assessment requirements are met:"

**Say** (checking off):
- ✅ **Input**: Start and finish locations in USA → ✓
- ✅ **Output**: Route map with optimal fuel stops and total cost → ✓
- ✅ **Vehicle constraints**: 500-mile range, 10 MPG efficiency enforced → ✓
- ✅ **Multiple fuel stops**: Handled for routes > 500 miles → ✓
- ✅ **Performance**: Fast response times with minimal API calls (3 total) → ✓
- ✅ **Cost optimization**: Dynamic programming guarantees globally optimal solution → ✓
- ✅ **Production-ready**: Error handling, logging, database indexes, migrations → ✓
- ✅ **Django best practices**: REST Framework, serializers, class-based views, management commands → ✓

**Final statement**:
> "This implementation exceeds the requirements with a production-ready dynamic programming optimizer,  
> pre-geocoded database for performance, and geometric route filtering for accuracy.  
> The code is clean, well-documented, and follows Django best practices.  
> Thank you for reviewing my submission!"

---

## 📋 Quick Reference - All Test Cases

### Health Check
```
GET http://127.0.0.1:8000/api/health/
```

### Short Route (< 500 miles)
```json
POST http://127.0.0.1:8000/api/route/
{
    "start": "New York, NY",
    "end": "Philadelphia, PA"
}
```

### Medium Route (~800 miles, 1-2 stops)
```json
POST http://127.0.0.1:8000/api/route/
{
    "start": "New York, NY",
    "end": "Chicago, IL"
}
```

### Long Route (2,800 miles, 5-6 stops)
```json
POST http://127.0.0.1:8000/api/route/
{
    "start": "New York, NY",
    "end": "Los Angeles, CA"
}
```

---

## 🎯 Key Talking Points Summary

**Algorithm**:
- Dynamic programming (not greedy heuristic)
- Guarantees globally optimal fuel cost
- O(n²) complexity where n = candidate stations

**Performance**:
- 3 API calls total (2 geocoding, 1 routing)
- Pre-geocoded database (no per-request geocoding)
- Geometric filtering (15-mile corridor along route)

**Technology**:
- Django 6.0 + Django REST Framework
- SQLite with spatial indexes
- OSRM for routing (free, no API key)
- Nominatim for geocoding (free, OpenStreetMap)

**Production Features**:
- Input validation with serializers
- Comprehensive error handling
- Request logging
- Database migrations
- Management commands for data loading
- Health check endpoint

---

## 🚀 If You Have Extra Time

### Show Database Query
```bash
# In Django shell
uv run python manage.py shell

from fuel_optimizer.models import FuelStation
print(f"Total stations: {FuelStation.objects.count()}")
print(f"Geocoded: {FuelStation.objects.filter(geocoded=True).count()}")
print(f"Cheapest in TX: {FuelStation.objects.filter(state='TX', geocoded=True).order_by('retail_price').first().retail_price}")
```

### Show Management Command
```bash
# Demonstrate geocoding command (don't run full, just show)
uv run python manage.py load_fuel_stations --help
```

---

## ✅ Pre-Recording Checklist

- [ ] Server running on port 8000
- [ ] All 4 Postman requests saved and tested
- [ ] Loom recording software ready
- [ ] Microphone tested
- [ ] Browser tabs: Postman + VS Code
- [ ] Practiced script once (aim for 4-5 minutes)
- [ ] Database has geocoded stations (check /api/health/)

**Recording tip**: Speak clearly, don't rush, and show confidence in your solution! 🎬
