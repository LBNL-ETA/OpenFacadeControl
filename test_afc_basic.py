#!/usr/bin/env python3
"""
Basic AFC functionality test for Phase 1 integration.
Tests core AFC imports and data structures without full optimization.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add AFC to path
sys.path.append('./afc')

def test_afc_imports():
    """Test basic AFC imports"""
    try:
        from afc.ctrlWrapper import Controller, make_inputs
        from afc.defaultConfig import default_parameter
        print("✓ AFC core imports successful")
        return True
    except ImportError as e:
        print(f"✗ AFC import failed: {e}")
        return False

def test_afc_config():
    """Test AFC configuration loading"""
    try:
        from afc.defaultConfig import default_parameter
        config = default_parameter()
        print("✓ AFC default configuration loaded")
        print(f"  Building geometry: {config['radiance']['dimensions']}")
        print(f"  Facade type: {config['facade']['type']}")
        print(f"  Location: {config['radiance']['location']}")
        return config
    except Exception as e:
        print(f"✗ AFC configuration failed: {e}")
        return None

def test_weather_data():
    """Create simple weather data for testing"""
    try:
        # Create 24-hour weather forecast
        times = pd.date_range('2023-07-01 00:00:00', '2023-07-01 23:00:00', freq='H')
        
        # Simple weather pattern
        hours = np.arange(len(times))
        dni = np.maximum(0, 800 * np.sin(np.pi * (hours - 6) / 12))  # Peak at noon
        dni[hours < 6] = 0  # No sun before 6 AM
        dni[hours > 18] = 0  # No sun after 6 PM
        
        dhi = 100 + 50 * np.sin(np.pi * hours / 12)  # Diffuse light
        temp_air = 20 + 8 * np.sin(np.pi * (hours - 6) / 12)  # Temperature cycle
        wind_speed = 2 + 1 * np.sin(np.pi * hours / 24)  # Light wind
        
        weather_df = pd.DataFrame({
            'dni': dni,
            'dhi': dhi,
            'temp_air': temp_air,
            'wind_speed': wind_speed
        }, index=times)
        
        print("✓ Weather data created")
        print(f"  Time range: {weather_df.index[0]} to {weather_df.index[-1]}")
        print(f"  Peak DNI: {weather_df['dni'].max():.1f} W/m²")
        print(f"  Temperature range: {weather_df['temp_air'].min():.1f}°C to {weather_df['temp_air'].max():.1f}°C")
        
        return weather_df
    except Exception as e:
        print(f"✗ Weather data creation failed: {e}")
        return None

def test_afc_controller_init():
    """Test AFC controller initialization"""
    try:
        from afc.ctrlWrapper import Controller
        controller = Controller()
        print("✓ AFC Controller instantiated")
        print(f"  Controller type: {type(controller)}")
        return controller
    except Exception as e:
        print(f"✗ AFC Controller initialization failed: {e}")
        return None

def test_make_inputs():
    """Test AFC input creation"""
    try:
        from afc.ctrlWrapper import make_inputs
        from afc.defaultConfig import default_parameter
        
        # Get configuration
        parameter = default_parameter()
        
        # Create simple weather data
        weather_df = test_weather_data()
        if weather_df is None:
            return False
            
        # Take first few hours for testing
        df = weather_df.iloc[:3]
        
        # Create AFC inputs
        inputs = make_inputs(parameter, df)
        
        print("✓ AFC inputs created")
        print(f"  Input keys: {list(inputs.keys())}")
        print(f"  Input data type: {type(inputs['input-data'])}")
        
        return inputs
    except Exception as e:
        print(f"✗ AFC input creation failed: {e}")
        return None

def main():
    """Run basic AFC tests for Phase 1"""
    print("=== AFC Basic Functionality Test ===\n")
    
    # Test 1: Imports
    if not test_afc_imports():
        return False
    
    # Test 2: Configuration
    config = test_afc_config()
    if config is None:
        return False
    
    # Test 3: Weather data
    weather_df = test_weather_data()
    if weather_df is None:
        return False
    
    # Test 4: Controller initialization
    controller = test_afc_controller_init()
    if controller is None:
        return False
    
    # Test 5: Input creation
    inputs = test_make_inputs()
    if inputs is None:
        return False
    
    print("\n=== All Basic Tests Passed ===")
    print("AFC core functionality is working!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)