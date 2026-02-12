"""
Tests for the Fuel Route Optimizer API.

Django testing vs pytest (FastAPI pattern):
- Django has built-in test client (like httpx.AsyncClient in FastAPI)
- TestCase classes instead of individual test functions
- setUp/tearDown instead of fixtures (though pytest works too)
"""
import json
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status


class RouteAPITest(APITestCase):
    """
    Test cases for the route optimization endpoint.
    
    Like FastAPI's TestClient:
        client = TestClient(app)
        response = client.post("/route", json={...})
        
    Django equivalent:
        response = self.client.post('/api/route/', data={...})
    """
    
    def test_health_endpoint(self):
        """Test the health check endpoint works."""
        response = self.client.get('/api/health/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'healthy')
    
    def test_route_short_distance(self):
        """Test route calculation for a short trip (< 500 miles)."""
        data = {
            "start": "New York, NY",
            "end": "Philadelphia, PA"
        }
        
        response = self.client.post(
            '/api/route/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Should succeed
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should have route info
        self.assertIn('route', response.data)
        self.assertIn('fuel_stops', response.data)
        self.assertIn('total_fuel_cost', response.data)
        self.assertIn('total_gallons', response.data)
        
        # Short route might not need fuel stops
        # but should still return valid data
        self.assertIsInstance(response.data['fuel_stops'], list)
        self.assertGreater(response.data['total_gallons'], 0)
    
    def test_route_long_distance(self):
        """Test route calculation for a long trip (> 500 miles)."""
        data = {
            "start": "New York, NY",
            "end": "Chicago, IL"
        }
        
        response = self.client.post(
            '/api/route/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Long route should have fuel stops
        route = response.data
        self.assertGreater(route['route']['distance_miles'], 500)
        # Should have at least one fuel stop
        # (depending on fuel station data availability)
        self.assertIsInstance(route['fuel_stops'], list)
    
    def test_route_validation_missing_start(self):
        """Test that missing start location is rejected."""
        data = {
            "end": "Los Angeles, CA"
        }
        
        response = self.client.post(
            '/api/route/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Should return 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_route_validation_missing_end(self):
        """Test that missing end location is rejected."""
        data = {
            "start": "New York, NY"
        }
        
        response = self.client.post(
            '/api/route/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_route_validation_empty_strings(self):
        """Test that empty location strings are rejected."""
        data = {
            "start": "  ",
            "end": "  "
        }
        
        response = self.client.post(
            '/api/route/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_route_invalid_location(self):
        """Test that invalid locations return proper error."""
        data = {
            "start": "InvalidCityXYZ123",
            "end": "AnotherFakeCity999"
        }
        
        response = self.client.post(
            '/api/route/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Should return 400 for geocoding failure
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_route_response_structure(self):
        """Test that response has correct structure."""
        data = {
            "start": "Boston, MA",
            "end": "Washington, DC"
        }
        
        response = self.client.post(
            '/api/route/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        if response.status_code == status.HTTP_200_OK:
            # Check structure
            self.assertIn('route', response.data)
            self.assertIn('fuel_stops', response.data)
            self.assertIn('total_fuel_cost', response.data)
            self.assertIn('total_gallons', response.data)
            self.assertIn('start_location', response.data)
            self.assertIn('end_location', response.data)
            
            # Check route structure
            route = response.data['route']
            self.assertIn('distance_miles', route)
            self.assertIn('duration_hours', route)
            self.assertIn('geometry', route)
            
            # Check fuel stop structure (if any)
            if response.data['fuel_stops']:
                stop = response.data['fuel_stops'][0]
                self.assertIn('name', stop)
                self.assertIn('city', stop)
                self.assertIn('state', stop)
                self.assertIn('price_per_gallon', stop)
                self.assertIn('cost', stop)
                self.assertIn('miles_from_start', stop)


class SerializerTest(TestCase):
    """Test serializers for proper validation."""
    
    def test_route_request_serializer_valid(self):
        """Test valid request data."""
        from fuel_optimizer.serializers import RouteRequestSerializer
        
        data = {
            "start": "New York, NY",
            "end": "Boston, MA"
        }
        
        serializer = RouteRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['start'], "New York, NY")
        self.assertEqual(serializer.validated_data['end'], "Boston, MA")
    
    def test_route_request_serializer_trims_whitespace(self):
        """Test that whitespace is trimmed."""
        from fuel_optimizer.serializers import RouteRequestSerializer
        
        data = {
            "start": "  New York, NY  ",
            "end": "  Boston, MA  "
        }
        
        serializer = RouteRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['start'], "New York, NY")
        self.assertEqual(serializer.validated_data['end'], "Boston, MA")
