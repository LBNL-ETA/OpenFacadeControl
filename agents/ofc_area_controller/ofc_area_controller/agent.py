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
import logging
from collections import defaultdict
from datetime import timedelta

# Volttron
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core, RPC
from volttron.platform.scheduling import periodic
from volttron.platform.agent.utils import format_timestamp, get_aware_utc_now

utils.setup_logging()
_log = logging.getLogger(__name__)

__version__ = "0.1"


def ofc_controller(config_path, **kwargs):
    """
    Load configuration from the given config path and instantiate an OFCController agent.

    :param config_path: Path to the configuration file.
    :param kwargs: Additional keyword arguments passed to the agent.
    :return: Instance of OFCController agent.
    """
    try:
        config = utils.load_config(config_path)
    except Exception as e:
        config = {}

    if not config:
        _log.info("Using Agent defaults for starting configuration.")

    return OFCController(config, **kwargs)


TYPE_TO_ENDPOINT_MAP = {
    "Light": [],
    "Occupancy": [],
    "Façade State": [],
    "Glare": [],
    "Illuminance": [],
    "Solar Radiation": []
}


class OFCController(Agent):
    """
    Agent class responsible for managing and controlling areas based on various configurations
    and handling different types of endpoints (e.g., Light, Façade State).

    Attributes:
        areas (dict): A dictionary mapping area names to their configurations.
        config (dict): The agent's configuration settings.
        control_ct (int): A counter for control actions.
        counter (int): A general-purpose counter for operations.
    """

    def __init__(self, config, **kwargs):
        """
        Initialize the OFCController agent with the given configuration.

        :param config: Dictionary containing configuration values for the agent.
        :param kwargs: Additional keyword arguments.
        """
        super(OFCController, self).__init__(**kwargs)
        self.areas = {}
        _log.info(f"In __init__ with config: {config} kwargs:{kwargs}")
        self.config = config
        self.control_ct = 0
        self.counter = 0
        self.vip.config.subscribe(self.configure, actions=["NEW", "UPDATE"], pattern="config")
        self.vip.config.subscribe(self.add_area, actions=["NEW", "UPDATE"], pattern="areas/*")
        self.vip.config.subscribe(self.remove_area, actions="DELETE", pattern="areas/*")
        _log.info(f"Finished __init__")
        self.periodic_f = lambda: None

    @Core.receiver('onstart')
    def onstart(self, sender, **kwargs):
        """
        Core receiver that is triggered when the agent starts. This schedules the periodic control loop.

        :param sender: The source of the event.
        :param kwargs: Additional arguments.
        """
        _log.info(f"In onstart self.config: {self.config} sender: {sender} kwargs: {kwargs}")
        self.periodic_f = self.core.schedule(periodic(10), self.start_control_loop)
        _log.info(f"Finished onstart self.config: {self.config} sender: {sender} kwargs: {kwargs}")

    def configure(self, config_name, action, contents):
        """
        Handles configuration updates for the agent.

        :param config_name: Name of the configuration file.
        :param action: The type of action (e.g., "NEW", "UPDATE").
        :param contents: The contents of the updated configuration.
        """
        _log.info(f"In configure with config_name: {config_name} action: {action}, contents: {contents}")
        _log.info(f"Finished configure")

    def add_area(self, config_name, action, contents):
        """
        Adds a new area based on the configuration provided.

        :param config_name: The name of the area to add.
        :param action: The type of action (e.g., "NEW", "UPDATE").
        :param contents: The configuration details for the area.
        """
        _log.info(f"In add_area with config_name: {config_name} action: {action}, contents: {contents}")
        try:
            endpoints = TYPE_TO_ENDPOINT_MAP.copy()
            devices = contents.get("Devices", [])
            for device in devices:
                device_type = device.get("Type")
                endpoint = device.get("VOLTTRON Endpoint")
                if device_type not in endpoints:
                    raise RuntimeError("Unsupported type: {device_type}")
                endpoints[device_type].append(endpoint)

            self.areas[config_name] = {
                "endpoints": endpoints,
                "control_options": contents.get("Control Options")
            }
        except Exception as e:
            _log.error(f"Error in add_area: {e}")
        _log.info(f"Finished add_area")

    def remove_area(self, config_name, action, contents):
        """
        Removes an existing area from the agent's management.

        :param config_name: The name of the area to remove.
        :param action: The type of action ("DELETE").
        :param contents: The configuration details (not used).
        """
        _log.info(f"In remove_area with config_name: {config_name} action: {action}, contents: {contents}")
        existing_area = self.areas.get(config_name)
        if existing_area:
            del self.areas[config_name]
        _log.info(f"Finished remove_area")

    @RPC.export
    def get_areas(self):
        """
        RPC method to retrieve the list of areas managed by the agent.

        :return: Dictionary of areas and their configurations.
        """
        return self.areas

    def get_topic_data_from_historian(self, topic):
        """
        Fetches historical data for a given topic from the platform historian.

        :param topic: The topic to query.
        :return: Data points for the specified topic.
        """
        _log.info(f"In get_topic_data_from_historian with topic: {topic}")
        try:
            data = self.vip.rpc.call(
                'platform.historian',
                'query',
                topic=topic,
                count=10,  # Maximum number of data points to return
                order="LAST_TO_FIRST"
            ).get(timeout=10)  # Timeout in seconds

            if data:
                _log.info(f"Received data: {data}")
            else:
                _log.info("No data received for the given time period.")
            return data
        except Exception as e:
            _log.info(f"Failed to fetch data: {str(e)}")

    @RPC.export
    def get_summary(self):
        """
        RPC method to generate a summary of areas with their respective endpoint data.

        :return: Summary of areas and their associated historical data.
        """
        summary = self.areas.copy()
        for config_name, config in summary.items():
            for endpoint_type, endpoints in config.get("endpoints").items():
                for idx, endpoint in enumerate(endpoints):
                    data = self.get_topic_data_from_historian(endpoint)
                    summary[config_name]["endpoints"][endpoint_type][idx] = {"endpoint": endpoint, "values": data}
        return summary

    @RPC.export
    def endpoints(self):
        """
        RPC method to retrieve the available endpoints and their corresponding data.

        :return: Dictionary of endpoints and their respective data.
        """
        res = defaultdict(dict)
        for endpoint_type, endpoints in self.endpoints.items():
            for endpoint in endpoints:
                res[endpoint_type][endpoint] = list(self.endpoints[endpoint_type][endpoint])
        return res

    def start_control_loop(self):
        """
        Start the control loop which periodically publishes control messages to endpoints.
        """
        try:
            headers = {"from": self.core.identity}
            for area_name, config in self.areas.items():
                msg = {"area": area_name, "endpoints": config.get("endpoints")}
                _log.info(f"Publishing control message for area {area_name}: {msg}")
                self.vip.pubsub.publish('pubsub', "agent/ofc_generic_control_algorithm", headers, msg)
        except Exception as e:
            _log.error(f"Error in start_control_loop: {e}")

    def schedule_and_actuate(self, endpoint, value):
        """
        Schedules and performs actuation for a given endpoint with the specified value.

        :param endpoint: The endpoint to actuate.
        :param value: The value to set for the endpoint.
        """
        result = {}
        try:
            _log.info(f"Scheduling actuation for: {endpoint}")
            self.counter += 1
            _now = get_aware_utc_now()
            str_now = format_timestamp(_now)
            str_end = format_timestamp(_now + timedelta(seconds=10))
            schedule_request = [[endpoint, str_now, str_end]]
            task_name = f"{_now}: {endpoint} {value}"
            result = self.vip.rpc.call(
                'platform.actuator', 'request_new_schedule', self.core.identity, task_name,
                'HIGH', schedule_request).get(timeout=4)
            _log.info(f"Schedule result: {result}")
        except Exception as e:
            _log.error(f"Error scheduling actuation for {endpoint}: {e}")

        try:
            if result.get("result") != "SUCCESS":
                _log.info(f"Schedule result was not successful.")
            result = self.vip.rpc.call('platform.actuator', 'set_point', self.core.identity, endpoint, value).get(
                timeout=4)
            _log.info(f"Set point result: {result}")
        except Exception as e:
            _log.error(f"Error actuating endpoint {endpoint}: {e}")

    @RPC.export
    def do_control(self, area_name, light_level, facade_state):
        """
        Perform control actions for a specified area by adjusting light level and façade state.

        :param area_name: Name of the area to control.
        :param light_level: Desired light level for the area.
        :param facade_state: Desired façade state for the area.
        """
        _log.info(
            f"Entered do_control with area: {area_name}, light_level: {light_level}, facade_state: {facade_state}")
        area = self.areas.get(area_name)
        if not area:
            _log.error(f"Area {area_name} not found in areas: {self.areas.keys()}")
            return
        endpoints = area.get("endpoints")
        if not endpoints:
            _log.error(f"Area {area_name} missing endpoints")
            return

        for light_level_endpoint in endpoints.get("Light", []):
            self.schedule_and_actuate(light_level_endpoint, light_level)
        for facade_state_endpoint in endpoints.get("Façade State", []):
            self.schedule_and_actuate(facade_state_endpoint, facade_state)
        _log.info(f"Finished do_control")


def main():
    """
    Main method called to start the agent.
    """
    utils.vip_main(ofc_controller, version=__version__)


if __name__ == '__main__':
    # Entry point for the script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
