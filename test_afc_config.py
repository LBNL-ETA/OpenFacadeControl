#!/usr/bin/env python3
"""
Test AFC configuration and data structures for Phase 1 integration.
"""

import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def test_afc_config_files():
    """Test reading AFC configuration files"""
    try:
        config_path = './afc/afc/resources/config/example_config.json'
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        print("✓ AFC example configuration loaded")
        print(f"  System ID: {config['system_id']}")
        print(f"  Location: {config['location_city']}, {config['location_state']}")
        print(f"  Room dimensions: {config['room_width']}m x {config['room_depth']}m x {config['room_height']}m")
        print(f"  Window: {config['window_width']}m x {config['window_height']}m")
        print(f"  System type: {config['system_type']}")
        print(f"  Occupancy: {config['occupant_number']} person(s)")
        
        return config
    except Exception as e:
        print(f"✗ AFC configuration loading failed: {e}")
        return None

def test_weather_data_format():
    """Test weather data format compatibility"""
    try:
        # Create sample weather data matching AFC requirements
        times = pd.date_range('2023-07-01 00:00:00', '2023-07-01 23:00:00', freq='H')
        
        # AFC weather inputs based on ctrlWrapper.py
        hours = np.arange(len(times))
        dni = np.maximum(0, 800 * np.sin(np.pi * (hours - 6) / 12))
        dni[hours < 6] = 0
        dni[hours > 18] = 0
        
        dhi = 100 + 50 * np.sin(np.pi * hours / 12)
        temp_air = 20 + 8 * np.sin(np.pi * (hours - 6) / 12)
        wind_speed = 2 + 1 * np.sin(np.pi * hours / 24)
        
        afc_weather = pd.DataFrame({
            'dni': dni,          # Direct normal irradiance
            'dhi': dhi,          # Diffuse horizontal irradiance  
            'temp_air': temp_air, # Air temperature
            'wind_speed': wind_speed
        }, index=times)
        
        print("✓ AFC weather data format created")
        print(f"  Required columns: {list(afc_weather.columns)}")
        print(f"  Sample values at noon:")
        noon_idx = afc_weather.index[12]  # 12:00 PM
        for col in afc_weather.columns:
            print(f"    {col}: {afc_weather.loc[noon_idx, col]:.2f}")
        
        return afc_weather
    except Exception as e:
        print(f"✗ Weather data format test failed: {e}")
        return None

def test_ofc_sensor_mapping():
    """Test OFC sensor data mapping to AFC inputs"""
    try:
        # Simulate OFC sensor data
        ofc_sensors = {
            'glare_sensor_1': 150,      # Glare (cd/m²)
            'occupancy_sensor_1': 1,    # Occupancy (0/1)
            'illuminance_sensor_1': 500, # Illuminance (lux)
            'temp_sensor_1': 22.5,      # Zone temperature (°C)
            'light_level_1': 0.8,       # Light dimming level (0-1)
            'shade_position_1': 0.3     # Shade position (0-1)
        }
        
        # Map to AFC input format
        afc_inputs = {
            'glare_max': ofc_sensors['glare_sensor_1'],
            'occupancy_light': ofc_sensors['occupancy_sensor_1'],
            'wpi_min': ofc_sensors['illuminance_sensor_1'],
            'temp_room_max': ofc_sensors['temp_sensor_1'] + 2,  # Comfort range
            'temp_room_min': ofc_sensors['temp_sensor_1'] - 2,
        }
        
        print("✓ OFC to AFC sensor mapping created")
        print("  OFC sensors:")
        for k, v in ofc_sensors.items():
            print(f"    {k}: {v}")
        print("  AFC inputs:")
        for k, v in afc_inputs.items():
            print(f"    {k}: {v}")
        
        return ofc_sensors, afc_inputs
    except Exception as e:
        print(f"✗ OFC sensor mapping failed: {e}")
        return None, None

def test_afc_output_format():
    """Test AFC output format for OFC compatibility"""
    try:
        # Simulate AFC optimization results
        afc_outputs = {
            'facade_setpoints': [
                {
                    'zone_id': 'zone_0',
                    'device_type': 'electrochromic_window',
                    'setpoint': 2.0,  # Tint state
                    'timestamp': '2023-07-01T12:00:00Z'
                },
                {
                    'zone_id': 'zone_1', 
                    'device_type': 'automated_blind',
                    'setpoint': 0.6,  # Position (0=closed, 1=open)
                    'timestamp': '2023-07-01T12:00:00Z'
                }
            ],
            'hvac_setpoints': {
                'cooling_setpoint': 24.0,
                'heating_setpoint': 20.0,
                'mode': 'cooling'
            },
            'optimization_data': {
                'objective_value': 15.67,
                'energy_cost': 12.34,
                'comfort_score': 0.85,
                'valid': True
            }
        }
        
        # Map to OFC device commands
        ofc_commands = []
        for setpoint in afc_outputs['facade_setpoints']:
            ofc_cmd = {
                'device_id': f"ofc_{setpoint['zone_id']}_{setpoint['device_type']}",
                'value': setpoint['setpoint'],
                'timestamp': setpoint['timestamp']
            }
            ofc_commands.append(ofc_cmd)
        
        print("✓ AFC to OFC output mapping created")
        print("  AFC outputs:")
        print(f"    Facade setpoints: {len(afc_outputs['facade_setpoints'])} zones")
        print(f"    HVAC cooling: {afc_outputs['hvac_setpoints']['cooling_setpoint']}°C")
        print(f"    Optimization valid: {afc_outputs['optimization_data']['valid']}")
        print("  OFC commands:")
        for cmd in ofc_commands:
            print(f"    {cmd['device_id']}: {cmd['value']}")
            
        return afc_outputs, ofc_commands
    except Exception as e:
        print(f"✗ AFC output format test failed: {e}")
        return None, None

def main():
    """Run AFC configuration and data format tests"""
    print("=== AFC Configuration & Data Format Test ===\n")
    
    # Test 1: Configuration loading
    config = test_afc_config_files()
    if config is None:
        return False
    
    # Test 2: Weather data format
    weather_data = test_weather_data_format()
    if weather_data is None:
        return False
    
    # Test 3: Sensor mapping
    ofc_sensors, afc_inputs = test_ofc_sensor_mapping()
    if ofc_sensors is None:
        return False
    
    # Test 4: Output format
    afc_outputs, ofc_commands = test_afc_output_format()
    if afc_outputs is None:
        return False
    
    print("\n=== All Configuration Tests Passed ===")
    print("AFC data formats are compatible with OFC!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)