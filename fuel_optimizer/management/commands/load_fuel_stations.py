"""
Django management command to load and pre-geocode fuel stations.

Usage:
    python manage.py load_fuel_stations              # Full load with geocoding
    python manage.py load_fuel_stations --geocode-only  # Geocode pending stations only
    python manage.py load_fuel_stations --skip-geocoding  # Load CSV without geocoding

Free API Used: Nominatim (OpenStreetMap) - https://nominatim.openstreetmap.org
- Rate limit: 1 request per second
- Timeout: 10 seconds per request
- No API key required
"""
import time
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

from fuel_optimizer.models import FuelStation


class Command(BaseCommand):
    help = 'Load and pre-geocode fuel stations from CSV using Nominatim (free OpenStreetMap API)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-geocoding',
            action='store_true',
            help='Skip geocoding (only load CSV data)',
        )
        parser.add_argument(
            '--geocode-only',
            action='store_true',
            help='Skip CSV import, only geocode pending stations',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Geocoding batch size (default: 100)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🚀 Starting fuel station import...\n'))
        
        # If geocode-only mode, skip CSV import
        if options['geocode_only']:
            self.stdout.write(self.style.WARNING('⏭️  Skipping CSV import (--geocode-only mode)\n'))
            total_stations = FuelStation.objects.count()
            if total_stations == 0:
                self.stdout.write(self.style.ERROR('❌ No stations in database! Run without --geocode-only first.\n'))
                return
        else:
            # Load CSV
            csv_path = Path(__file__).parent.parent.parent.parent / 'data' / 'fuel_prices.csv'
            self.stdout.write(f'📂 Loading CSV from: {csv_path}')
            
            df = pd.read_csv(csv_path)
            self.stdout.write(f'   Loaded {len(df)} rows')
            
            # Clean column names
            df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]
            
            # Group by location, take minimum price (most competitive)
            self.stdout.write('\n🔄 Grouping duplicate locations...')
            grouped = df.groupby(
                ['truckstop_name', 'address', 'city', 'state'],
                as_index=False
            ).agg({
                'opis_truckstop_id': 'first',
                'rack_id': 'first',
                'retail_price': 'min'  # Best price
            })
            
            self.stdout.write(f'   Reduced to {len(grouped)} unique stations')
            
            # Bulk create stations
            self.stdout.write('\n💾 Saving to database...')
            stations_to_create = []
            
            for _, row in grouped.iterrows():
                stations_to_create.append(FuelStation(
                    opis_truckstop_id=int(row['opis_truckstop_id']),
                    truckstop_name=row['truckstop_name'],
                    address=row['address'],
                    city=row['city'],
                    state=row['state'],
                    rack_id=int(row['rack_id']),
                    retail_price=float(row['retail_price']),
                    geocoded=False
                ))
            
            with transaction.atomic():
                # Only delete if re-importing (not geocode-only mode)
                FuelStation.objects.all().delete()
                # Bulk create (much faster than one-by-one)
                FuelStation.objects.bulk_create(
                    stations_to_create,
                    ignore_conflicts=True  # Skip duplicates
                )
            
            total_stations = FuelStation.objects.count()
            self.stdout.write(self.style.SUCCESS(f'   ✅ Saved {total_stations} stations'))
        
        # Geocode if requested
        if not options['skip_geocoding']:
            self.geocode_stations(options['batch_size'])
        else:
            self.stdout.write(self.style.WARNING('\n⏭️  Skipping geocoding (use without --skip-geocoding to geocode)'))
        
        # Summary
        total_stations = FuelStation.objects.count()
        geocoded_count = FuelStation.objects.filter(geocoded=True).count()
        self.stdout.write(self.style.SUCCESS(f'\n✅ Import complete!'))
        self.stdout.write(f'   Total stations: {total_stations}')
        self.stdout.write(f'   Geocoded: {geocoded_count}')
        self.stdout.write(f'   Pending: {total_stations - geocoded_count}\n')

    def geocode_stations(self, batch_size):
        """Geocode all stations that don't have coordinates yet (skips already geocoded)."""
        self.stdout.write('\n🌍 Starting geocoding process...')
        self.stdout.write('   Using: Nominatim (OpenStreetMap) - FREE API')
        self.stdout.write('   Rate limit: 1 request/second (no API key needed)')
        self.stdout.write('   (This may take 10-20 minutes for full dataset)\n')
        
        # Initialize geocoder with longer timeout
        geocoder = Nominatim(
            user_agent="fuel_route_optimizer_django_v2",
            timeout=10  # 10 second timeout (was causing errors before)
        )
        
        # Get ONLY ungeocoded unique city/state combinations
        ungeocoded = FuelStation.objects.filter(geocoded=False)
        unique_locations = ungeocoded.values('city', 'state').distinct()
        
        total_locations = len(unique_locations)
        
        if total_locations == 0:
            self.stdout.write(self.style.SUCCESS('   ✅ All stations already geocoded!'))
            return
        
        self.stdout.write(f'   Found {total_locations} unique locations to geocode')
        self.stdout.write(f'   (Skipping {FuelStation.objects.filter(geocoded=True).count()} already geocoded)\n')
        
        # Geocode cache
        coords_cache = {}
        failed_locations = []
        
        for idx, location in enumerate(unique_locations, 1):
            city = location['city']
            state = location['state']
            cache_key = f"{city},{state}"
            
            # Progress update every 10 locations
            if idx % 10 == 0 or idx == total_locations:
                progress = (idx / total_locations) * 100
                self.stdout.write(f'   Progress: {idx}/{total_locations} ({progress:.1f}%)')
            
            # Skip Canadian provinces (SK, AB, BC, MB, etc.)
            canadian_provinces = ['SK', 'AB', 'BC', 'MB', 'ON', 'QC', 'NB', 'NS', 'PE', 'NL', 'NT', 'YT', 'NU']
            if state.upper() in canadian_provinces:
                self.stdout.write(
                    self.style.WARNING(f'   ⏭️  Skipping Canadian location: {city}, {state}')
                )
                failed_locations.append(f"{city}, {state} (Canada)")
                continue
            
            query = f"{city}, {state}, USA"
            
            # Retry logic with exponential backoff
            max_attempts = 3
            result = None
            
            for attempt in range(max_attempts):
                try:
                    # Rate limiting - wait 1 second between requests
                    if idx > 1 or attempt > 0:
                        time.sleep(1.0)
                    
                    result = geocoder.geocode(query)
                    
                    if result:
                        coords_cache[cache_key] = (result.latitude, result.longitude)
                        break  # Success!
                    else:
                        # No results found
                        if attempt == max_attempts - 1:
                            self.stdout.write(
                                self.style.WARNING(f'   ⚠️  Could not find: {query}')
                            )
                            failed_locations.append(query)
                        
                except (GeocoderTimedOut, GeocoderUnavailable) as e:
                    # Timeout or service unavailable - retry
                    if attempt < max_attempts - 1:
                        wait_time = 2 ** attempt  # 1s, 2s, 4s
                        self.stdout.write(
                            self.style.WARNING(f'   ⏳ Timeout on {query}, retrying in {wait_time}s... (attempt {attempt + 1}/{max_attempts})')
                        )
                        time.sleep(wait_time)
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'   ❌ Failed after {max_attempts} attempts: {query}')
                        )
                        failed_locations.append(query)
                        
                except Exception as e:
                    # Other errors
                    self.stdout.write(
                        self.style.ERROR(f'   ❌ Error geocoding {query}: {type(e).__name__}: {e}')
                    )
                    failed_locations.append(query)
                    break  # Don't retry on unknown errors
        
        # Update stations with coordinates
        self.stdout.write('\n💾 Updating stations with coordinates...')
        
        updated_count = 0
        with transaction.atomic():
            for cache_key, coords in coords_cache.items():
                city, state = cache_key.split(',')
                count = FuelStation.objects.filter(
                    city=city,
                    state=state,
                    geocoded=False
                ).update(
                    latitude=coords[0],
                    longitude=coords[1],
                    geocoded=True
                )
                updated_count += count
        
        self.stdout.write(self.style.SUCCESS(f'   ✅ Geocoded {len(coords_cache)} unique locations'))
        self.stdout.write(self.style.SUCCESS(f'   ✅ Updated {updated_count} station records'))
        
        if failed_locations:
            self.stdout.write(self.style.WARNING(f'\n   ⚠️  Failed to geocode {len(failed_locations)} locations:'))
            for loc in failed_locations[:10]:  # Show first 10
                self.stdout.write(f'      - {loc}')
            if len(failed_locations) > 10:
                self.stdout.write(f'      ... and {len(failed_locations) - 10} more')
            self.stdout.write(self.style.WARNING(f'\n   💡 Run command again with --geocode-only to retry failed locations'))

