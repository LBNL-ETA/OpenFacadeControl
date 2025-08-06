# *** Copyright Notice ***
# 
# OpenFacadeControl (OFC) Copyright (c) 2024, The Regents of the University
# of California, through Lawrence Berkeley National Laboratory (subject to receipt
# of any required approvals from the U.S. Dept. of Energy). All rights reserved.
# 
# If you have questions about your rights to use or distribute this software,
# please contact Berkeley Lab's Intellectual Property Office at
# IPO@lbl.gov.
# 
# NOTICE.  This Software was developed under funding from the U.S. Department
# of Energy and the U.S. Government consequently retains certain rights.  As
# such, the U.S. Government has been granted for itself and others acting on
# its behalf a paid-up, nonexclusive, irrevocable, worldwide license in the
# Software to reproduce, distribute copies to the public, prepare derivative 
# works, and perform publicly and display publicly, and to permit others to do so.

__docformat__ = 'reStructuredText'

import sys
import os
import json
import logging
import datetime
import threading
import asyncio
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np

# Volttron
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core, RPC, PubSub
from volttron.platform.messaging import headers as headers_mod

# Add project paths
project_root = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
sys.path.insert(0, project_root)

# Import AFC integration components
try:
    from ofc_afc_converter import OFCAFCConverter
    from agents.ofc_afc_algorithm.ofc_afc_algorithm.afc_wrapper import AFCWrapper
    from agents.ofc_afc_algorithm.ofc_afc_algorithm.weather_integration import WeatherIntegration
    from agents.ofc_afc_algorithm.ofc_afc_algorithm.data_converter import DataConverter
except ImportError as e:
    logging.warning(f"AFC components not available: {e}")
    OFCAFCConverter = None
    AFCWrapper = None
    WeatherIntegration = None
    DataConverter = None

utils.setup_logging()
_log = logging.getLogger(__name__)

__version__ = "0.2"


def ofc_afc_algorithm(config_path, **kwargs):
    """
    Load configuration from the given config path and instantiate an OFCAFCAlgorithm agent.

    :param config_path: Path to the configuration file.
    :param kwargs: Additional keyword arguments passed to the agent.
    :return: Instance of OFCAFCAlgorithm agent.
    """
    try:
        config = utils.load_config(config_path)
    except Exception as e:
        config = {}

    if not config:
        _log.info("Using Agent defaults for starting configuration.")

    return OFCAFCAlgorithm(config, **kwargs)


class OFCAFCAlgorithm(Agent):
    """
    Advanced Facade Controller (AFC) Algorithm Agent for OFC.
    
    This agent integrates the LBNL-ETA AFC with OFC's VOLTTRON infrastructure,
    providing Model Predictive Control (MPC) optimization for facade and HVAC systems.
    
    Features:
    - Weather forecast integration
    - Advanced daylighting and glare analysis
    - Multi-objective optimization (energy, comfort, cost)
    - Fallback to heuristic control
    - Real-time performance monitoring
    
    Attributes:
        config (dict): Agent configuration settings.
        afc_wrapper (AFCWrapper): AFC controller wrapper.
        weather_integration (WeatherIntegration): Weather forecast handler.
        data_converter (DataConverter): OFC-AFC data conversion utility.
        algorithm_params (dict): AFC algorithm parameters.
        control_ct (int): Counter for control cycles.
        last_optimization (datetime): Timestamp of last optimization.
        sensor_cache (dict): Cache of latest sensor readings.
        weather_cache (dict): Cache of latest weather data.
        afc_enabled (bool): Whether AFC optimization is available.
        fallback_mode (bool): Whether system is in fallback mode.
    """

    def __init__(self, config, **kwargs):
        """
        Initialize the OFCAFCAlgorithm agent.

        :param config: Dictionary containing configuration values for the agent.
        :param kwargs: Additional keyword arguments.
        """
        super(OFCAFCAlgorithm, self).__init__(**kwargs)
        
        # Configuration
        self.config = config
        self.algorithm_params = config.get('afc', {})
        
        # Initialize components
        self.afc_wrapper = None
        self.weather_integration = None 
        self.data_converter = DataConverter() if DataConverter else OFCAFCConverter()
        
        # State management
        self.control_ct = 0
        self.last_optimization = None
        self.sensor_cache = {}
        self.weather_cache = {}
        self.afc_enabled = False
        self.fallback_mode = config.get('fallback_mode', True)
        
        # Performance tracking
        self.performance_stats = {
            'optimization_count': 0,
            'optimization_failures': 0,
            'avg_optimization_time': 0,
            'last_objective_value': None
        }
        
        # Threading for async operations
        self._optimization_lock = threading.Lock()
        self._optimization_thread = None
        
        # Subscribe to configuration updates
        self.vip.config.subscribe(self.configure, actions=["NEW", "UPDATE"], pattern="config")
        
        _log.info(f"OFCAFCAlgorithm initialized - Fallback mode: {self.fallback_mode}")

    @Core.receiver('onstart')
    def onstart(self, sender, **kwargs):
        """
        Core receiver triggered when the agent starts.
        
        :param sender: The source of the event.
        :param kwargs: Additional arguments.
        """
        _log.info("OFCAFCAlgorithm agent starting...")
        
        try:
            # Initialize AFC components
            self._initialize_afc_components()
            
            # Setup subscriptions
            self._setup_subscriptions()
            
            # Schedule periodic tasks
            self._schedule_periodic_tasks()
            
            _log.info(f"OFCAFCAlgorithm started - AFC enabled: {self.afc_enabled}")
            
        except Exception as e:
            _log.error(f"Error during agent startup: {e}")
            self.fallback_mode = True

    def configure(self, config_name, action, contents):
        """
        Handle configuration updates for the agent.

        :param config_name: Name of the configuration file.
        :param action: The type of action (e.g., "NEW", "UPDATE").
        :param contents: The contents of the updated configuration.
        """
        _log.info(f"Configuration update: {config_name} - {action}")
        
        try:
            self.config.update(contents)
            self.algorithm_params = self.config.get('afc', {})
            
            # Reinitialize AFC components if needed
            if 'afc' in contents:
                self._initialize_afc_components()
                
            # Update fallback mode
            self.fallback_mode = self.config.get('fallback_mode', True)
            
            _log.info("Configuration updated successfully")
            
        except Exception as e:
            _log.error(f"Error updating configuration: {e}")

    def _initialize_afc_components(self):
        """Initialize AFC wrapper and related components."""
        try:
            if AFCWrapper and self.algorithm_params:
                # Initialize AFC wrapper
                self.afc_wrapper = AFCWrapper(self.algorithm_params)
                self.afc_enabled = True
                _log.info("AFC wrapper initialized successfully")
                
                # Initialize weather integration  
                if WeatherIntegration:
                    weather_config = self.config.get('weather', {})
                    self.weather_integration = WeatherIntegration(weather_config)
                    _log.info("Weather integration initialized")
                    
            else:
                _log.warning("AFC components not available - using fallback mode")
                self.afc_enabled = False
                self.fallback_mode = True
                
        except Exception as e:
            _log.error(f"Error initializing AFC components: {e}")
            self.afc_enabled = False
            self.fallback_mode = True

    def _setup_subscriptions(self):
        """Setup VOLTTRON message subscriptions."""
        try:
            # Subscribe to sensor data
            sensor_topics = self.config.get('sensor_topics', [
                'devices/ofc/glare_sensor/all',
                'devices/ofc/occupancy_sensor/all',
                'devices/ofc/illuminance_sensor/all', 
                'devices/ofc/temp_sensor/all'
            ])
            
            for topic in sensor_topics:
                self.vip.pubsub.subscribe(
                    peer='pubsub',
                    prefix=topic,
                    callback=self.on_sensor_data
                )
                _log.debug(f"Subscribed to sensor topic: {topic}")
            
            # Subscribe to weather data
            weather_topics = self.config.get('weather_topics', [
                'devices/ofc/weather/all',
                'weather/forecast/all'
            ])
            
            for topic in weather_topics:
                self.vip.pubsub.subscribe(
                    peer='pubsub',
                    prefix=topic,
                    callback=self.on_weather_data
                )
                _log.debug(f"Subscribed to weather topic: {topic}")
            
            # Subscribe to control requests
            control_topic = self.config.get('control_request_topic', 'ofc/control_request')
            self.vip.pubsub.subscribe(
                peer='pubsub',
                prefix=control_topic,
                callback=self.on_control_request
            )
            _log.info(f"Subscribed to control requests: {control_topic}")
            
        except Exception as e:
            _log.error(f"Error setting up subscriptions: {e}")

    def _schedule_periodic_tasks(self):
        """Schedule periodic maintenance tasks."""
        try:
            # Schedule optimization cycle
            optimization_interval = self.config.get('optimization_interval', 3600)  # 1 hour default
            self.core.schedule(
                datetime.datetime.now() + datetime.timedelta(seconds=optimization_interval),
                self._periodic_optimization
            )
            
            # Schedule weather forecast updates
            weather_interval = self.config.get('weather_update_interval', 1800)  # 30 minutes default
            self.core.schedule(
                datetime.datetime.now() + datetime.timedelta(seconds=weather_interval),
                self._update_weather_forecast
            )
            
            _log.info("Periodic tasks scheduled")
            
        except Exception as e:
            _log.error(f"Error scheduling periodic tasks: {e}")

    def on_sensor_data(self, peer, sender, bus, topic, headers, message):
        """
        Handle incoming sensor data.
        
        :param peer: Peer identifier.
        :param sender: Sender identifier.
        :param bus: Message bus.
        :param topic: Topic string.
        :param headers: Message headers.
        :param message: Sensor data message.
        """
        try:
            _log.debug(f"Received sensor data: {topic}")
            
            # Extract and cache sensor data
            sensor_data = message[0] if isinstance(message, list) else message
            timestamp = datetime.datetime.now()
            
            # Cache sensor reading
            sensor_id = self._extract_sensor_id(topic)
            self.sensor_cache[sensor_id] = {
                'data': sensor_data,
                'timestamp': timestamp,
                'topic': topic
            }
            
            # Trigger optimization if conditions met
            self._check_optimization_trigger()
            
        except Exception as e:
            _log.error(f"Error processing sensor data from {topic}: {e}")

    def on_weather_data(self, peer, sender, bus, topic, headers, message):
        """
        Handle incoming weather data.
        
        :param peer: Peer identifier.
        :param sender: Sender identifier.
        :param bus: Message bus.
        :param topic: Topic string.
        :param headers: Message headers.
        :param message: Weather data message.
        """
        try:
            _log.debug(f"Received weather data: {topic}")
            
            # Extract and cache weather data
            weather_data = message[0] if isinstance(message, list) else message
            timestamp = datetime.datetime.now()
            
            self.weather_cache = {
                'data': weather_data,
                'timestamp': timestamp,
                'topic': topic
            }
            
            # Update weather integration if available
            if self.weather_integration:
                self.weather_integration.update_current_weather(weather_data)
                
        except Exception as e:
            _log.error(f"Error processing weather data from {topic}: {e}")

    def on_control_request(self, peer, sender, bus, topic, headers, message):
        """
        Handle control requests from area controllers.
        
        :param peer: Peer identifier.
        :param sender: Sender identifier.
        :param bus: Message bus.
        :param topic: Topic string.
        :param headers: Message headers.
        :param message: Control request message.
        """
        try:
            _log.info(f"Received control request: {topic}")
            
            # Extract control request
            request = message[0] if isinstance(message, list) else message
            
            # Process the control request
            response = self._process_control_request(request)
            
            # Send response
            response_topic = request.get('response_topic', f"{topic}/response")
            self.vip.pubsub.publish(
                peer='pubsub',
                topic=response_topic,
                message=response,
                headers={'AgentID': self.core.identity}
            )
            
            _log.info(f"Control response sent to: {response_topic}")
            
        except Exception as e:
            _log.error(f"Error processing control request: {e}")

    def _process_control_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a control request and return optimization results.
        
        :param request: Control request dictionary.
        :return: Control response dictionary.
        """
        try:
            start_time = datetime.datetime.now()
            
            # Extract request parameters
            area_id = request.get('area_id', 'unknown')
            devices = request.get('devices', [])
            sensor_data = request.get('sensor_data', {})
            
            _log.info(f"Processing control request for area {area_id} with {len(devices)} devices")
            
            # Get weather forecast
            weather_forecast = self._get_weather_forecast()
            
            if not weather_forecast:
                _log.warning("No weather forecast available - using fallback control")
                return self._fallback_control(request)
            
            # Run AFC optimization
            if self.afc_enabled and not self.fallback_mode:
                try:
                    optimization_result = self._run_afc_optimization(
                        sensor_data, weather_forecast, devices
                    )
                    
                    if optimization_result and optimization_result.get('valid', False):
                        # Convert to OFC format
                        control_commands = self.data_converter.afc_outputs_to_ofc_commands(
                            optimization_result
                        )
                        
                        # Update performance stats
                        duration = (datetime.datetime.now() - start_time).total_seconds()
                        self._update_performance_stats(duration, optimization_result)
                        
                        return {
                            'success': True,
                            'area_id': area_id,
                            'control_commands': control_commands,
                            'optimization_data': optimization_result.get('optimization_data', {}),
                            'source': 'afc_optimization',
                            'duration': duration,
                            'timestamp': datetime.datetime.now().isoformat()
                        }
                        
                    else:
                        _log.warning("AFC optimization failed - using fallback control")
                        return self._fallback_control(request)
                        
                except Exception as e:
                    _log.error(f"AFC optimization error: {e}")
                    self.performance_stats['optimization_failures'] += 1
                    return self._fallback_control(request)
            else:
                _log.info("AFC disabled - using fallback control")
                return self._fallback_control(request)
                
        except Exception as e:
            _log.error(f"Error processing control request: {e}")
            return {
                'success': False,
                'error': str(e),
                'area_id': request.get('area_id', 'unknown'),
                'timestamp': datetime.datetime.now().isoformat()
            }

    def _run_afc_optimization(self, sensor_data: Dict[str, Any], 
                            weather_forecast: pd.DataFrame,
                            devices: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Run AFC optimization with current conditions.
        
        :param sensor_data: Current sensor readings.
        :param weather_forecast: Weather forecast DataFrame.
        :param devices: List of devices to control.
        :return: AFC optimization results or None if failed.
        """
        try:
            if not self.afc_wrapper:
                return None
            
            # Convert OFC data to AFC format
            afc_inputs = self.data_converter.ofc_sensors_to_afc_inputs(
                sensor_data, weather_forecast
            )
            
            # Validate inputs
            is_valid, errors = self.data_converter.validate_afc_inputs(afc_inputs)
            if not is_valid:
                _log.error(f"AFC input validation failed: {errors}")
                return None
            
            # Run AFC optimization
            with self._optimization_lock:
                result = self.afc_wrapper.optimize(afc_inputs, devices)
                self.control_ct += 1
                self.last_optimization = datetime.datetime.now()
                
            return result
            
        except Exception as e:
            _log.error(f"AFC optimization failed: {e}")
            return None

    def _fallback_control(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provide fallback control using simple heuristics.
        
        :param request: Original control request.
        :return: Fallback control response.
        """
        try:
            area_id = request.get('area_id', 'unknown')
            devices = request.get('devices', [])
            sensor_data = request.get('sensor_data', {})
            
            # Simple heuristic control logic
            control_commands = []
            
            for device in devices:
                device_type = device.get('type', '')
                zone_id = device.get('zone_id', 'zone_0')
                
                if 'facade' in device_type.lower() or 'window' in device_type.lower():
                    # Simple glare-based facade control
                    glare = sensor_data.get('glare', 100)
                    if glare > 300:
                        setpoint = 1.0  # High tint
                    elif glare > 150:
                        setpoint = 2.0  # Medium tint
                    else:
                        setpoint = 3.0  # Clear
                        
                    control_commands.append({
                        'device_id': device.get('device_id'),
                        'device_type': device_type,
                        'point': 'setpoint',
                        'value': setpoint,
                        'timestamp': datetime.datetime.now().isoformat(),
                        'zone': zone_id
                    })
                    
                elif 'hvac' in device_type.lower():
                    # Simple temperature-based HVAC control
                    temp = sensor_data.get('temperature', 22.0)
                    occupancy = sensor_data.get('occupancy', 1)
                    
                    if occupancy:
                        cooling_setpoint = 24.0
                        heating_setpoint = 20.0
                    else:
                        cooling_setpoint = 26.0  # Higher for energy savings
                        heating_setpoint = 18.0  # Lower for energy savings
                        
                    if 'cooling' in device_type.lower():
                        value = cooling_setpoint
                        point = 'cooling_setpoint'
                    else:
                        value = heating_setpoint
                        point = 'heating_setpoint'
                        
                    control_commands.append({
                        'device_id': device.get('device_id'),
                        'device_type': device_type,
                        'point': point,
                        'value': value,
                        'timestamp': datetime.datetime.now().isoformat(),
                        'zone': zone_id
                    })
            
            return {
                'success': True,
                'area_id': area_id,
                'control_commands': control_commands,
                'source': 'fallback_heuristic',
                'timestamp': datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            _log.error(f"Fallback control failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'area_id': request.get('area_id', 'unknown'),
                'source': 'fallback_heuristic',
                'timestamp': datetime.datetime.now().isoformat()
            }

    def _get_weather_forecast(self) -> Optional[pd.DataFrame]:
        """
        Get weather forecast data.
        
        :return: Weather forecast DataFrame or None.
        """
        try:
            if self.weather_integration:
                return self.weather_integration.get_forecast()
            elif self.weather_cache:
                # Create simple forecast from current weather
                current = self.weather_cache['data']
                times = pd.date_range(
                    datetime.datetime.now(),
                    datetime.datetime.now() + datetime.timedelta(hours=24),
                    freq='h'
                )
                
                # Simple persistence forecast
                forecast_data = {}
                for key in ['dni', 'dhi', 'temp_air', 'wind_speed']:
                    if key in current:
                        forecast_data[key] = [current[key]] * len(times)
                    else:
                        # Default values
                        defaults = {'dni': 400, 'dhi': 100, 'temp_air': 20, 'wind_speed': 2}
                        forecast_data[key] = [defaults[key]] * len(times)
                        
                return pd.DataFrame(forecast_data, index=times)
            else:
                _log.warning("No weather data available")
                return None
                
        except Exception as e:
            _log.error(f"Error getting weather forecast: {e}")
            return None

    def _check_optimization_trigger(self):
        """Check if conditions are met to trigger optimization."""
        try:
            # Check if enough time has passed since last optimization
            min_interval = self.config.get('min_optimization_interval', 300)  # 5 minutes
            
            if (self.last_optimization and 
                (datetime.datetime.now() - self.last_optimization).total_seconds() < min_interval):
                return
            
            # Check if we have sufficient sensor data
            required_sensors = self.config.get('required_sensors', ['glare', 'occupancy'])
            sensor_ids = set(self.sensor_cache.keys())
            
            if not all(sensor in str(sensor_ids) for sensor in required_sensors):
                _log.debug("Insufficient sensor data for optimization")
                return
            
            # Trigger optimization in background
            if not self._optimization_thread or not self._optimization_thread.is_alive():
                self._optimization_thread = threading.Thread(
                    target=self._background_optimization,
                    daemon=True
                )
                self._optimization_thread.start()
                
        except Exception as e:
            _log.error(f"Error checking optimization trigger: {e}")

    def _background_optimization(self):
        """Run optimization in background thread."""
        try:
            _log.debug("Running background optimization")
            
            # Create synthetic control request from cached data
            request = {
                'area_id': 'background',
                'devices': self.config.get('managed_devices', []),
                'sensor_data': {k: v['data'] for k, v in self.sensor_cache.items()}
            }
            
            # Process the request
            result = self._process_control_request(request)
            
            if result.get('success'):
                # Publish optimization results
                self.vip.pubsub.publish(
                    peer='pubsub',
                    topic='ofc/afc/optimization_results',
                    message=result,
                    headers={'AgentID': self.core.identity}
                )
                
        except Exception as e:
            _log.error(f"Background optimization error: {e}")

    def _periodic_optimization(self):
        """Periodic optimization task."""
        try:
            _log.debug("Running periodic optimization")
            self._check_optimization_trigger()
            
            # Reschedule next periodic optimization
            optimization_interval = self.config.get('optimization_interval', 3600)
            self.core.schedule(
                datetime.datetime.now() + datetime.timedelta(seconds=optimization_interval),
                self._periodic_optimization
            )
            
        except Exception as e:
            _log.error(f"Periodic optimization error: {e}")

    def _update_weather_forecast(self):
        """Update weather forecast data."""
        try:
            if self.weather_integration:
                self.weather_integration.update_forecast()
                _log.debug("Weather forecast updated")
            
            # Reschedule next weather update
            weather_interval = self.config.get('weather_update_interval', 1800)
            self.core.schedule(
                datetime.datetime.now() + datetime.timedelta(seconds=weather_interval),
                self._update_weather_forecast
            )
            
        except Exception as e:
            _log.error(f"Weather forecast update error: {e}")

    def _extract_sensor_id(self, topic: str) -> str:
        """Extract sensor ID from topic string."""
        parts = topic.split('/')
        return '_'.join(parts[-3:-1]) if len(parts) >= 3 else topic

    def _update_performance_stats(self, duration: float, result: Dict[str, Any]):
        """Update performance statistics."""
        try:
            self.performance_stats['optimization_count'] += 1
            
            # Update average optimization time
            count = self.performance_stats['optimization_count']
            avg_time = self.performance_stats['avg_optimization_time']
            self.performance_stats['avg_optimization_time'] = (
                (avg_time * (count - 1) + duration) / count
            )
            
            # Store last objective value
            opt_data = result.get('optimization_data', {})
            self.performance_stats['last_objective_value'] = opt_data.get('objective_value')
            
        except Exception as e:
            _log.error(f"Error updating performance stats: {e}")

    @RPC.export
    def calculate_setpoints(self, sensor_data: Dict[str, Any], 
                          weather_forecast: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Calculate control setpoints using AFC optimization.
        
        :param sensor_data: Current sensor readings.
        :param weather_forecast: Optional weather forecast data.
        :return: Control setpoints and optimization data.
        """
        try:
            # Create control request
            request = {
                'area_id': 'rpc_request',
                'devices': self.config.get('managed_devices', []),
                'sensor_data': sensor_data
            }
            
            # Add weather forecast if provided
            if weather_forecast:
                self.weather_cache = {
                    'data': weather_forecast,
                    'timestamp': datetime.datetime.now()
                }
            
            # Process request
            result = self._process_control_request(request)
            
            return result
            
        except Exception as e:
            _log.error(f"Error in calculate_setpoints: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.datetime.now().isoformat()
            }

    @RPC.export
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get current performance statistics.
        
        :return: Performance statistics dictionary.
        """
        stats = self.performance_stats.copy()
        stats.update({
            'afc_enabled': self.afc_enabled,
            'fallback_mode': self.fallback_mode,
            'control_cycles': self.control_ct,
            'last_optimization': self.last_optimization.isoformat() if self.last_optimization else None,
            'cached_sensors': len(self.sensor_cache),
            'weather_available': bool(self.weather_cache),
            'version': __version__
        })
        return stats

    @RPC.export
    def set_fallback_mode(self, enabled: bool) -> Dict[str, Any]:
        """
        Enable or disable fallback mode.
        
        :param enabled: Whether to enable fallback mode.
        :return: Status dictionary.
        """
        try:
            self.fallback_mode = enabled
            _log.info(f"Fallback mode {'enabled' if enabled else 'disabled'}")
            
            return {
                'success': True,
                'fallback_mode': self.fallback_mode,
                'timestamp': datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            _log.error(f"Error setting fallback mode: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.datetime.now().isoformat()
            }

    @RPC.export
    def force_optimization(self) -> Dict[str, Any]:
        """
        Force an immediate optimization cycle.
        
        :return: Optimization result.
        """
        try:
            _log.info("Forcing optimization cycle")
            
            # Create request from cached data
            request = {
                'area_id': 'forced_optimization',
                'devices': self.config.get('managed_devices', []),
                'sensor_data': {k: v['data'] for k, v in self.sensor_cache.items()}
            }
            
            result = self._process_control_request(request)
            
            return result
            
        except Exception as e:
            _log.error(f"Error in forced optimization: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.datetime.now().isoformat()
            }