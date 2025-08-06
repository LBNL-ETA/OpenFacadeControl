# *** Copyright Notice ***
# 
# OpenFacadeControl (OFC) Copyright (c) 2024, The Regents of the University
# of California, through Lawrence Berkeley National Laboratory (subject to receipt
# of any required approvals from the U.S. Dept. of Energy). All rights reserved.

"""
Weather Integration Module for AFC-OFC Integration

This module handles weather forecast data collection, validation, and formatting
for AFC optimization algorithms.
"""

import os
import json
import logging
import datetime
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
import requests
from datetime import timedelta

_log = logging.getLogger(__name__)


class WeatherIntegration:
    """
    Weather forecast integration for AFC optimization.
    
    Supports multiple weather data sources and provides forecast caching,
    validation, and format conversion for AFC requirements.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize weather integration.
        
        :param config: Weather integration configuration.
        """
        self.config = config
        self.forecast_cache = {}
        self.current_weather = {}
        self.last_update = None
        
        # Configuration
        self.source = config.get('source', 'openweather')
        self.api_key = config.get('api_key', '')
        self.location = config.get('location', {'lat': 37.85, 'lon': -122.24})
        self.update_interval = config.get('update_interval', 1800)  # 30 minutes
        self.forecast_hours = config.get('forecast_hours', 48)
        self.cache_duration = config.get('cache_duration', 3600)  # 1 hour
        
        # Validation settings
        self.validation_enabled = config.get('validation_enabled', True)
        self.validation_limits = config.get('validation_limits', {
            'dni': {'min': 0, 'max': 1200},
            'dhi': {'min': 0, 'max': 500},
            'temp_air': {'min': -40, 'max': 60},
            'wind_speed': {'min': 0, 'max': 50}
        })
        
        # Initialize
        self._initialize_weather_sources()
        
    def _initialize_weather_sources(self):
        """Initialize weather data sources."""
        try:
            if self.source == 'openweather' and self.api_key:
                self.weather_source = OpenWeatherMapSource(self.api_key, self.location)
            elif self.source == 'nws':
                self.weather_source = NWSSource(self.location)
            elif self.source == 'simulation':
                self.weather_source = SimulationWeatherSource(self.location)
            else:
                _log.warning(f"Weather source '{self.source}' not configured, using simulation")
                self.weather_source = SimulationWeatherSource(self.location)
                
            _log.info(f"Weather integration initialized with source: {self.source}")
            
        except Exception as e:
            _log.error(f"Error initializing weather sources: {e}")
            self.weather_source = SimulationWeatherSource(self.location)
            
    def get_forecast(self, hours: Optional[int] = None) -> Optional[pd.DataFrame]:
        """
        Get weather forecast data.
        
        :param hours: Number of forecast hours (uses config default if None).
        :return: Weather forecast DataFrame or None if failed.
        """
        try:
            # Check cache first
            if self._is_cache_valid():
                _log.debug("Using cached weather forecast")
                return self._get_cached_forecast(hours)
                
            # Update forecast
            self.update_forecast()
            
            # Return forecast
            return self._get_cached_forecast(hours)
            
        except Exception as e:
            _log.error(f"Error getting weather forecast: {e}")
            return None
            
    def update_forecast(self) -> bool:
        """
        Update weather forecast from source.
        
        :return: True if successful, False otherwise.
        """
        try:
            _log.info("Updating weather forecast")
            
            # Get forecast from source
            forecast_data = self.weather_source.get_forecast(self.forecast_hours)
            
            if forecast_data is None:
                _log.error("Failed to get forecast from weather source")
                return False
                
            # Validate forecast data
            if self.validation_enabled:
                forecast_data = self._validate_forecast(forecast_data)
                
            # Cache the forecast
            self.forecast_cache = {
                'data': forecast_data,
                'timestamp': datetime.datetime.now(),
                'source': self.source
            }
            
            self.last_update = datetime.datetime.now()
            
            _log.info(f"Weather forecast updated - {len(forecast_data)} hours from {self.source}")
            return True
            
        except Exception as e:
            _log.error(f"Error updating weather forecast: {e}")
            return False
            
    def update_current_weather(self, weather_data: Dict[str, Any]):
        """
        Update current weather conditions from external source.
        
        :param weather_data: Current weather data dictionary.
        """
        try:
            # Convert to standard format
            standardized = self._standardize_weather_data(weather_data)
            
            if standardized:
                self.current_weather = {
                    'data': standardized,
                    'timestamp': datetime.datetime.now(),
                    'source': 'external'
                }
                
                _log.debug("Current weather updated from external source")
                
        except Exception as e:
            _log.error(f"Error updating current weather: {e}")
            
    def _is_cache_valid(self) -> bool:
        """Check if cached forecast is still valid."""
        if not self.forecast_cache:
            return False
            
        cache_age = (datetime.datetime.now() - self.forecast_cache['timestamp']).total_seconds()
        return cache_age < self.cache_duration
        
    def _get_cached_forecast(self, hours: Optional[int] = None) -> Optional[pd.DataFrame]:
        """Get forecast from cache."""
        try:
            if not self.forecast_cache:
                return None
                
            forecast = self.forecast_cache['data']
            
            # Limit to requested hours
            if hours and len(forecast) > hours:
                forecast = forecast.iloc[:hours]
                
            return forecast
            
        except Exception as e:
            _log.error(f"Error getting cached forecast: {e}")
            return None
            
    def _validate_forecast(self, forecast: pd.DataFrame) -> pd.DataFrame:
        """
        Validate and clean forecast data.
        
        :param forecast: Raw forecast DataFrame.
        :return: Validated forecast DataFrame.
        """
        try:
            validated = forecast.copy()
            
            for column, limits in self.validation_limits.items():
                if column in validated.columns:
                    # Check for out-of-range values
                    min_val, max_val = limits['min'], limits['max']
                    
                    # Clip values to valid range
                    validated[column] = validated[column].clip(min_val, max_val)
                    
                    # Check for NaN values
                    if validated[column].isna().any():
                        _log.warning(f"NaN values found in {column}, interpolating")
                        validated[column] = validated[column].interpolate()
                        
                        # Fill remaining NaN with reasonable defaults
                        defaults = {
                            'dni': 400,
                            'dhi': 100, 
                            'temp_air': 20,
                            'wind_speed': 2
                        }
                        validated[column] = validated[column].fillna(defaults.get(column, 0))
                        
            _log.debug("Weather forecast validated")
            return validated
            
        except Exception as e:
            _log.error(f"Error validating forecast: {e}")
            return forecast
            
    def _standardize_weather_data(self, data: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """
        Standardize weather data to AFC format.
        
        :param data: Raw weather data.
        :return: Standardized weather data or None.
        """
        try:
            # Common field mappings
            field_mappings = {
                'dni': ['dni', 'direct_normal_irradiance', 'beam_irradiance'],
                'dhi': ['dhi', 'diffuse_horizontal_irradiance', 'diffuse_irradiance'],
                'temp_air': ['temp_air', 'temperature', 'temp', 'air_temperature'],
                'wind_speed': ['wind_speed', 'windspeed', 'wind']
            }
            
            standardized = {}
            
            for afc_field, possible_names in field_mappings.items():
                value = None
                
                # Try to find the field in the data
                for name in possible_names:
                    if name in data:
                        value = data[name]
                        break
                        
                if value is not None:
                    try:
                        standardized[afc_field] = float(value)
                    except (ValueError, TypeError):
                        _log.warning(f"Could not convert {name} to float: {value}")
                        
            return standardized if standardized else None
            
        except Exception as e:
            _log.error(f"Error standardizing weather data: {e}")
            return None
            
    def get_status(self) -> Dict[str, Any]:
        """Get weather integration status."""
        return {
            'source': self.source,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'cache_valid': self._is_cache_valid(),
            'cached_hours': len(self.forecast_cache.get('data', [])),
            'current_weather_available': bool(self.current_weather),
            'config': {
                'update_interval': self.update_interval,
                'forecast_hours': self.forecast_hours,
                'validation_enabled': self.validation_enabled
            }
        }


class WeatherSource:
    """Base class for weather data sources."""
    
    def __init__(self, location: Dict[str, float]):
        self.location = location
        
    def get_forecast(self, hours: int) -> Optional[pd.DataFrame]:
        """Get weather forecast. Override in subclasses."""
        raise NotImplementedError
        
    def get_current(self) -> Optional[Dict[str, Any]]:
        """Get current weather. Override in subclasses."""
        raise NotImplementedError


class OpenWeatherMapSource(WeatherSource):
    """OpenWeatherMap API weather source."""
    
    def __init__(self, api_key: str, location: Dict[str, float]):
        super().__init__(location)
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"
        
    def get_forecast(self, hours: int) -> Optional[pd.DataFrame]:
        """Get forecast from OpenWeatherMap."""
        try:
            url = f"{self.base_url}/forecast"
            params = {
                'lat': self.location['lat'],
                'lon': self.location['lon'],
                'appid': self.api_key,
                'units': 'metric'
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Convert to AFC format
            forecast_list = []
            
            for item in data['list'][:hours]:
                timestamp = datetime.datetime.fromtimestamp(item['dt'])
                
                # Estimate solar irradiance from cloud cover and time
                clouds = item['clouds']['all'] / 100.0  # 0-1
                hour = timestamp.hour
                
                # Simple solar irradiance estimation
                if 6 <= hour <= 18:
                    max_dni = 800 * np.sin(np.pi * (hour - 6) / 12)
                    dni = max_dni * (1 - clouds * 0.8)
                    dhi = 100 + clouds * 150
                else:
                    dni = 0
                    dhi = 0
                    
                forecast_list.append({
                    'timestamp': timestamp,
                    'dni': max(0, dni),
                    'dhi': max(0, dhi),
                    'temp_air': item['main']['temp'],
                    'wind_speed': item['wind']['speed']
                })
                
            df = pd.DataFrame(forecast_list)
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            _log.error(f"Error getting OpenWeatherMap forecast: {e}")
            return None


class NWSSource(WeatherSource):
    """National Weather Service API source."""
    
    def __init__(self, location: Dict[str, float]):
        super().__init__(location)
        self.base_url = "https://api.weather.gov"
        
    def get_forecast(self, hours: int) -> Optional[pd.DataFrame]:
        """Get forecast from NWS (simplified implementation)."""
        try:
            # Note: This is a simplified implementation
            # Full NWS integration would require proper grid point lookup
            _log.warning("NWS integration not fully implemented, using simulation")
            return SimulationWeatherSource(self.location).get_forecast(hours)
            
        except Exception as e:
            _log.error(f"Error getting NWS forecast: {e}")
            return None


class SimulationWeatherSource(WeatherSource):
    """Simulated weather source for testing."""
    
    def __init__(self, location: Dict[str, float]):
        super().__init__(location)
        
    def get_forecast(self, hours: int) -> Optional[pd.DataFrame]:
        """Generate simulated weather forecast."""
        try:
            # Create time index
            start_time = datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
            times = pd.date_range(start_time, periods=hours, freq='H')
            
            # Generate realistic weather patterns
            hour_angles = 2 * np.pi * np.arange(hours) / 24
            day_angles = 2 * np.pi * np.arange(hours) / (24 * 7)  # Weekly cycle
            
            # Solar irradiance - peak at solar noon, zero at night
            solar_hours = np.array([t.hour for t in times])
            solar_elevation = np.maximum(0, np.sin(np.pi * (solar_hours - 6) / 12))
            
            # Add some randomness and weather patterns
            cloud_factor = 0.3 + 0.4 * np.sin(day_angles) + 0.2 * np.random.random(hours)
            cloud_factor = np.clip(cloud_factor, 0, 1)
            
            dni = 800 * solar_elevation * (1 - cloud_factor * 0.8)
            dhi = 50 + 150 * cloud_factor + 20 * np.random.random(hours)
            
            # Temperature - daily cycle with some randomness
            base_temp = 20 + 5 * np.sin(day_angles)  # Seasonal variation
            daily_temp = 8 * np.sin(hour_angles - np.pi/3)  # Daily variation
            temp_air = base_temp + daily_temp + 2 * np.random.normal(0, 1, hours)
            
            # Wind speed - some variation
            wind_speed = 3 + 2 * np.sin(hour_angles) + np.random.exponential(1, hours)
            wind_speed = np.clip(wind_speed, 0, 15)
            
            # Create DataFrame
            forecast = pd.DataFrame({
                'dni': np.maximum(0, dni),
                'dhi': np.maximum(0, dhi),
                'temp_air': temp_air,
                'wind_speed': wind_speed
            }, index=times)
            
            return forecast
            
        except Exception as e:
            _log.error(f"Error generating simulated forecast: {e}")
            return None
            
    def get_current(self) -> Optional[Dict[str, Any]]:
        """Get simulated current weather."""
        try:
            current_hour = datetime.datetime.now().hour
            
            # Simple current weather simulation
            if 6 <= current_hour <= 18:
                dni = 600 * np.sin(np.pi * (current_hour - 6) / 12)
                dhi = 100
            else:
                dni = 0
                dhi = 0
                
            return {
                'dni': max(0, dni + np.random.normal(0, 50)),
                'dhi': max(0, dhi + np.random.normal(0, 20)),
                'temp_air': 20 + 8 * np.sin(np.pi * (current_hour - 6) / 12) + np.random.normal(0, 2),
                'wind_speed': 2 + np.random.exponential(1)
            }
            
        except Exception as e:
            _log.error(f"Error getting simulated current weather: {e}")
            return None