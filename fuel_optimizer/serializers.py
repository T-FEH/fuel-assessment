"""
Serializers for API request/response validation.

Django REST Framework Serializers vs FastAPI Pydantic:

FastAPI (Pydantic):
    class RouteRequest(BaseModel):
        start: str
        end: str
        
        @validator('start')
        def validate_start(cls, v):
            if not v:
                raise ValueError("Start is required")
            return v

Django REST Framework (Serializers):
    class RouteSerializer(serializers.Serializer):
        start = serializers.CharField()
        end = serializers.CharField()
        
        def validate_start(self, value):
            if not value:
                raise serializers.ValidationError("Start is required")
            return value

Key differences:
1. DRF uses class attributes, Pydantic uses type annotations
2. DRF validators are instance methods (validate_<field>), Pydantic uses @validator decorator
3. Both support nested serialization and custom validation
"""
from rest_framework import serializers


class RouteRequestSerializer(serializers.Serializer):
    """
    Input validation for route calculation requests.
    Like Pydantic's BaseModel for request body validation.
    """
    start = serializers.CharField(
        max_length=200,
        help_text="Starting location (city, state or address in USA)"
    )
    end = serializers.CharField(
        max_length=200,
        help_text="Ending location (city, state or address in USA)"
    )

    def validate_start(self, value: str) -> str:
        """Validate start location is not empty."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Start location is required")
        return value

    def validate_end(self, value: str) -> str:
        """Validate end location is not empty."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("End location is required")
        return value


class FuelStopSerializer(serializers.Serializer):
    """Serializer for individual fuel stop information."""
    name = serializers.CharField()
    address = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    price_per_gallon = serializers.FloatField()
    gallons_needed = serializers.FloatField()
    cost = serializers.FloatField()
    miles_from_start = serializers.FloatField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()


class RouteInfoSerializer(serializers.Serializer):
    """Serializer for route information."""
    distance_miles = serializers.FloatField()
    duration_hours = serializers.FloatField()
    geometry = serializers.DictField()  # GeoJSON geometry


class RouteResponseSerializer(serializers.Serializer):
    """
    Output serializer for route calculation response.
    Like Pydantic's response model.
    """
    route = RouteInfoSerializer()
    fuel_stops = FuelStopSerializer(many=True)
    total_fuel_cost = serializers.FloatField()
    total_gallons = serializers.FloatField()
    start_location = serializers.DictField()
    end_location = serializers.DictField()
