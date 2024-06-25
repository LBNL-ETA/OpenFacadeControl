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

    """

    def __init__(self, config, **kwargs):
        super(OFCController, self).__init__(**kwargs)

        self.areas = {}
        _log.info(f"in __init__ with config: {config} kwargs:{kwargs}")
        self.config = config
        self.control_ct = 0
        self.counter = 0
        self.vip.config.subscribe(self.configure, actions=["NEW", "UPDATE"], pattern="config")
        self.vip.config.subscribe(self.add_area, actions=["NEW", "UPDATE"], pattern="areas/*")
        self.vip.config.subscribe(self.remove_area, actions="DELETE", pattern="areas/*")
        _log.info(f"finished __init__")
        self.periodic_f = lambda: None

    @Core.receiver('onstart')
    def onstart(self, sender, **kwargs):
        """

        """
        _log.info(f"in onstart self.config: {self.config} sender: {sender} kwargs: {kwargs}")
        self.periodic_f = self.core.schedule(periodic(10), self.start_control_loop)
        _log.info(f"finished onstart self.config: {self.config} sender: {sender} kwargs: {kwargs}")

    def configure(self, config_name, action, contents):
        _log.info(f"in configure with config_name: {config_name} action:{action}, contents: {contents}")

        _log.info(f"finished configure")
        
    def add_area(self, config_name, action, contents):
        _log.info(f"in add_area with config_name: {config_name} action:{action}, contents: {contents}")

        try:
            endpoints = TYPE_TO_ENDPOINT_MAP.copy()

            devices = contents.get("Devices", [])
            for device in devices:
                device_type = device.get("Type")
                endpoint = device.get("VOLTTRON Endpoint")

                if device_type not in endpoints:
                    raise RuntimeError("Unsupported type: {device_type}")

                endpoints[device_type].append(endpoint)

            self.areas[config_name] = {"endpoints": endpoints, "control_options": contents.get("Control Options")}
        except Exception as e:
            _log.error(f"Error in add_area: {e}")

        _log.info(f"finished add_area")

    def remove_area(self, config_name, action, contents):
        _log.info(f"in remove_area with config_name: {config_name} action:{action}, contents: {contents}")

        existing_area = self.areas.get(config_name)
        if existing_area:
            del self.areas[config_name]

        _log.info(f"finished remove_area")

    @RPC.export
    def get_areas(self):
        return self.areas

    def get_topic_data_from_historian(self, topic):
        _log.info(f"in get_topic_data_from_historian with topic: {topic}")
        try:
            data = self.vip.rpc.call(
                'platform.historian',
                'query',
                topic=topic,
                count=10,  # Maximum number of data points to return
                order="LAST_TO_FIRST"
            ).get(timeout=10)  # timeout in seconds

            if data:
                _log.info(f"Received data: {data}")
            else:
                _log.info("No data received for the given time period.")
            return data

        except Exception as e:
            _log.info(f"Failed to fetch data: {str(e)}")

    @RPC.export
    def get_summary(self):
        summary = self.areas.copy()

        for config_name, config in summary.items():
            for endpoint_type, endpoints in config.get("endpoints").items():
                for idx, endpoint in enumerate(endpoints):
                    data = self.get_topic_data_from_historian(endpoint)
                    summary[config_name]["endpoints"][endpoint_type][idx] = {"endpoint": endpoint, "values": data}

        return summary

    @RPC.export
    def endpoints(self):
        res = defaultdict(dict)

        for endpoint_type, endpoints in self.endpoints.items():
            for endpoint in endpoints:
                res[endpoint_type][endpoint] = list(self.endpoints[endpoint_type][endpoint])

        return res


    def start_control_loop(self):
        try:
            headers = {"from": self.core.identity}
            for area_name, config in self.areas.items():
                msg = {"area": area_name, "endpoints": config.get("endpoints")}

                _log.info(f"before self.vip.pubsub.publish('pubsub', 'agent/ofc_generic_control_algorithm', {headers}, {msg})")
                if not msg:
                    _log.error(f"No control loop msg for {area_name} with config {config}")
                self.vip.pubsub.publish('pubsub', "agent/ofc_generic_control_algorithm", headers, msg)
                _log.info(f"after self.vip.pubsub.publish('pubsub', 'agent/ofc_generic_control_algorithm', {headers}, {msg})")
        except Exception as e:
            _log.error(f"error in start_control_loop: {e}")

    def schedule_and_actuate(self, endpoint, value):
        result = {}
        try:
            _log.info(f"Trying to schedule actuation for: {endpoint}")
            self.counter += 1
            _now = get_aware_utc_now()
            str_now = format_timestamp(_now)
            str_end = format_timestamp(_now + timedelta(seconds=10))
            schedule_request = [[endpoint, str_now, str_end]]
            _log.info(f"schedule_request: {schedule_request}")
            task_name = f"{_now}: {endpoint} {value}"
            result = self.vip.rpc.call(
                'platform.actuator', 'request_new_schedule', self.core.identity, task_name,
                'HIGH', schedule_request).get(
                timeout=4)
            _log.info(f"result: {result}")
        except Exception as e:
            _log.info(f"Error trying to schedule actuation for {endpoint}: {e}")

        try:
            if result.get("result") != "SUCCESS":
                _log.info(f"result was not success.  pass")

            _log.info(
                f"prior to self.vip.rpc.call('platform.actuator', 'set_point', {self.core.identity}, {endpoint}, {value})")
            result = self.vip.rpc.call('platform.actuator', 'set_point', self.core.identity, endpoint, value).get(timeout=4)
            _log.info(f"result: {result}")

        except Exception as e:
            _log.info(f"Error in trying to actuate {endpoint}: {e}")


    @RPC.export
    def do_control(self, area_name, light_level, facade_state):
        _log.info(f"Entered do_control with area: {area_name} light_level: {light_level} facade_state: {facade_state}")
        area = self.areas.get(area_name)
        if not area:
            _log.error(f"Error {area_name} not in areas: {self.areas.keys()}")
            return
        endpoints = area.get("endpoints")
        if not endpoints:
            _log.error(f"Error {area_name} missing endpoints")
            return

        for light_level_endpoint in endpoints.get("Light"):
            self.schedule_and_actuate(light_level_endpoint, light_level)
        for facade_state_endpoint in endpoints.get("Façade State"):
            self.schedule_and_actuate(facade_state_endpoint, facade_state)
        _log.info(f"finished do_control")

def main():
    """Main method called to start the agent."""
    utils.vip_main(ofc_controller,
                   version=__version__)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
