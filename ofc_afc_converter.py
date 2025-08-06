#!/usr/bin/env python3
"""
OFC-AFC Data Conversion Utilities for Phase 1 Integration

This module provides conversion functions between OFC and AFC data formats,
enabling seamless data exchange during the integration process.
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple


class OFCAFCConverter:
    """Data conversion utilities for OFC-AFC integration"""
    
    def __init__(self):
        """Initialize converter with default mappings"""
        self.ofc_to_afc_sensor_map = {
            'glare_sensor': 'glare_max',
            'occupancy_sensor': 'occupancy_light', 
            'illuminance_sensor': 'wpi_min',
            'temp_sensor': 'temp_room',
            'light_level': 'lighting_level',
            'shade_position': 'shade_position'
        }
        
        self.afc_to_ofc_device_map = {
            'electrochromic_window': 'electrochromic_window',
            'automated_blind': 'hunter_douglas_shade',
            'dimmable_light': 'cree_light',
            'hvac_cooling': 'hvac_cooling',
            'hvac_heating': 'hvac_heating'
        }
    
    def ofc_sensors_to_afc_inputs(self, ofc_sensor_data: Dict[str, Any], 
                                 weather_data: pd.DataFrame) -> pd.DataFrame:
        """
        Convert OFC sensor data to AFC input format
        
        Args:
            ofc_sensor_data: OFC sensor readings
            weather_data: Weather forecast data with dni, dhi, temp_air, wind_speed
            
        Returns:
            DataFrame with AFC-compatible input data
        """
        try:
            # Start with weather data
            afc_inputs = weather_data.copy()
            
            # Add default occupancy and comfort parameters
            defaults = {
                'plug_load': 100,  # W
                'occupant_load': 100,  # W  
                'equipment': 50,  # W
                'occupancy_light': 1,  # Occupied
                'wpi_min': 300,  # Minimum illuminance (lux)
                'glare_max': 2000,  # Maximum glare (DGP)
                'temp_room_max': 26,  # °C
                'temp_room_min': 20,  # °C
                'generation_pv': 0,
                'load_demand': 0,
                'temp_slab_max': 1000,
                'temp_slab_min': 0,
                'temp_wall_max': 1000,
                'temp_wall_min': 0,
                'grid_co2_intensity': 0
            }
            
            # Apply defaults
            for key, value in defaults.items():
                if key not in afc_inputs.columns:
                    afc_inputs[key] = value
            
            # Override with actual sensor data if available
            for ofc_key, ofc_value in ofc_sensor_data.items():
                if 'glare' in ofc_key.lower():
                    afc_inputs['glare_max'] = ofc_value
                elif 'occupancy' in ofc_key.lower():
                    afc_inputs['occupancy_light'] = ofc_value
                elif 'illuminance' in ofc_key.lower():
                    afc_inputs['wpi_min'] = ofc_value
                elif 'temp' in ofc_key.lower():
                    # Set comfort range around current temperature
                    temp = float(ofc_value)
                    afc_inputs['temp_room_max'] = temp + 2
                    afc_inputs['temp_room_min'] = temp - 2
            
            return afc_inputs
            
        except Exception as e:
            raise ValueError(f"OFC to AFC conversion failed: {e}")
    
    def afc_outputs_to_ofc_commands(self, afc_outputs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert AFC optimization outputs to OFC device commands
        
        Args:
            afc_outputs: AFC controller outputs
            
        Returns:
            List of OFC device commands
        """
        try:
            ofc_commands = []
            
            # Process facade setpoints
            if 'facade_setpoints' in afc_outputs:
                for setpoint in afc_outputs['facade_setpoints']:
                    zone_id = setpoint.get('zone_id', 'zone_0')
                    device_type = setpoint.get('device_type', 'electrochromic_window')
                    value = setpoint.get('setpoint', 0)
                    timestamp = setpoint.get('timestamp', datetime.now().isoformat())
                    
                    # Map AFC device type to OFC device type
                    ofc_device_type = self.afc_to_ofc_device_map.get(device_type, device_type)
                    
                    ofc_cmd = {
                        'device_id': f"ofc_{zone_id}_{ofc_device_type}",
                        'device_type': ofc_device_type,
                        'point': 'setpoint',
                        'value': float(value),
                        'timestamp': timestamp,
                        'zone': zone_id
                    }
                    ofc_commands.append(ofc_cmd)
            
            # Process HVAC setpoints
            if 'hvac_setpoints' in afc_outputs:
                hvac = afc_outputs['hvac_setpoints']
                timestamp = datetime.now().isoformat()
                
                if 'cooling_setpoint' in hvac:
                    ofc_commands.append({
                        'device_id': 'ofc_hvac_cooling',
                        'device_type': 'hvac_cooling',
                        'point': 'cooling_setpoint',
                        'value': float(hvac['cooling_setpoint']),
                        'timestamp': timestamp,
                        'zone': 'building'
                    })
                
                if 'heating_setpoint' in hvac:
                    ofc_commands.append({
                        'device_id': 'ofc_hvac_heating', 
                        'device_type': 'hvac_heating',
                        'point': 'heating_setpoint',
                        'value': float(hvac['heating_setpoint']),
                        'timestamp': timestamp,
                        'zone': 'building'
                    })
            
            return ofc_commands
            
        except Exception as e:
            raise ValueError(f"AFC to OFC conversion failed: {e}")
    
    def ofc_config_to_afc_parameters(self, ofc_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert OFC building configuration to AFC parameters
        
        Args:
            ofc_config: OFC building configuration
            
        Returns:
            AFC parameter dictionary
        """
        try:
            # Default AFC configuration based on example_config.json
            afc_params = {
                'system_id': ofc_config.get('system_id', 'OFC-Integration'),
                'location_state': ofc_config.get('location_state', 'CA'),
                'location_city': ofc_config.get('location_city', 'Berkeley'),
                'location_latitude': ofc_config.get('latitude', 37.85),
                'location_longitude': ofc_config.get('longitude', -122.24),
                'location_elevation': ofc_config.get('elevation', 51.8),
                'location_orientation': ofc_config.get('orientation', 0),
                
                # Room geometry
                'room_width': ofc_config.get('room_width', 3.0),
                'room_height': ofc_config.get('room_height', 3.4), 
                'room_depth': ofc_config.get('room_depth', 4.6),
                
                # Window configuration
                'window_width': ofc_config.get('window_width', 1.4),
                'window_height': ofc_config.get('window_height', 2.6),
                'window_sill': ofc_config.get('window_sill', 0.2),
                'window_count': ofc_config.get('window_count', 2),
                
                # Building systems
                'system_type': ofc_config.get('facade_type', 'ec-71t'),
                'system_light': ofc_config.get('lighting_type', 'LED'),
                'system_cooling': ofc_config.get('cooling_type', 'el'),
                'system_cooling_eff': ofc_config.get('cooling_efficiency', 3.5),
                'system_heating': ofc_config.get('heating_type', 'el'),
                'system_heating_eff': ofc_config.get('heating_efficiency', 0.95),
                
                # Occupancy
                'occupant_number': ofc_config.get('occupant_count', 1),
                'occupant_1_direction': ofc_config.get('occupant_direction', 's'),
                'occupant_1_distance': ofc_config.get('occupant_distance', 1.22),
                'occupant_brightness': ofc_config.get('brightness_preference', 100),
                'occupant_glare': ofc_config.get('glare_tolerance', 100),
                
                # Utility
                'tariff_name': ofc_config.get('tariff', 'e19-2020'),
                'building_age': ofc_config.get('building_age', 'new_constr'),
                'debug': ofc_config.get('debug', False)
            }
            
            return afc_params
            
        except Exception as e:
            raise ValueError(f"OFC config to AFC parameters conversion failed: {e}")
    
    def validate_afc_inputs(self, afc_inputs: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate AFC input data format and completeness
        
        Args:
            afc_inputs: AFC input DataFrame
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Required columns
        required_cols = ['dni', 'dhi', 'temp_air', 'wind_speed', 'occupancy_light',
                        'wpi_min', 'glare_max', 'temp_room_max', 'temp_room_min']
        
        for col in required_cols:
            if col not in afc_inputs.columns:
                errors.append(f"Missing required column: {col}")
        
        # Check for NaN values
        if afc_inputs.isnull().any().any():
            errors.append("Input data contains NaN values")
        
        # Validate ranges
        if 'dni' in afc_inputs.columns:
            if (afc_inputs['dni'] < 0).any():
                errors.append("DNI values cannot be negative")
        
        if 'temp_room_max' in afc_inputs.columns and 'temp_room_min' in afc_inputs.columns:
            if (afc_inputs['temp_room_max'] <= afc_inputs['temp_room_min']).any():
                errors.append("temp_room_max must be greater than temp_room_min")
        
        return len(errors) == 0, errors
    
    def create_sample_ofc_data(self) -> Tuple[Dict[str, Any], pd.DataFrame, Dict[str, Any]]:
        """
        Create sample OFC data for testing
        
        Returns:
            Tuple of (sensor_data, weather_data, config)
        """
        # Sample sensor data
        sensor_data = {
            'glare_sensor_1': 180,
            'occupancy_sensor_1': 1,
            'illuminance_sensor_1': 450,
            'temp_sensor_1': 22.0,
            'light_level_1': 0.7,
            'shade_position_1': 0.4
        }
        
        # Sample weather data
        times = pd.date_range('2023-07-01 09:00:00', '2023-07-01 17:00:00', freq='h')
        hours = np.arange(len(times))
        
        weather_data = pd.DataFrame({
            'dni': np.maximum(0, 700 * np.sin(np.pi * hours / (len(hours)-1))),
            'dhi': 80 + 30 * np.sin(np.pi * hours / (len(hours)-1)),
            'temp_air': 18 + 10 * np.sin(np.pi * hours / (len(hours)-1)),
            'wind_speed': 2 + 0.5 * np.sin(2 * np.pi * hours / (len(hours)-1))
        }, index=times)
        
        # Sample configuration
        config = {
            'system_id': 'OFC-Test-Building',
            'location_city': 'Berkeley',
            'location_state': 'CA',
            'latitude': 37.85,
            'longitude': -122.24,
            'room_width': 4.0,
            'room_depth': 5.0,
            'room_height': 3.5,
            'window_width': 2.0,
            'window_height': 2.8,
            'facade_type': 'ec-71t',
            'occupant_count': 2
        }
        
        return sensor_data, weather_data, config


def test_converter():
    """Test the OFC-AFC converter functionality"""
    print("=== Testing OFC-AFC Converter ===\n")
    
    converter = OFCAFCConverter()
    
    # Create sample data
    sensor_data, weather_data, config = converter.create_sample_ofc_data()
    
    print("1. Testing OFC to AFC input conversion...")
    try:
        afc_inputs = converter.ofc_sensors_to_afc_inputs(sensor_data, weather_data)
        print(f"✓ Converted to AFC inputs: {afc_inputs.shape[0]} timesteps, {afc_inputs.shape[1]} variables")
        
        # Validate inputs
        is_valid, errors = converter.validate_afc_inputs(afc_inputs)
        if is_valid:
            print("✓ AFC inputs are valid")
        else:
            print(f"✗ AFC input validation errors: {errors}")
            
    except Exception as e:
        print(f"✗ Input conversion failed: {e}")
        return False
    
    print("\n2. Testing AFC to OFC output conversion...")
    try:
        # Sample AFC outputs
        afc_outputs = {
            'facade_setpoints': [
                {'zone_id': 'zone_0', 'device_type': 'electrochromic_window', 'setpoint': 2.0},
                {'zone_id': 'zone_1', 'device_type': 'automated_blind', 'setpoint': 0.6}
            ],
            'hvac_setpoints': {
                'cooling_setpoint': 24.0,
                'heating_setpoint': 21.0
            }
        }
        
        ofc_commands = converter.afc_outputs_to_ofc_commands(afc_outputs)
        print(f"✓ Converted to OFC commands: {len(ofc_commands)} device commands")
        
        for cmd in ofc_commands:
            print(f"  {cmd['device_id']}: {cmd['value']}")
            
    except Exception as e:
        print(f"✗ Output conversion failed: {e}")
        return False
    
    print("\n3. Testing OFC config to AFC parameters...")
    try:
        afc_params = converter.ofc_config_to_afc_parameters(config)
        print(f"✓ Converted to AFC parameters: {len(afc_params)} parameters")
        print(f"  Building: {afc_params['room_width']}x{afc_params['room_depth']}x{afc_params['room_height']}m")
        print(f"  Location: {afc_params['location_city']}, {afc_params['location_state']}")
        print(f"  System: {afc_params['system_type']}")
        
    except Exception as e:
        print(f"✗ Config conversion failed: {e}")
        return False
    
    print("\n=== All Converter Tests Passed ===")
    return True


if __name__ == "__main__":
    success = test_converter()
    exit(0 if success else 1)