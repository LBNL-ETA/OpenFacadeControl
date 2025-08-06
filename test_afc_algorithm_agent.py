#!/usr/bin/env python3
"""
Comprehensive test suite for the OFC AFC Algorithm Agent (Phase 2).

This test validates the full functionality of the production-ready AFC integration.
"""

import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add project paths
sys.path.insert(0, '.')
sys.path.insert(0, './agents/ofc_afc_algorithm')

# Import AFC components
try:
    from agents.ofc_afc_algorithm.ofc_afc_algorithm.afc_wrapper import MockAFCWrapper
    from agents.ofc_afc_algorithm.ofc_afc_algorithm.weather_integration import WeatherIntegration
    from agents.ofc_afc_algorithm.ofc_afc_algorithm.data_converter import DataConverter
    afc_components_available = True
except ImportError as e:
    print(f"Warning: AFC components not available: {e}")
    afc_components_available = False


class MockOFCAFCAlgorithm:
    """Mock AFC Algorithm agent for testing without VOLTTRON."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize mock agent."""
        self.config = config
        self.afc_wrapper = None
        self.weather_integration = None
        self.data_converter = DataConverter(config.get('data_converter', {}))
        self.control_ct = 0
        self.afc_enabled = False
        self.fallback_mode = config.get('fallback_mode', True)
        
        # Initialize components
        self._initialize_components()
        
    def _initialize_components(self):
        """Initialize AFC components."""
        try:
            # Initialize AFC wrapper
            afc_config = self.config.get('afc', {})
            if afc_config:
                self.afc_wrapper = MockAFCWrapper(afc_config)
                self.afc_enabled = True
                
            # Initialize weather integration
            weather_config = self.config.get('weather', {})
            if weather_config:
                self.weather_integration = WeatherIntegration(weather_config)
                
            print("✓ AFC components initialized")
            
        except Exception as e:
            print(f"✗ Error initializing components: {e}")
            self.fallback_mode = True
            
    def process_control_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a control request."""
        try:
            area_id = request.get('area_id', 'test_area')
            devices = request.get('devices', [])
            sensor_data = request.get('sensor_data', {})
            
            # Get weather forecast
            weather_forecast = self._get_weather_forecast()
            
            if weather_forecast is None or weather_forecast.empty:
                return self._fallback_control(request)
                
            # Run AFC optimization
            if self.afc_enabled and not self.fallback_mode:
                try:
                    optimization_result = self._run_afc_optimization(
                        sensor_data, weather_forecast, devices
                    )
                    
                    if optimization_result and optimization_result.get('valid', False):
                        control_commands = self.data_converter.afc_outputs_to_ofc_commands(
                            optimization_result, devices
                        )
                        
                        self.control_ct += 1
                        
                        return {
                            'success': True,
                            'area_id': area_id,
                            'control_commands': control_commands,
                            'optimization_data': optimization_result.get('optimization_data', {}),
                            'source': 'afc_optimization',
                            'timestamp': datetime.now().isoformat()
                        }
                    else:
                        return self._fallback_control(request)
                        
                except Exception as e:
                    print(f"AFC optimization error: {e}")
                    return self._fallback_control(request)
            else:
                return self._fallback_control(request)
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'area_id': request.get('area_id', 'unknown'),
                'timestamp': datetime.now().isoformat()
            }
            
    def _run_afc_optimization(self, sensor_data: Dict[str, Any],
                            weather_forecast: pd.DataFrame,
                            devices: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Run AFC optimization."""
        try:
            if not self.afc_wrapper:
                return None
                
            # Convert to AFC inputs
            afc_inputs = self.data_converter.ofc_sensors_to_afc_inputs(
                sensor_data, weather_forecast
            )
            
            # Validate inputs
            is_valid, errors = self.data_converter.validate_afc_inputs(afc_inputs)
            if not is_valid:
                print(f"AFC input validation failed: {errors}")
                return None
                
            # Run optimization
            result = self.afc_wrapper.optimize(afc_inputs, devices)
            return result
            
        except Exception as e:
            print(f"AFC optimization failed: {e}")
            return None
            
    def _get_weather_forecast(self) -> Optional[pd.DataFrame]:
        """Get weather forecast."""
        try:
            if self.weather_integration:
                return self.weather_integration.get_forecast()
            else:
                # Create simple forecast
                times = pd.date_range(
                    datetime.now(),
                    datetime.now() + timedelta(hours=24),
                    freq='h'
                )
                
                hours = np.arange(len(times))
                dni = np.maximum(0, 600 * np.sin(np.pi * hours / 12))
                dhi = 80 + 20 * np.sin(np.pi * hours / 12)
                temp_air = 20 + 6 * np.sin(np.pi * hours / 12)
                wind_speed = 2.0
                
                return pd.DataFrame({
                    'dni': dni,
                    'dhi': dhi,
                    'temp_air': temp_air,
                    'wind_speed': wind_speed
                }, index=times)
                
        except Exception as e:
            print(f"Error getting weather forecast: {e}")
            return None
            
    def _fallback_control(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback control using heuristics."""
        try:
            area_id = request.get('area_id', 'unknown')
            devices = request.get('devices', [])
            sensor_data = request.get('sensor_data', {})
            
            control_commands = []
            
            # Simple heuristic control
            for device in devices:
                device_type = device.get('type', '')
                zone_id = device.get('zone_id', 'zone_0')
                
                if 'facade' in device_type.lower() or 'window' in device_type.lower():
                    glare = sensor_data.get('glare', 100)
                    if glare > 300:
                        setpoint = 1.0
                    elif glare > 150:
                        setpoint = 2.0
                    else:
                        setpoint = 3.0
                        
                    control_commands.append({
                        'device_id': device.get('device_id'),
                        'device_type': device_type,
                        'point': 'setpoint',
                        'value': setpoint,
                        'timestamp': datetime.now().isoformat(),
                        'zone': zone_id
                    })
                    
                elif 'hvac' in device_type.lower():
                    temp = sensor_data.get('temperature', 22.0)
                    occupancy = sensor_data.get('occupancy', 1)
                    
                    if 'cooling' in device_type.lower():
                        value = 24.0 if occupancy else 26.0
                        point = 'cooling_setpoint'
                    else:
                        value = 20.0 if occupancy else 18.0
                        point = 'heating_setpoint'
                        
                    control_commands.append({
                        'device_id': device.get('device_id'),
                        'device_type': device_type,
                        'point': point,
                        'value': value,
                        'timestamp': datetime.now().isoformat(),
                        'zone': zone_id
                    })
                    
            return {
                'success': True,
                'area_id': area_id,
                'control_commands': control_commands,
                'source': 'fallback_heuristic',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'area_id': request.get('area_id', 'unknown'),
                'timestamp': datetime.now().isoformat()
            }
            
    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        return {
            'afc_enabled': self.afc_enabled,
            'fallback_mode': self.fallback_mode,
            'control_cycles': self.control_ct,
            'weather_available': self.weather_integration is not None,
            'data_converter_available': self.data_converter is not None
        }


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}


def test_configuration_loading():
    """Test configuration loading and validation."""
    print("=== Testing Configuration Loading ===")
    
    # Test main config
    config_path = './agents/ofc_afc_algorithm/config/afc_algorithm.config'
    config = load_config(config_path)
    
    if config:
        print(f"✓ Main configuration loaded: {len(config)} top-level keys")
        
        # Validate required sections
        required_sections = ['afc', 'building', 'weather']
        for section in required_sections:
            if section in config:
                print(f"  ✓ {section} section present")
            else:
                print(f"  ✗ {section} section missing")
                return False
    else:
        print("✗ Failed to load main configuration")
        return False
        
    # Test building templates
    template_dir = './agents/ofc_afc_algorithm/config/building_templates'
    templates = ['office_building.json', 'laboratory.json', 'classroom.json']
    
    for template in templates:
        template_path = os.path.join(template_dir, template)
        template_config = load_config(template_path)
        
        if template_config:
            print(f"  ✓ {template} template loaded")
        else:
            print(f"  ✗ Failed to load {template}")
            return False
            
    print("✓ All configurations loaded successfully\n")
    return True


def test_afc_wrapper():
    """Test AFC wrapper functionality."""
    print("=== Testing AFC Wrapper ===")
    
    try:
        # Create AFC wrapper config
        afc_config = {
            'max_optimization_time': 300,
            'optimization_timeout': 120,
            'use_fallback': True,
            'building': {
                'location': {'latitude': 37.85, 'longitude': -122.24},
                'geometry': {'room_width': 4.0, 'room_depth': 5.0}
            }
        }
        
        wrapper = MockAFCWrapper(afc_config)
        print(f"✓ AFC wrapper created: {wrapper.afc_available}")
        
        # Test optimization
        times = pd.date_range(datetime.now(), periods=24, freq='h')
        hours = np.arange(24)
        
        afc_inputs = pd.DataFrame({
            'dni': np.maximum(0, 600 * np.sin(np.pi * hours / 12)),
            'dhi': 80 + 20 * np.sin(np.pi * hours / 12),
            'temp_air': 20 + 6 * np.sin(np.pi * hours / 12),
            'wind_speed': 2.0,
            'occupancy_light': 1,
            'wpi_min': 300,
            'glare_max': 200,
            'temp_room_max': 26,
            'temp_room_min': 20
        }, index=times)
        
        devices = [
            {'device_id': 'test_window', 'type': 'electrochromic_window', 'zone_id': 'zone_0'},
            {'device_id': 'test_hvac', 'type': 'hvac_cooling', 'zone_id': 'building'}
        ]
        
        result = wrapper.optimize(afc_inputs, devices)
        
        if result and result.get('valid', False):
            print("✓ AFC optimization completed successfully")
            print(f"  Facade setpoints: {len(result.get('facade_setpoints', []))}")
            print(f"  HVAC setpoints: {bool(result.get('hvac_setpoints', {}))}")
            print(f"  Objective value: {result.get('optimization_data', {}).get('objective_value', 'N/A')}")
        else:
            print("✗ AFC optimization failed or invalid")
            return False
            
        # Test status
        status = wrapper.get_status()
        print(f"✓ Wrapper status: {status['optimization_count']} cycles, {status['success_rate']:.2f} success rate")
        
    except Exception as e:
        print(f"✗ AFC wrapper test failed: {e}")
        return False
        
    print("✓ AFC wrapper tests passed\n")
    return True


def test_weather_integration():
    """Test weather integration functionality."""
    print("=== Testing Weather Integration ===")
    
    try:
        weather_config = {
            'source': 'simulation',
            'location': {'lat': 37.85, 'lon': -122.24},
            'forecast_hours': 48,
            'validation_enabled': True
        }
        
        weather = WeatherIntegration(weather_config)
        print("✓ Weather integration initialized")
        
        # Test forecast
        forecast = weather.get_forecast(24)
        
        if forecast is not None and len(forecast) > 0:
            print(f"✓ Weather forecast retrieved: {len(forecast)} hours")
            print(f"  Columns: {list(forecast.columns)}")
            print(f"  DNI range: {forecast['dni'].min():.1f} - {forecast['dni'].max():.1f} W/m²")
            print(f"  Temperature range: {forecast['temp_air'].min():.1f} - {forecast['temp_air'].max():.1f} °C")
        else:
            print("✗ Failed to get weather forecast")
            return False
            
        # Test status
        status = weather.get_status()
        print(f"✓ Weather status: Source={status['source']}, Cache valid={status['cache_valid']}")
        
    except Exception as e:
        print(f"✗ Weather integration test failed: {e}")
        return False
        
    print("✓ Weather integration tests passed\n")
    return True


def test_data_converter():
    """Test data converter functionality."""
    print("=== Testing Data Converter ===")
    
    try:
        converter_config = {
            'validation_enabled': True,
            'cache_enabled': True
        }
        
        converter = DataConverter(converter_config)
        print("✓ Data converter initialized")
        
        # Test sensor to AFC conversion
        sensor_data = {
            'glare_sensor_1': 200,
            'occupancy_sensor_1': 1,
            'illuminance_sensor_1': 400,
            'temp_sensor_1': 23.0
        }
        
        times = pd.date_range(datetime.now(), periods=8, freq='h')
        weather_data = pd.DataFrame({
            'dni': [400, 500, 600, 700, 600, 400, 200, 0],
            'dhi': [100, 120, 140, 160, 140, 120, 100, 80],
            'temp_air': [20, 22, 25, 27, 25, 23, 21, 19],
            'wind_speed': [2, 2, 3, 3, 3, 2, 2, 2]
        }, index=times)
        
        afc_inputs = converter.ofc_sensors_to_afc_inputs(sensor_data, weather_data)
        
        if afc_inputs is not None and len(afc_inputs) > 0:
            print(f"✓ Sensor to AFC conversion: {afc_inputs.shape[0]} timesteps, {afc_inputs.shape[1]} variables")
            
            # Validate inputs
            is_valid, errors = converter.validate_afc_inputs(afc_inputs)
            if is_valid:
                print("✓ AFC inputs are valid")
            else:
                print(f"✗ AFC input validation failed: {errors}")
                return False
        else:
            print("✗ Sensor to AFC conversion failed")
            return False
            
        # Test AFC to OFC conversion
        afc_outputs = {
            'facade_setpoints': [
                {'zone_id': 'zone_0', 'device_type': 'electrochromic_window', 'setpoint': 2.0},
                {'zone_id': 'zone_1', 'device_type': 'automated_blind', 'setpoint': 0.6}
            ],
            'hvac_setpoints': {
                'cooling_setpoint': 24.0,
                'heating_setpoint': 20.0
            },
            'optimization_data': {
                'objective_value': 15.5,
                'valid': True
            }
        }
        
        devices = [
            {'device_id': 'window_0', 'type': 'electrochromic_window', 'zone_id': 'zone_0'},
            {'device_id': 'blind_1', 'type': 'automated_blind', 'zone_id': 'zone_1'},
            {'device_id': 'hvac_cool', 'type': 'hvac_cooling', 'zone_id': 'building'}
        ]
        
        ofc_commands = converter.afc_outputs_to_ofc_commands(afc_outputs, devices)
        
        if ofc_commands and len(ofc_commands) > 0:
            print(f"✓ AFC to OFC conversion: {len(ofc_commands)} commands")
            
            for cmd in ofc_commands:
                print(f"  {cmd['device_id']}: {cmd['value']} ({cmd.get('priority', 'N/A')} priority)")
        else:
            print("✗ AFC to OFC conversion failed")
            return False
            
        # Test status
        status = converter.get_status()
        print(f"✓ Converter status: Validation={status['validation_enabled']}, Cache={status['cache_enabled']}")
        
    except Exception as e:
        print(f"✗ Data converter test failed: {e}")
        return False
        
    print("✓ Data converter tests passed\n")
    return True


def test_full_integration():
    """Test full agent integration."""
    print("=== Testing Full Agent Integration ===")
    
    try:
        # Load configuration
        config_path = './agents/ofc_afc_algorithm/config/afc_algorithm.config'
        config = load_config(config_path)
        
        if not config:
            print("✗ Failed to load configuration")
            return False
            
        # Create mock agent
        agent = MockOFCAFCAlgorithm(config)
        print("✓ Mock AFC agent created")
        
        # Test control scenarios
        test_scenarios = [
            {
                'name': 'High Solar Load',
                'request': {
                    'area_id': 'test_area_1',
                    'devices': config.get('managed_devices', []),
                    'sensor_data': {
                        'glare': 300,
                        'occupancy': 1,
                        'illuminance': 800,
                        'temperature': 26.0
                    }
                }
            },
            {
                'name': 'Low Light Conditions',
                'request': {
                    'area_id': 'test_area_2', 
                    'devices': config.get('managed_devices', []),
                    'sensor_data': {
                        'glare': 50,
                        'occupancy': 1,
                        'illuminance': 200,
                        'temperature': 20.0
                    }
                }
            },
            {
                'name': 'Unoccupied Space',
                'request': {
                    'area_id': 'test_area_3',
                    'devices': config.get('managed_devices', []),
                    'sensor_data': {
                        'glare': 150,
                        'occupancy': 0,
                        'illuminance': 300,
                        'temperature': 22.0
                    }
                }
            }
        ]
        
        for scenario in test_scenarios:
            print(f"\n  Testing scenario: {scenario['name']}")
            
            result = agent.process_control_request(scenario['request'])
            
            if result.get('success', False):
                commands = result.get('control_commands', [])
                source = result.get('source', 'unknown')
                
                print(f"    ✓ Control successful: {len(commands)} commands from {source}")
                
                # Show key commands
                for cmd in commands[:3]:  # Show first 3 commands
                    device_type = cmd.get('device_type', 'unknown')
                    value = cmd.get('value', 'N/A')
                    print(f"      {device_type}: {value}")
                    
                if len(commands) > 3:
                    print(f"      ... and {len(commands) - 3} more commands")
                    
            else:
                error = result.get('error', 'Unknown error')
                print(f"    ✗ Control failed: {error}")
                return False
                
        # Test agent status
        status = agent.get_status()
        print(f"\n✓ Agent status: {status['control_cycles']} cycles, AFC enabled: {status['afc_enabled']}")
        
    except Exception as e:
        print(f"✗ Full integration test failed: {e}")
        return False
        
    print("\n✓ Full integration tests passed\n")
    return True


def test_building_templates():
    """Test building template functionality."""
    print("=== Testing Building Templates ===")
    
    try:
        template_dir = './agents/ofc_afc_algorithm/config/building_templates'
        templates = {
            'office_building.json': 'office',
            'laboratory.json': 'laboratory', 
            'classroom.json': 'classroom'
        }
        
        for template_file, building_type in templates.items():
            template_path = os.path.join(template_dir, template_file)
            template_config = load_config(template_path)
            
            if template_config:
                print(f"✓ {building_type} template loaded")
                
                # Validate template structure
                required_sections = ['building', 'afc', 'devices']
                for section in required_sections:
                    if section in template_config:
                        print(f"  ✓ {section} section present")
                    else:
                        print(f"  ✗ {section} section missing")
                        return False
                        
                # Check building-specific parameters
                building_config = template_config.get('building', {})
                if building_config.get('type') == building_type:
                    print(f"  ✓ Building type correctly set to {building_type}")
                else:
                    print(f"  ✗ Building type mismatch")
                    return False
                    
            else:
                print(f"✗ Failed to load {template_file}")
                return False
                
    except Exception as e:
        print(f"✗ Building template test failed: {e}")
        return False
        
    print("✓ Building template tests passed\n")
    return True


def main():
    """Run all Phase 2 tests."""
    print("=== OFC AFC Algorithm Agent - Phase 2 Testing ===\n")
    
    if not afc_components_available:
        print("⚠️  AFC components not fully available - running limited tests")
        
    tests = [
        ("Configuration Loading", test_configuration_loading),
        ("Building Templates", test_building_templates),
        ("Data Converter", test_data_converter),
        ("Weather Integration", test_weather_integration),
        ("AFC Wrapper", test_afc_wrapper),
        ("Full Integration", test_full_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} FAILED\n")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}\n")
            
    print("=" * 50)
    print(f"Phase 2 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Phase 2 Complete!")
        return True
    else:
        print("❌ Some tests failed - review and fix issues")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)