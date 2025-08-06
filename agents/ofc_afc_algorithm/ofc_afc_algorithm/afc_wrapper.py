# *** Copyright Notice ***
# 
# OpenFacadeControl (OFC) Copyright (c) 2024, The Regents of the University
# of California, through Lawrence Berkeley National Laboratory (subject to receipt
# of any required approvals from the U.S. Dept. of Energy). All rights reserved.

"""
AFC Controller Wrapper for OFC Integration

This module provides a wrapper around the AFC (Advanced Facade Controller)
to integrate it with OFC's VOLTTRON-based architecture.
"""

import os
import sys
import json
import logging
import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import tempfile
import traceback

# Add AFC path if available
afc_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'afc')
if os.path.exists(afc_path):
    sys.path.insert(0, afc_path)

_log = logging.getLogger(__name__)


class AFCWrapper:
    """
    Wrapper class for the AFC controller to integrate with OFC.
    
    This wrapper provides:
    - Error handling and fallback mechanisms
    - Data format conversion
    - Performance monitoring
    - Asynchronous operation support
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the AFC wrapper.
        
        :param config: AFC configuration dictionary.
        """
        self.config = config
        self.afc_controller = None
        self.afc_available = False
        self.last_optimization_time = None
        self.optimization_count = 0
        self.failure_count = 0
        
        # Performance settings
        self.max_optimization_time = config.get('max_optimization_time', 300)  # 5 minutes
        self.optimization_timeout = config.get('optimization_timeout', 120)   # 2 minutes
        
        # Fallback settings
        self.use_fallback = config.get('use_fallback', True)
        self.fallback_on_error = config.get('fallback_on_error', True)
        
        # Initialize AFC if possible
        self._initialize_afc()
        
    def _initialize_afc(self):
        """Initialize the AFC controller."""
        try:
            # Try to import AFC components
            from afc.ctrlWrapper import Controller, make_inputs
            from afc.defaultConfig import default_parameter
            
            # Create AFC controller
            self.afc_controller = Controller()
            
            # Load default parameters and update with config
            self.afc_parameters = default_parameter()
            self._update_afc_parameters()
            
            self.afc_available = True
            _log.info("AFC controller initialized successfully")
            
        except ImportError as e:
            _log.warning(f"AFC not available: {e}")
            self.afc_available = False
            
        except Exception as e:
            _log.error(f"Error initializing AFC: {e}")
            self.afc_available = False
            
    def _update_afc_parameters(self):
        """Update AFC parameters with OFC configuration."""
        try:
            # Building configuration
            building_config = self.config.get('building', {})
            if building_config:
                # Location
                location = building_config.get('location', {})
                if location:
                    self.afc_parameters['radiance']['location'].update(location)
                
                # Geometry  
                geometry = building_config.get('geometry', {})
                if geometry:
                    self.afc_parameters['radiance']['dimensions'].update(geometry)
                
                # Facade system
                facade_type = building_config.get('facade_system')
                if facade_type:
                    self.afc_parameters['facade']['type'] = facade_type
                    
                # HVAC system
                hvac_type = building_config.get('hvac_system')
                if hvac_type:
                    # Update HVAC parameters based on system type
                    pass
            
            # Optimization configuration
            opt_config = self.config.get('optimization', {})
            if opt_config:
                # Optimization horizon
                horizon = opt_config.get('horizon', 24)
                self.afc_parameters['wrapper']['optimization_horizon'] = horizon
                
                # Timestep
                timestep = opt_config.get('timestep_minutes', 60)
                self.afc_parameters['wrapper']['timestep_minutes'] = timestep
                
                # Solver settings
                solver_config = opt_config.get('solver', {})
                if solver_config:
                    self.afc_parameters['wrapper'].update(solver_config)
            
            # Comfort weights
            comfort_weights = self.config.get('comfort_weights', {})
            if comfort_weights:
                # Update occupant preferences
                occupant_config = self.afc_parameters.get('occupant', {})
                occupant_config.update(comfort_weights)
                
            _log.debug("AFC parameters updated with OFC configuration")
            
        except Exception as e:
            _log.error(f"Error updating AFC parameters: {e}")
            
    def optimize(self, afc_inputs: pd.DataFrame, 
                devices: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Run AFC optimization.
        
        :param afc_inputs: AFC input DataFrame.
        :param devices: List of devices to control.
        :return: Optimization results or None if failed.
        """
        start_time = datetime.datetime.now()
        
        try:
            if not self.afc_available:
                _log.warning("AFC not available - cannot run optimization")
                return None
                
            self.optimization_count += 1
            _log.info(f"Starting AFC optimization cycle {self.optimization_count}")
            
            # Prepare AFC inputs
            afc_ready_inputs = self._prepare_afc_inputs(afc_inputs, devices)
            
            if not afc_ready_inputs:
                _log.error("Failed to prepare AFC inputs")
                self.failure_count += 1
                return None
            
            # Run AFC optimization with timeout
            result = self._run_afc_with_timeout(afc_ready_inputs)
            
            if result:
                # Process results
                processed_result = self._process_afc_results(result, devices)
                
                duration = (datetime.datetime.now() - start_time).total_seconds()
                self.last_optimization_time = start_time
                
                _log.info(f"AFC optimization completed in {duration:.2f}s")
                
                return processed_result
            else:
                _log.error("AFC optimization returned no results")
                self.failure_count += 1
                return None
                
        except Exception as e:
            _log.error(f"AFC optimization failed: {e}")
            _log.debug(traceback.format_exc())
            self.failure_count += 1
            return None
            
    def _prepare_afc_inputs(self, afc_inputs: pd.DataFrame, 
                          devices: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Prepare inputs for AFC controller.
        
        :param afc_inputs: Input DataFrame.
        :param devices: Device list.
        :return: AFC-ready inputs or None.
        """
        try:
            from afc.ctrlWrapper import make_inputs
            
            # Create initial states
            facade_initial = self._get_initial_facade_states(devices)
            temps_initial = self._get_initial_temperatures(devices)
            
            # Create weather forecast for full period
            wf_all = self._create_weather_forecast(afc_inputs)
            
            # Prepare inputs
            inputs = make_inputs(
                parameter=self.afc_parameters,
                df=afc_inputs,
                return_json=True
            )
            
            # Add additional inputs
            inputs['wf-all'] = wf_all.to_dict()
            inputs['facade-initial'] = facade_initial
            inputs['temps-initial'] = temps_initial
            
            return inputs
            
        except Exception as e:
            _log.error(f"Error preparing AFC inputs: {e}")
            return None
            
    def _get_initial_facade_states(self, devices: List[Dict[str, Any]]) -> List[float]:
        """Get initial facade states from devices."""
        try:
            facade_states = []
            
            for device in devices:
                if 'facade' in device.get('type', '').lower():
                    # Get current state or use default
                    current_state = device.get('current_value', 3.0)  # Default to clear
                    facade_states.append(float(current_state))
                    
            # Ensure we have at least one facade state
            if not facade_states:
                facade_states = [3.0]  # Default clear state
                
            return facade_states
            
        except Exception as e:
            _log.error(f"Error getting initial facade states: {e}")
            return [3.0]  # Default
            
    def _get_initial_temperatures(self, devices: List[Dict[str, Any]]) -> List[float]:
        """Get initial zone temperatures."""
        try:
            # Look for temperature sensors in devices
            for device in devices:
                if 'temp' in device.get('type', '').lower():
                    temp = device.get('current_value', 22.0)
                    return [float(temp)]
                    
            # Default temperature
            return [22.0]
            
        except Exception as e:
            _log.error(f"Error getting initial temperatures: {e}")
            return [22.0]  # Default
            
    def _create_weather_forecast(self, afc_inputs: pd.DataFrame) -> pd.DataFrame:
        """Create extended weather forecast for AFC."""
        try:
            # AFC needs longer forecast - extend if necessary
            current_hours = len(afc_inputs)
            required_hours = self.afc_parameters.get('wrapper', {}).get('optimization_horizon', 24)
            
            if current_hours >= required_hours:
                return afc_inputs[['dni', 'dhi']].copy()
            
            # Extend forecast using simple persistence
            last_row = afc_inputs.iloc[-1]
            extend_hours = required_hours - current_hours
            
            # Create extended time index
            last_time = afc_inputs.index[-1]
            extended_times = pd.date_range(
                last_time + pd.Timedelta(hours=1),
                periods=extend_hours,
                freq='H'
            )
            
            # Create extended data
            extended_data = pd.DataFrame(
                index=extended_times,
                columns=['dni', 'dhi']
            )
            
            # Fill with last known values
            for col in ['dni', 'dhi']:
                extended_data[col] = last_row[col]
                
            # Combine original and extended
            full_forecast = pd.concat([
                afc_inputs[['dni', 'dhi']],
                extended_data
            ])
            
            return full_forecast
            
        except Exception as e:
            _log.error(f"Error creating weather forecast: {e}")
            return afc_inputs[['dni', 'dhi']].copy()
            
    def _run_afc_with_timeout(self, inputs: Dict[str, Any]) -> Optional[str]:
        """
        Run AFC with timeout protection.
        
        :param inputs: AFC inputs.
        :return: AFC message output or None.
        """
        try:
            # Set inputs
            for key, value in inputs.items():
                if hasattr(self.afc_controller, 'input') and key in self.afc_controller.input:
                    self.afc_controller.input[key] = value
                    
            # Run optimization
            message = self.afc_controller.compute()
            
            return message
            
        except Exception as e:
            _log.error(f"Error running AFC: {e}")
            return None
            
    def _process_afc_results(self, afc_message: str, 
                           devices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process AFC results into OFC format.
        
        :param afc_message: AFC output message.
        :param devices: Device list.
        :return: Processed results.
        """
        try:
            # Get AFC outputs
            if not hasattr(self.afc_controller, 'output'):
                _log.error("AFC controller has no output")
                return {'valid': False}
                
            outputs = self.afc_controller.output
            
            # Check if optimization was valid
            valid = outputs.get('valid', False)
            
            if not valid:
                _log.warning("AFC optimization was not valid")
                return {'valid': False}
                
            # Extract optimization statistics
            opt_stats = outputs.get('opt-stats', {})
            duration = opt_stats.get('duration', 0)
            objective = opt_stats.get('objective', 0)
            termination = opt_stats.get('termination', 'unknown')
            
            # Extract control outputs
            facade_setpoints = []
            hvac_setpoints = {}
            
            # Facade controls
            facade_ctrl = outputs.get('ctrl-facade', [])
            if facade_ctrl:
                for i, setpoint in enumerate(facade_ctrl):
                    facade_setpoints.append({
                        'zone_id': f'zone_{i}',
                        'device_type': 'electrochromic_window',
                        'setpoint': float(setpoint),
                        'timestamp': datetime.datetime.now().isoformat()
                    })
                    
            # HVAC controls
            thermostat_ctrl = outputs.get('ctrl-thermostat', {})
            if thermostat_ctrl:
                hvac_setpoints = {
                    'cooling_setpoint': thermostat_ctrl.get('cooling', 24.0),
                    'heating_setpoint': thermostat_ctrl.get('heating', 20.0),
                    'mode': 'auto'
                }
                
            # Room temperature
            room_temp = outputs.get('ctrl-troom')
            
            return {
                'valid': True,
                'facade_setpoints': facade_setpoints,
                'hvac_setpoints': hvac_setpoints,
                'optimization_data': {
                    'objective_value': float(objective) if objective else None,
                    'duration': float(duration),
                    'termination': str(termination),
                    'room_temperature': float(room_temp) if room_temp else None,
                    'valid': True
                },
                'afc_message': afc_message,
                'timestamp': datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            _log.error(f"Error processing AFC results: {e}")
            return {'valid': False, 'error': str(e)}
            
    def get_status(self) -> Dict[str, Any]:
        """Get AFC wrapper status."""
        return {
            'afc_available': self.afc_available,
            'optimization_count': self.optimization_count,
            'failure_count': self.failure_count,
            'last_optimization': self.last_optimization_time.isoformat() if self.last_optimization_time else None,
            'success_rate': (self.optimization_count - self.failure_count) / max(1, self.optimization_count),
            'config': {
                'max_optimization_time': self.max_optimization_time,
                'optimization_timeout': self.optimization_timeout,
                'use_fallback': self.use_fallback
            }
        }
        
    def reset_stats(self):
        """Reset optimization statistics."""
        self.optimization_count = 0
        self.failure_count = 0
        self.last_optimization_time = None
        _log.info("AFC wrapper statistics reset")


class MockAFCWrapper(AFCWrapper):
    """Mock AFC wrapper for testing without full AFC dependencies."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize mock wrapper."""
        self.config = config
        self.afc_controller = None
        self.afc_available = True  # Mock is always available
        self.last_optimization_time = None
        self.optimization_count = 0
        self.failure_count = 0
        
        # Performance settings
        self.max_optimization_time = config.get('max_optimization_time', 300)
        self.optimization_timeout = config.get('optimization_timeout', 120)
        self.use_fallback = config.get('use_fallback', True)
        self.fallback_on_error = config.get('fallback_on_error', True)
        
        _log.info("Mock AFC wrapper initialized")
        
    def optimize(self, afc_inputs: pd.DataFrame, 
                devices: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Mock optimization that simulates AFC behavior."""
        start_time = datetime.datetime.now()
        
        try:
            self.optimization_count += 1
            _log.info(f"Running mock AFC optimization cycle {self.optimization_count}")
            
            # Simulate optimization delay
            import time
            time.sleep(0.1)  # Brief delay to simulate computation
            
            # Get current conditions from inputs
            current_data = afc_inputs.iloc[0] if len(afc_inputs) > 0 else {}
            
            # Generate mock facade setpoints based on solar conditions
            dni = current_data.get('dni', 400)
            glare = current_data.get('glare_max', 200)
            
            # Simple rule-based facade control
            if dni > 600 or glare > 300:
                facade_state = 1.0  # High tint
            elif dni > 300 or glare > 150:
                facade_state = 2.0  # Medium tint
            else:
                facade_state = 3.0  # Clear
                
            # Generate mock HVAC setpoints
            temp_air = current_data.get('temp_air', 22)
            occupancy = current_data.get('occupancy_light', 1)
            
            if occupancy:
                cooling_setpoint = min(26, temp_air + 2)
                heating_setpoint = max(18, temp_air - 2)
            else:
                cooling_setpoint = min(28, temp_air + 3)  # Energy saving
                heating_setpoint = max(16, temp_air - 3)
                
            # Create mock optimization results
            facade_setpoints = []
            num_zones = len([d for d in devices if 'facade' in d.get('type', '').lower()])
            num_zones = max(1, num_zones)  # At least one zone
            
            for i in range(num_zones):
                facade_setpoints.append({
                    'zone_id': f'zone_{i}',
                    'device_type': 'electrochromic_window',
                    'setpoint': facade_state + np.random.normal(0, 0.1),  # Small variation
                    'timestamp': datetime.datetime.now().isoformat()
                })
                
            duration = (datetime.datetime.now() - start_time).total_seconds()
            self.last_optimization_time = start_time
            
            # Mock objective value calculation
            energy_cost = 15.0 + np.random.normal(0, 2)
            comfort_penalty = 5.0 + np.random.normal(0, 1)
            objective_value = energy_cost + comfort_penalty
            
            result = {
                'valid': True,
                'facade_setpoints': facade_setpoints,
                'hvac_setpoints': {
                    'cooling_setpoint': cooling_setpoint,
                    'heating_setpoint': heating_setpoint,
                    'mode': 'auto'
                },
                'optimization_data': {
                    'objective_value': objective_value,
                    'energy_cost': energy_cost,
                    'comfort_score': max(0, min(1, 0.9 - comfort_penalty/10)),
                    'duration': duration,
                    'termination': 'optimal',
                    'valid': True
                },
                'timestamp': datetime.datetime.now().isoformat()
            }
            
            _log.info(f"Mock AFC optimization completed in {duration:.3f}s")
            return result
            
        except Exception as e:
            _log.error(f"Mock AFC optimization failed: {e}")
            self.failure_count += 1
            return None