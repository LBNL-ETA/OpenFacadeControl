#!/usr/bin/env python3
"""
Test the basic AFC agent functionality without VOLTTRON dependencies.
"""

import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project path
sys.path.insert(0, '.')

# Import converter
from ofc_afc_converter import OFCAFCConverter


class MockAFCAgent:
    """Mock AFC agent for testing basic functionality"""
    
    def __init__(self):
        self.converter = OFCAFCConverter()
        self.control_ct = 0
        
    def simulate_afc_optimization(self, sensor_data):
        """Simulate AFC optimization"""
        try:
            self.control_ct += 1
            
            # Create sample weather data
            current_time = datetime.now()
            times = pd.date_range(current_time, current_time + timedelta(hours=8), freq='h')
            
            # Simulate weather forecast
            hours = np.arange(len(times))
            weather_df = pd.DataFrame({
                'dni': np.maximum(0, 600 * np.sin(np.pi * hours / (len(hours)-1))),
                'dhi': 80 + 20 * np.sin(np.pi * hours / (len(hours)-1)),
                'temp_air': 20 + 6 * np.sin(np.pi * hours / (len(hours)-1)),
                'wind_speed': 2.0
            }, index=times)
            
            # Convert to AFC inputs
            afc_inputs = self.converter.ofc_sensors_to_afc_inputs(sensor_data, weather_df)
            
            # Validate inputs
            is_valid, errors = self.converter.validate_afc_inputs(afc_inputs)
            
            if not is_valid:
                print(f"⚠️  AFC input validation failed: {errors}")
                return None
            
            # Simulate AFC optimization results
            current_data = afc_inputs.iloc[0]
            
            # Simple rule-based simulation
            dni = current_data.get('dni', 0)
            if dni > 400:
                facade_state = 1.0  # Partially tinted
            elif dni > 200:
                facade_state = 2.0  # Moderately tinted
            else:
                facade_state = 3.0  # Clear
            
            # Simulate HVAC
            temp = current_data.get('temp_air', 22)
            cooling_setpoint = min(26, temp + 2)
            heating_setpoint = max(18, temp - 2)
            
            simulated_results = {
                'facade_setpoints': [
                    {
                        'zone_id': 'zone_0',
                        'device_type': 'electrochromic_window', 
                        'setpoint': facade_state,
                        'timestamp': datetime.now().isoformat()
                    }
                ],
                'hvac_setpoints': {
                    'cooling_setpoint': cooling_setpoint,
                    'heating_setpoint': heating_setpoint,
                    'mode': 'auto'
                },
                'optimization_data': {
                    'objective_value': 10.5 + np.random.normal(0, 1),
                    'energy_cost': 8.2 + np.random.normal(0, 0.5),
                    'comfort_score': 0.8 + np.random.normal(0, 0.1),
                    'valid': True
                }
            }
            
            # Convert to OFC commands
            ofc_commands = self.converter.afc_outputs_to_ofc_commands(simulated_results)
            
            return {
                'afc_inputs': afc_inputs,
                'afc_results': simulated_results,
                'ofc_commands': ofc_commands
            }
            
        except Exception as e:
            print(f"Error in AFC simulation: {e}")
            return None

    def get_status(self):
        """Get agent status"""
        return {
            'converter_available': self.converter is not None,
            'control_cycles': self.control_ct,
            'version': '0.1'
        }


def test_afc_agent():
    """Test the AFC agent functionality"""
    print("=== Testing AFC Agent Functionality ===\n")
    
    # Create mock agent
    agent = MockAFCAgent()
    
    print("1. Testing agent initialization...")
    status = agent.get_status()
    print(f"✓ Agent initialized - Converter: {status['converter_available']}")
    
    print("\n2. Testing sensor data processing...")
    
    # Simulate various sensor conditions
    test_scenarios = [
        {
            'name': 'High solar radiation',
            'data': {
                'glare_sensor_1': 250,
                'occupancy_sensor_1': 1,
                'illuminance_sensor_1': 800,
                'temp_sensor_1': 25.0
            }
        },
        {
            'name': 'Low light conditions', 
            'data': {
                'glare_sensor_1': 50,
                'occupancy_sensor_1': 1,
                'illuminance_sensor_1': 200,
                'temp_sensor_1': 20.0
            }
        },
        {
            'name': 'Unoccupied space',
            'data': {
                'glare_sensor_1': 150,
                'occupancy_sensor_1': 0,
                'illuminance_sensor_1': 300,
                'temp_sensor_1': 22.0
            }
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n  Testing scenario: {scenario['name']}")
        
        result = agent.simulate_afc_optimization(scenario['data'])
        
        if result:
            afc_inputs = result['afc_inputs']
            ofc_commands = result['ofc_commands']
            
            print(f"    ✓ AFC inputs: {afc_inputs.shape[0]} timesteps")
            print(f"    ✓ OFC commands: {len(ofc_commands)} devices")
            
            # Show key results
            for cmd in ofc_commands:
                if 'facade' in cmd['device_type']:
                    print(f"      Facade {cmd['zone']}: {cmd['value']}")
                elif 'hvac' in cmd['device_type']:
                    print(f"      HVAC {cmd['point']}: {cmd['value']}°C")
        else:
            print(f"    ✗ Scenario failed")
            return False
    
    print("\n3. Testing agent status...")
    final_status = agent.get_status()
    print(f"✓ Control cycles completed: {final_status['control_cycles']}")
    
    print("\n=== All AFC Agent Tests Passed ===")
    print(f"Successfully completed {final_status['control_cycles']} control cycles")
    return True


if __name__ == "__main__":
    success = test_afc_agent()
    exit(0 if success else 1)