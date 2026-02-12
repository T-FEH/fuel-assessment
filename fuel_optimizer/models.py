"""
Django models for fuel optimization.

This is similar to SQLAlchemy models in FastAPI, but Django's ORM is built-in.
"""
from django.db import models


class FuelStation(models.Model):
    """
    Pre-geocoded fuel station with pricing data.
    
    This stores all fuel stations from the CSV with their coordinates
    pre-geocoded to avoid runtime geocoding overhead.
    
    FastAPI equivalent:
        class FuelStation(Base):  # SQLAlchemy
            __tablename__ = "fuel_stations"
            id = Column(Integer, primary_key=True)
            ...
    """
    # Original CSV fields
    opis_truckstop_id = models.IntegerField(db_index=True)
    truckstop_name = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    city = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=2, db_index=True)
    rack_id = models.IntegerField()
    retail_price = models.FloatField(db_index=True)  # Index for sorting by price
    
    # Pre-geocoded coordinates
    latitude = models.FloatField(null=True, blank=True, db_index=True)
    longitude = models.FloatField(null=True, blank=True, db_index=True)
    geocoded = models.BooleanField(default=False, db_index=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'fuel_stations'
        indexes = [
            models.Index(fields=['state', 'geocoded']),
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['retail_price']),
        ]
        # Unique constraint on location to avoid duplicates
        unique_together = [['truckstop_name', 'address', 'city', 'state']]
    
    def __str__(self):
        return f"{self.truckstop_name} - {self.city}, {self.state}"
    
    @property
    def coordinates(self):
        """Return (lat, lon) tuple."""
        return (self.latitude, self.longitude) if self.geocoded else None
