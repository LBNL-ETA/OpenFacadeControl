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
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional

# Volttron
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core, RPC, PubSub
from volttron.platform.messaging import headers as headers_mod

# Add project root to path for imports
project_root = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
sys.path.insert(0, project_root)

# Import OFC-AFC converter
try:
    from ofc_afc_converter import OFCAFCConverter
except ImportError:
    # Fallback if converter not found
    OFCAFCConverter = None
    

utils.setup_logging()
_log = logging.getLogger(__name__)

__version__ = "0.1"

def ofc_afc_test_agent(config_path, **kwargs):
    """
    Load configuration from the given config path and instantiate an OFCAFCTestAgent.

    :param config_path: Path to the configuration file.
    :param kwargs: Additional keyword arguments passed to the agent.
    :return: Instance of OFCAFCTestAgent.
    """
    try:
        config = utils.load_config(config_path)
    except Exception as e:
        config = {}

    if not config:
        _log.info("Using Agent defaults for starting configuration.")

    return OFCAFCTestAgent(config, **kwargs)


class OFCAFCTestAgent(Agent):
    """
    Test agent for AFC integration with OFC.
    
    This agent provides basic AFC functionality for Phase 1 testing,
    including data conversion and simplified optimization without full
    AFC dependencies.
    
    Attributes:
        config (dict): Agent configuration settings.
        converter (OFCAFCConverter): Data conversion utility.
        afc_enabled (bool): Whether AFC functionality is available.
        test_mode (bool): Whether to run in test mode with simulated AFC.
    """

    def __init__(self, config, **kwargs):
        """
        Initialize the OFCAFCTestAgent with the given configuration.

        :param config: Dictionary containing configuration values for the agent.
        :param kwargs: Additional keyword arguments.
        """
        super(OFCAFCTestAgent, self).__init__(**kwargs)
        self.config = config
        self.converter = OFCAFCConverter() if OFCAFCConverter else None
        self.afc_enabled = self.converter is not None
        self.test_mode = config.get('test_mode', True)
        self.control_ct = 0
        
        # Subscribe to configuration updates
        self.vip.config.subscribe(self.configure, actions=["NEW", "UPDATE"], pattern="config")
        
        _log.info(f"OFCAFCTestAgent initialized - AFC enabled: {self.afc_enabled}, Test mode: {self.test_mode}")

    @Core.receiver('onstart')
    def onstart(self, sender, **kwargs):
        """
        Core receiver that is triggered when the agent starts.
        
        :param sender: The source of the event.
        :param kwargs: Additional arguments.
        """
        _log.info("OFCAFCTestAgent started")
        
        # Subscribe to sensor data topics
        sensor_topics = self.config.get('sensor_topics', [
            'devices/ofc/glare_sensor/all',
            'devices/ofc/occupancy_sensor/all', 
            'devices/ofc/illuminance_sensor/all',
            'devices/ofc/temp_sensor/all'
        ])
        
        for topic in sensor_topics:
            self.vip.pubsub.subscribe(peer='pubsub', prefix=topic, callback=self.on_sensor_data)
            _log.info(f"Subscribed to sensor topic: {topic}")

    def configure(self, config_name, action, contents):
        """
        Handles configuration updates for the agent.

        :param config_name: Name of the configuration file.
        :param action: The type of action (e.g., "NEW", "UPDATE").
        :param contents: The contents of the updated configuration.
        """
        _log.info(f"Configuration update: {config_name} - {action}")
        self.config.update(contents)
        
        # Update test mode setting
        self.test_mode = self.config.get('test_mode', True)
        _log.info(f"Test mode set to: {self.test_mode}")

    @PubSub.subscribe('pubsub', 'devices/ofc/weather/all')
    def on_weather_data(self, peer, sender, bus, topic, headers, message):
        """
        Handle weather forecast data updates.
        
        :param peer: Peer identifier.
        :param sender: Sender identifier.
        :param bus: Message bus.
        :param topic: Topic string.
        :param headers: Message headers.
        :param message: Weather data message.
        """
        try:
            _log.debug(f"Received weather data: {topic}")
            
            # Extract weather data
            weather_data = message[0] if isinstance(message, list) else message
            
            # Store for AFC processing
            self.latest_weather = weather_data
            
        except Exception as e:
            _log.error(f"Error processing weather data: {e}")

    def on_sensor_data(self, peer, sender, bus, topic, headers, message):
        """
        Handle sensor data updates from various OFC sensors.
        
        :param peer: Peer identifier.
        :param sender: Sender identifier.
        :param bus: Message bus.
        :param topic: Topic string.
        :param headers: Message headers.
        :param message: Sensor data message.
        """
        try:
            _log.debug(f"Received sensor data: {topic}")
            
            # Extract sensor data
            sensor_data = message[0] if isinstance(message, list) else message
            
            # Process if we have AFC converter
            if self.converter:
                # This would trigger AFC optimization in full implementation
                self._process_sensor_update(topic, sensor_data)
                
        except Exception as e:
            _log.error(f"Error processing sensor data from {topic}: {e}")

    def _process_sensor_update(self, topic: str, sensor_data: Dict[str, Any]):
        """
        Process sensor data update and potentially trigger AFC optimization.
        
        :param topic: Sensor topic string.
        :param sensor_data: Sensor data dictionary.
        """
        try:
            # In test mode, simulate AFC behavior
            if self.test_mode:
                self._simulate_afc_optimization(sensor_data)
            else:
                # This would call actual AFC controller
                pass
                
        except Exception as e:
            _log.error(f"Error in sensor processing: {e}")

    def _simulate_afc_optimization(self, sensor_data: Dict[str, Any]):
        """
        Simulate AFC optimization for testing purposes.
        
        :param sensor_data: Current sensor readings.
        """
        try:
            self.control_ct += 1
            
            # Create sample weather data for testing
            current_time = datetime.datetime.now()
            times = pd.date_range(current_time, current_time + datetime.timedelta(hours=8), freq='h')
            
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
                _log.warning(f"AFC input validation failed: {errors}")
                return
            
            # Simulate AFC optimization results
            simulated_results = self._generate_simulated_afc_results(afc_inputs)
            
            # Convert to OFC commands
            ofc_commands = self.converter.afc_outputs_to_ofc_commands(simulated_results)
            
            # Publish control commands
            self._publish_control_commands(ofc_commands)
            
            _log.info(f"AFC simulation cycle {self.control_ct} completed - {len(ofc_commands)} commands generated")
            
        except Exception as e:
            _log.error(f"Error in AFC simulation: {e}")

    def _generate_simulated_afc_results(self, afc_inputs: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate simulated AFC optimization results for testing.
        
        :param afc_inputs: AFC input DataFrame.
        :return: Simulated AFC results.
        """
        # Simple rule-based simulation
        current_data = afc_inputs.iloc[0]
        
        # Simulate facade control based on DNI
        dni = current_data.get('dni', 0)
        if dni > 400:
            facade_state = 1.0  # Partially tinted
        elif dni > 200:
            facade_state = 2.0  # Moderately tinted
        else:
            facade_state = 3.0  # Clear
        
        # Simulate HVAC based on temperature
        temp = current_data.get('temp_air', 22)
        cooling_setpoint = min(26, temp + 2)
        heating_setpoint = max(18, temp - 2)
        
        return {
            'facade_setpoints': [
                {
                    'zone_id': 'zone_0',
                    'device_type': 'electrochromic_window', 
                    'setpoint': facade_state,
                    'timestamp': datetime.datetime.now().isoformat()
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

    def _publish_control_commands(self, ofc_commands: List[Dict[str, Any]]):
        """
        Publish OFC control commands to the message bus.
        
        :param ofc_commands: List of OFC device commands.
        """
        try:
            for cmd in ofc_commands:
                topic = f"devices/ofc/{cmd['device_type']}/{cmd['zone']}/actuate"
                
                # Create command message
                message = {
                    'device_id': cmd['device_id'],
                    'point': cmd['point'],
                    'value': cmd['value'],
                    'timestamp': cmd['timestamp'],
                    'source': 'afc_test_agent'
                }
                
                # Publish command
                self.vip.pubsub.publish(
                    peer='pubsub',
                    topic=topic,
                    message=message,
                    headers={'AgentID': self.core.identity}
                )
                
                _log.debug(f"Published command: {topic} -> {cmd['value']}")
                
        except Exception as e:
            _log.error(f"Error publishing control commands: {e}")

    @RPC.export
    def get_afc_status(self) -> Dict[str, Any]:
        """
        Get current AFC integration status.
        
        :return: Status dictionary.
        """
        return {
            'afc_enabled': self.afc_enabled,
            'test_mode': self.test_mode,
            'control_cycles': self.control_ct,
            'converter_available': self.converter is not None,
            'version': __version__
        }

    @RPC.export
    def run_afc_test(self, sensor_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run a manual AFC test with provided or simulated sensor data.
        
        :param sensor_data: Optional sensor data for testing.
        :return: Test results.
        """
        try:
            if not self.converter:
                return {'error': 'AFC converter not available'}
            
            # Use provided data or create test data
            if sensor_data is None:
                sensor_data = {
                    'glare_sensor_1': 200,
                    'occupancy_sensor_1': 1,
                    'illuminance_sensor_1': 400,
                    'temp_sensor_1': 23.0
                }
            
            # Run simulation
            self._simulate_afc_optimization(sensor_data)
            
            return {
                'success': True,
                'message': 'AFC test completed successfully',
                'control_cycle': self.control_ct
            }
            
        except Exception as e:
            _log.error(f"Error in AFC test: {e}")
            return {'error': str(e)}


def main():
    """Main function for testing the agent."""
    # Simple test function
    try:
        config = {'test_mode': True}
        agent = OFCAFCTestAgent(config)
        print("OFCAFCTestAgent created successfully")
        return True
    except Exception as e:
        print(f"Error creating agent: {e}")
        return False


if __name__ == "__main__":
    main()