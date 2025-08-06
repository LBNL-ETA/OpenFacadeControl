# *** Copyright Notice ***
# 
# OpenFacadeControl (OFC) Copyright (c) 2024, The Regents of the University
# of California, through Lawrence Berkeley National Laboratory (subject to receipt
# of any required approvals from the U.S. Dept. of Energy). All rights reserved.

"""
Enhanced Data Converter for AFC-OFC Integration

This module provides advanced data conversion capabilities between OFC and AFC formats,
building on the basic converter with additional features for production use.
"""

import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import copy

# Import base converter
import sys
import os
project_root = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
sys.path.insert(0, project_root)

try:
    from ofc_afc_converter import OFCAFCConverter
except ImportError:
    OFCAFCConverter = None

_log = logging.getLogger(__name__)


class DataConverter:
    """
    Enhanced data converter for AFC-OFC integration.
    
    Provides advanced features beyond the basic converter:
    - Device-specific conversions
    - Historical data integration
    - Performance optimization
    - Error recovery
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the data converter.
        
        :param config: Converter configuration.
        """
        self.config = config or {}
        
        # Initialize base converter if available
        if OFCAFCConverter:
            self.base_converter = OFCAFCConverter()
        else:
            self.base_converter = None
            _log.warning("Base converter not available")
            
        # Configuration
        self.device_mappings = self.config.get('device_mappings', self._get_default_device_mappings())
        self.sensor_mappings = self.config.get('sensor_mappings', self._get_default_sensor_mappings())
        self.validation_enabled = self.config.get('validation_enabled', True)
        
        # Performance settings
        self.cache_enabled = self.config.get('cache_enabled', True)
        self.cache_duration = self.config.get('cache_duration', 300)  # 5 minutes
        self.conversion_cache = {}
        
        _log.info("Enhanced data converter initialized")
        
    def _get_default_device_mappings(self) -> Dict[str, Dict[str, str]]:
        """Get default device type mappings."""
        return {
            'ofc_to_afc': {
                'cree_light': 'dimmable_light',
                'hunter_douglas_shade': 'automated_blind',
                'electrochromic_window': 'electrochromic_window',
                'lutron_light': 'dimmable_light',
                'enlighted_sensor': 'occupancy_sensor',
                'hvac_cooling': 'hvac_cooling',
                'hvac_heating': 'hvac_heating'
            },
            'afc_to_ofc': {
                'dimmable_light': 'cree_light',
                'automated_blind': 'hunter_douglas_shade',
                'electrochromic_window': 'electrochromic_window',
                'occupancy_sensor': 'enlighted_sensor',
                'hvac_cooling': 'hvac_cooling',
                'hvac_heating': 'hvac_heating'
            }
        }
        
    def _get_default_sensor_mappings(self) -> Dict[str, str]:
        """Get default sensor mappings."""
        return {
            'glare_sensor': 'glare_max',
            'occupancy_sensor': 'occupancy_light',
            'illuminance_sensor': 'wpi_min',
            'temp_sensor': 'temp_room',
            'light_level': 'lighting_level',
            'shade_position': 'shade_position',
            'window_state': 'window_state'
        }
        
    def ofc_sensors_to_afc_inputs(self, ofc_sensor_data: Dict[str, Any], 
                                 weather_data: pd.DataFrame,
                                 building_config: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Enhanced OFC sensor data to AFC input conversion.
        
        :param ofc_sensor_data: OFC sensor readings.
        :param weather_data: Weather forecast data.
        :param building_config: Optional building configuration.
        :return: AFC-compatible input DataFrame.
        """
        try:
            # Use base converter if available
            if self.base_converter:
                afc_inputs = self.base_converter.ofc_sensors_to_afc_inputs(
                    ofc_sensor_data, weather_data
                )
            else:
                afc_inputs = self._fallback_sensor_conversion(ofc_sensor_data, weather_data)
                
            # Apply enhancements
            afc_inputs = self._enhance_afc_inputs(afc_inputs, ofc_sensor_data, building_config)
            
            # Validate if enabled
            if self.validation_enabled:
                afc_inputs = self._validate_and_clean_inputs(afc_inputs)
                
            return afc_inputs
            
        except Exception as e:
            _log.error(f"Error converting OFC sensors to AFC inputs: {e}")
            raise
            
    def afc_outputs_to_ofc_commands(self, afc_outputs: Dict[str, Any],
                                   device_context: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Enhanced AFC output to OFC command conversion.
        
        :param afc_outputs: AFC optimization results.
        :param device_context: Optional device context for enhanced mapping.
        :return: List of OFC device commands.
        """
        try:
            # Use base converter if available
            if self.base_converter:
                ofc_commands = self.base_converter.afc_outputs_to_ofc_commands(afc_outputs)
            else:
                ofc_commands = self._fallback_output_conversion(afc_outputs)
                
            # Apply enhancements
            ofc_commands = self._enhance_ofc_commands(ofc_commands, device_context)
            
            # Add command metadata
            ofc_commands = self._add_command_metadata(ofc_commands, afc_outputs)
            
            return ofc_commands
            
        except Exception as e:
            _log.error(f"Error converting AFC outputs to OFC commands: {e}")
            raise
            
    def _fallback_sensor_conversion(self, sensor_data: Dict[str, Any], 
                                  weather_data: pd.DataFrame) -> pd.DataFrame:
        """Fallback sensor conversion when base converter unavailable."""
        try:
            # Start with weather data
            afc_inputs = weather_data.copy()
            
            # Add sensor-derived parameters
            sensor_defaults = {
                'plug_load': 100,
                'occupant_load': 100,
                'equipment': 50,
                'occupancy_light': 1,
                'wpi_min': 300,
                'glare_max': 2000,
                'temp_room_max': 26,
                'temp_room_min': 20,
                'generation_pv': 0,
                'load_demand': 0,
                'temp_slab_max': 1000,
                'temp_slab_min': 0,
                'temp_wall_max': 1000,
                'temp_wall_min': 0,
                'grid_co2_intensity': 0
            }
            
            # Apply defaults
            for key, value in sensor_defaults.items():
                if key not in afc_inputs.columns:
                    afc_inputs[key] = value
                    
            # Map sensor data
            for sensor_key, sensor_value in sensor_data.items():
                afc_key = self._map_sensor_key(sensor_key)
                if afc_key:
                    if afc_key in ['temp_room_max', 'temp_room_min']:
                        # Set comfort range around temperature
                        temp = float(sensor_value)
                        afc_inputs['temp_room_max'] = temp + 2
                        afc_inputs['temp_room_min'] = temp - 2
                    else:
                        afc_inputs[afc_key] = sensor_value
                        
            return afc_inputs
            
        except Exception as e:
            _log.error(f"Fallback sensor conversion failed: {e}")
            raise
            
    def _fallback_output_conversion(self, afc_outputs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fallback output conversion when base converter unavailable."""
        try:
            ofc_commands = []
            timestamp = datetime.now().isoformat()
            
            # Process facade setpoints
            if 'facade_setpoints' in afc_outputs:
                for setpoint in afc_outputs['facade_setpoints']:
                    zone_id = setpoint.get('zone_id', 'zone_0')
                    device_type = setpoint.get('device_type', 'electrochromic_window')
                    value = setpoint.get('setpoint', 0)
                    
                    ofc_device_type = self.device_mappings['afc_to_ofc'].get(device_type, device_type)
                    
                    ofc_commands.append({
                        'device_id': f"ofc_{zone_id}_{ofc_device_type}",
                        'device_type': ofc_device_type,
                        'point': 'setpoint',
                        'value': float(value),
                        'timestamp': timestamp,
                        'zone': zone_id
                    })
                    
            # Process HVAC setpoints
            if 'hvac_setpoints' in afc_outputs:
                hvac = afc_outputs['hvac_setpoints']
                
                for point, value in hvac.items():
                    if point in ['cooling_setpoint', 'heating_setpoint']:
                        device_type = point.replace('_setpoint', '')
                        
                        ofc_commands.append({
                            'device_id': f"ofc_hvac_{device_type}",
                            'device_type': f"hvac_{device_type}",
                            'point': point,
                            'value': float(value),
                            'timestamp': timestamp,
                            'zone': 'building'
                        })
                        
            return ofc_commands
            
        except Exception as e:
            _log.error(f"Fallback output conversion failed: {e}")
            raise
            
    def _enhance_afc_inputs(self, afc_inputs: pd.DataFrame, 
                          sensor_data: Dict[str, Any],
                          building_config: Optional[Dict[str, Any]]) -> pd.DataFrame:
        """Enhance AFC inputs with additional processing."""
        try:
            enhanced = afc_inputs.copy()
            
            # Add historical context if available
            enhanced = self._add_historical_context(enhanced, sensor_data)
            
            # Apply building-specific adjustments
            if building_config:
                enhanced = self._apply_building_adjustments(enhanced, building_config)
                
            # Add derived parameters
            enhanced = self._add_derived_parameters(enhanced, sensor_data)
            
            return enhanced
            
        except Exception as e:
            _log.error(f"Error enhancing AFC inputs: {e}")
            return afc_inputs
            
    def _enhance_ofc_commands(self, ofc_commands: List[Dict[str, Any]],
                            device_context: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Enhance OFC commands with additional metadata."""
        try:
            enhanced_commands = []
            
            for cmd in ofc_commands:
                enhanced_cmd = cmd.copy()
                
                # Add device-specific enhancements
                device_type = cmd.get('device_type', '')
                
                if 'facade' in device_type or 'window' in device_type:
                    enhanced_cmd = self._enhance_facade_command(enhanced_cmd, device_context)
                elif 'light' in device_type:
                    enhanced_cmd = self._enhance_lighting_command(enhanced_cmd, device_context)
                elif 'hvac' in device_type:
                    enhanced_cmd = self._enhance_hvac_command(enhanced_cmd, device_context)
                    
                # Add priority and timing information
                enhanced_cmd['priority'] = self._calculate_command_priority(enhanced_cmd)
                enhanced_cmd['execution_delay'] = self._calculate_execution_delay(enhanced_cmd)
                
                enhanced_commands.append(enhanced_cmd)
                
            return enhanced_commands
            
        except Exception as e:
            _log.error(f"Error enhancing OFC commands: {e}")
            return ofc_commands
            
    def _enhance_facade_command(self, cmd: Dict[str, Any], 
                              device_context: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Enhance facade control commands."""
        try:
            enhanced = cmd.copy()
            
            # Add ramp rate for smooth transitions
            enhanced['ramp_rate'] = 0.1  # 10% per second
            
            # Add bounds checking
            if 'electrochromic' in cmd.get('device_type', ''):
                enhanced['value'] = max(0.0, min(3.0, enhanced['value']))
            elif 'shade' in cmd.get('device_type', ''):
                enhanced['value'] = max(0.0, min(1.0, enhanced['value']))
                
            # Add confirmation requirement for large changes
            if device_context:
                for device in device_context:
                    if device.get('device_id') == cmd.get('device_id'):
                        current_value = device.get('current_value', enhanced['value'])
                        change_magnitude = abs(enhanced['value'] - current_value)
                        
                        if change_magnitude > 1.0:  # Large change
                            enhanced['require_confirmation'] = True
                            
            return enhanced
            
        except Exception as e:
            _log.error(f"Error enhancing facade command: {e}")
            return cmd
            
    def _enhance_lighting_command(self, cmd: Dict[str, Any],
                                device_context: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Enhance lighting control commands."""
        try:
            enhanced = cmd.copy()
            
            # Add dimming rate
            enhanced['dimming_rate'] = 0.05  # 5% per second
            
            # Bounds checking
            enhanced['value'] = max(0.0, min(1.0, enhanced['value']))
            
            # Add energy saving mode flag
            if enhanced['value'] < 0.3:
                enhanced['energy_saving_mode'] = True
                
            return enhanced
            
        except Exception as e:
            _log.error(f"Error enhancing lighting command: {e}")
            return cmd
            
    def _enhance_hvac_command(self, cmd: Dict[str, Any],
                            device_context: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Enhance HVAC control commands."""
        try:
            enhanced = cmd.copy()
            
            # Add temperature bounds
            if 'cooling' in cmd.get('point', ''):
                enhanced['value'] = max(18, min(30, enhanced['value']))
            elif 'heating' in cmd.get('point', ''):
                enhanced['value'] = max(10, min(28, enhanced['value']))
                
            # Add deadband information
            enhanced['deadband'] = 1.0  # 1°C deadband
            
            return enhanced
            
        except Exception as e:
            _log.error(f"Error enhancing HVAC command: {e}")
            return cmd
            
    def _add_command_metadata(self, commands: List[Dict[str, Any]], 
                            afc_outputs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Add metadata to commands."""
        try:
            enhanced_commands = []
            
            # Get optimization data
            opt_data = afc_outputs.get('optimization_data', {})
            
            for cmd in commands:
                enhanced = cmd.copy()
                
                # Add optimization metadata
                enhanced['optimization_id'] = f"opt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                enhanced['objective_value'] = opt_data.get('objective_value')
                enhanced['optimization_valid'] = opt_data.get('valid', False)
                enhanced['energy_impact'] = self._estimate_energy_impact(enhanced)
                enhanced['comfort_impact'] = self._estimate_comfort_impact(enhanced)
                
                enhanced_commands.append(enhanced)
                
            return enhanced_commands
            
        except Exception as e:
            _log.error(f"Error adding command metadata: {e}")
            return commands
            
    def _add_historical_context(self, afc_inputs: pd.DataFrame, 
                              sensor_data: Dict[str, Any]) -> pd.DataFrame:
        """Add historical context to inputs."""
        # Placeholder for historical data integration
        return afc_inputs
        
    def _apply_building_adjustments(self, afc_inputs: pd.DataFrame,
                                  building_config: Dict[str, Any]) -> pd.DataFrame:
        """Apply building-specific adjustments."""
        try:
            adjusted = afc_inputs.copy()
            
            # Adjust comfort ranges based on building type
            building_type = building_config.get('type', 'office')
            
            if building_type == 'residential':
                # Tighter comfort ranges for residential
                if 'temp_room_max' in adjusted.columns:
                    adjusted['temp_room_max'] = adjusted['temp_room_max'] - 1
                if 'temp_room_min' in adjusted.columns:
                    adjusted['temp_room_min'] = adjusted['temp_room_min'] + 1
                    
            elif building_type == 'laboratory':
                # Stricter illuminance requirements
                if 'wpi_min' in adjusted.columns:
                    adjusted['wpi_min'] = adjusted['wpi_min'] * 1.2
                    
            return adjusted
            
        except Exception as e:
            _log.error(f"Error applying building adjustments: {e}")
            return afc_inputs
            
    def _add_derived_parameters(self, afc_inputs: pd.DataFrame, 
                              sensor_data: Dict[str, Any]) -> pd.DataFrame:
        """Add derived parameters to inputs."""
        try:
            enhanced = afc_inputs.copy()
            
            # Calculate solar heat gain
            if 'dni' in enhanced.columns and 'dhi' in enhanced.columns:
                enhanced['solar_heat_gain'] = enhanced['dni'] * 0.3 + enhanced['dhi'] * 0.1
                
            # Calculate cooling load estimate
            if all(col in enhanced.columns for col in ['temp_air', 'solar_heat_gain']):
                enhanced['cooling_load_estimate'] = (
                    np.maximum(0, enhanced['temp_air'] - 20) * 100 +
                    enhanced['solar_heat_gain'] * 0.5
                )
                
            return enhanced
            
        except Exception as e:
            _log.error(f"Error adding derived parameters: {e}")
            return afc_inputs
            
    def _validate_and_clean_inputs(self, afc_inputs: pd.DataFrame) -> pd.DataFrame:
        """Validate and clean AFC inputs."""
        try:
            cleaned = afc_inputs.copy()
            
            # Define validation ranges
            ranges = {
                'dni': (0, 1200),
                'dhi': (0, 500), 
                'temp_air': (-40, 60),
                'wind_speed': (0, 50),
                'occupancy_light': (0, 1),
                'wpi_min': (0, 2000),
                'glare_max': (0, 5000),
                'temp_room_max': (15, 35),
                'temp_room_min': (10, 30)
            }
            
            # Apply validation
            for col, (min_val, max_val) in ranges.items():
                if col in cleaned.columns:
                    cleaned[col] = cleaned[col].clip(min_val, max_val)
                    
            # Interpolate missing values
            cleaned = cleaned.interpolate()
            
            # Fill remaining NaN values
            defaults = {
                'dni': 400, 'dhi': 100, 'temp_air': 20, 'wind_speed': 2,
                'occupancy_light': 1, 'wpi_min': 300, 'glare_max': 2000,
                'temp_room_max': 26, 'temp_room_min': 20
            }
            
            for col, default in defaults.items():
                if col in cleaned.columns:
                    cleaned[col] = cleaned[col].fillna(default)
                    
            return cleaned
            
        except Exception as e:
            _log.error(f"Error validating inputs: {e}")
            return afc_inputs
            
    def _map_sensor_key(self, sensor_key: str) -> Optional[str]:
        """Map sensor key to AFC parameter."""
        for ofc_key, afc_key in self.sensor_mappings.items():
            if ofc_key.lower() in sensor_key.lower():
                return afc_key
        return None
        
    def _calculate_command_priority(self, cmd: Dict[str, Any]) -> int:
        """Calculate command execution priority."""
        device_type = cmd.get('device_type', '')
        
        # HVAC has highest priority
        if 'hvac' in device_type:
            return 1
        # Lighting second
        elif 'light' in device_type:
            return 2
        # Facade third
        else:
            return 3
            
    def _calculate_execution_delay(self, cmd: Dict[str, Any]) -> float:
        """Calculate command execution delay."""
        # Simple delay based on device type
        device_type = cmd.get('device_type', '')
        
        if 'hvac' in device_type:
            return 0.0  # Immediate
        elif 'light' in device_type:
            return 1.0  # 1 second
        else:
            return 2.0  # 2 seconds
            
    def _estimate_energy_impact(self, cmd: Dict[str, Any]) -> str:
        """Estimate energy impact of command."""
        device_type = cmd.get('device_type', '')
        value = cmd.get('value', 0)
        
        if 'hvac' in device_type:
            return 'high'
        elif 'light' in device_type and value > 0.7:
            return 'medium'
        else:
            return 'low'
            
    def _estimate_comfort_impact(self, cmd: Dict[str, Any]) -> str:
        """Estimate comfort impact of command."""
        device_type = cmd.get('device_type', '')
        
        if 'hvac' in device_type:
            return 'high'
        elif 'facade' in device_type or 'window' in device_type:
            return 'medium'
        else:
            return 'low'
            
    def validate_afc_inputs(self, afc_inputs: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Validate AFC input data."""
        if self.base_converter:
            return self.base_converter.validate_afc_inputs(afc_inputs)
        else:
            # Simple fallback validation
            errors = []
            required_cols = ['dni', 'dhi', 'temp_air', 'wind_speed']
            
            for col in required_cols:
                if col not in afc_inputs.columns:
                    errors.append(f"Missing required column: {col}")
                    
            return len(errors) == 0, errors
            
    def get_status(self) -> Dict[str, Any]:
        """Get converter status."""
        return {
            'base_converter_available': self.base_converter is not None,
            'validation_enabled': self.validation_enabled,
            'cache_enabled': self.cache_enabled,
            'cached_conversions': len(self.conversion_cache),
            'device_mappings_count': len(self.device_mappings.get('ofc_to_afc', {})),
            'sensor_mappings_count': len(self.sensor_mappings)
        }