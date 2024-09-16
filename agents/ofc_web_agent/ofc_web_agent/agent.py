import logging
import os
import sys
import json

from volttron.platform.vip.agent import Core, Agent, RPC
from volttron.platform.agent import utils
from volttron.platform import jsonrpc
from volttron.platform.agent.known_identities import (
    VOLTTRON_CENTRAL, VOLTTRON_CENTRAL_PLATFORM, CONTROL, CONFIGURATION_STORE, PLATFORM)
from typing import Optional

utils.setup_logging()
_log = logging.getLogger(__name__)
__version__ = '0.1'

MY_PATH = os.path.dirname(__file__)
WEBROOT = os.path.join(MY_PATH, "webroot")


class OFCWebAgent(Agent):
    """
    OFCWebAgent is an agent that provides a web interface for controlling
    and retrieving data related to the OFC (Occupancy, Façade, and Control) system.

    Attributes:
        config_path: Path to the agent configuration file.
    """

    def __init__(self, config_path, **kwargs):
        """
        Initialize the OFCWebAgent with the provided configuration.

        :param config_path: Path to the configuration file.
        :param kwargs: Additional keyword arguments.
        """
        super(OFCWebAgent, self).__init__(enable_web=True, **kwargs)
        self.vip.config.subscribe(self.configure, actions=["NEW", "UPDATE"], pattern="config")

    def configure(self, config_name, action, contents):
        """
        Handle configuration updates.

        :param config_name: Name of the configuration file.
        :param action: Action performed on the configuration (e.g., "NEW", "UPDATE").
        :param contents: The contents of the configuration.
        """
        _log.info(f"in configure with config_name: {config_name} action:{action}, contents: {contents}")

    @Core.receiver("onstart")
    def onstart(self, sender, **kwargs):
        """
        Called when the agent starts. Registers the web interface path.

        :param sender: The sender of the onstart event.
        :param kwargs: Additional arguments.
        """
        _log.info(f"in onstart with sender: {sender} kwargs:{kwargs}")
        self.vip.web.register_path("/ofc_ui", os.path.join(WEBROOT))

    @RPC.export
    def hello(self):
        """
        Simple RPC method that returns a greeting message.

        :return: A greeting message ("hello").
        """
        return "hello"

    @RPC.export
    def controller_endpoint(self, env, data):
        """
        RPC method for returning controller data.

        :param env: Environment variables.
        :param data: Data provided with the request.
        :return: JSON response with controller data.
        """
        _log.info(f"in controller_endpoint with env: {env} kwargs:{data}")
        result = self.vip.rpc.call(
            'ofs.area_controller', 'endpoints').get(timeout=4)
        return jsonrpc.json_result("controller", result)

    def get_ofc_agents(self):
        """
        Retrieves a list of OFC agents.

        :return: List of OFC agent identities.
        """
        agent_list = self.vip.rpc.call(
            'control', 'list_agents').get(timeout=4)

        ofc_agents = [agent.get("identity") for agent in agent_list if
                      agent.get("identity") and agent.get("identity").startswith("ofc.")]
        return ofc_agents

    @RPC.export
    def areas(self, path: Optional[str] = None, *args, **kwargs):
        """
        RPC method to retrieve area configurations or schema.

        :param path: The path for the area (or "schema" to return the schema).
        :param args: Additional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A list of areas or schema content.
        """
        _log.info(f"in areas with path {path} args: {args} kwargs:{kwargs}")
        try:
            if not path:
                ofc_agents = self.get_ofc_agents()
                area_controllers = [x for x in ofc_agents if ".controller." in x]
                controller_configs = {controller: self.config_files(controller, "config") for controller in
                                      area_controllers}
                return [v.get("Area") for _, v in controller_configs.items()]

            if path == "schema":
                schema_file_path = os.path.join(WEBROOT, "ofc_ui", "schemas", "ofc_area_controller_schema.json")
                with open(schema_file_path) as f:
                    contents = json.load(f)
                    return contents

            contents = self.config_files(path, "config")
            return contents
        except Exception as e:
            _log.error(f"Error in areas method: {e}")

    def test_add_device(self):
        """
        Adds a device configuration to the platform.

        :return: None
        """
        config_data = {
            "driver_config": {"host_name": "https://some_other_cree_occupancy_host", "manufacturer": "Cree",
                              "api_key": "33"},
            "registry_config": "config://cree_occupancy_registers.json",
            "interval": 10,
            "timezone": "US/Pacific",
            "heart_beat_point": "Heartbeat",
            "driver_type": "ofc_cree_occupancy_driver",
            "publish_breadth_first_all": False,
            "publish_depth_first": False,
            "publish_breadth_first": False,
            "campus": "LBNL",
            "building": "71T",
            "unit": "Cree occupancy A"
        }

        try:
            result = self.vip.rpc.call('config.store', 'manage_store',
                                       'platform.driver',
                                       'devices/LBNL/71T/test_room/dynamic_cree_light',
                                       config_data).get(timeout=10)
            _log.info(f"Config stored successfully: {result}")
        except Exception as e:
            _log.error(f"Error storing config: {e}")

    @RPC.export
    def control_algorithms(self, path: Optional[str] = None, *args, **kwargs):
        """
        RPC method to retrieve control algorithms or schema.

        :param path: The path for the algorithm (or "schema" to return the schema).
        :param args: Additional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A list of control algorithms or schema content.
        """
        _log.info(f"in control_algorithms with path {path} args: {args} kwargs:{kwargs}")

        if not path:
            ofc_agents = self.get_ofc_agents()
            return [x for x in ofc_agents if ".control_algorithm." in x]

        if path == "schema":
            schema_file_path = os.path.join(WEBROOT, "ofc_ui", "schemas", "ofc_control_algorithm_schema.json")
            with open(schema_file_path) as f:
                return json.load(f)

        return self.config_files(path, "config")

    @RPC.export
    def config_files(self, agent: Optional[str] = "platform.driver", path: Optional[str] = None, *args, **kwargs):
        """
        Retrieve configuration files for a given agent and path.

        :param agent: The agent to retrieve the configuration from.
        :param path: The path of the configuration.
        :param args: Additional arguments.
        :param kwargs: Additional keyword arguments.
        :return: List of configurations or specific configuration content.
        """
        _log.info(f"in config_files with path {path} args: {args} kwargs:{kwargs}")

        if not path:
            try:
                configs = self.vip.rpc.call('config.store', 'manage_list_configs', agent).get(timeout=4)
                return [x for x in configs if x.startswith("devices/")]
            except Exception as e:
                _log.error(f"Failed to list configurations: {e}")

        if path == "schema":
            schema_file_path = os.path.join(WEBROOT, "ofc_ui", "schemas", "ofc_component_schema.json")
            with open(schema_file_path) as f:
                return json.load(f)

        try:
            config_data = self.vip.rpc.call('config.store', 'manage_get', agent, path).get(timeout=4)
            return json.loads(config_data)
        except Exception as e:
            _log.error(f"Failed to retrieve configuration: {e}")

    @RPC.export
    def topics_endpoint(self, *args, **kwargs):
        """
        RPC method to retrieve the list of topics from the platform historian.

        :param args: Additional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A list of topics.
        """
        _log.info(f"in topics_endpoint with args: {args} kwargs:{kwargs}")
        result = self.vip.rpc.call('platform.historian', 'get_topic_list').get(timeout=4)
        return [r for r in result if not r.startswith("ofc_analysis")]

    def get_topic_data_from_historian(self, topic):
        """
        Retrieve historical data for a given topic.

        :param topic: The topic to query.
        :return: Data points for the specified topic.
        """
        _log.info(f"in get_topic_data_from_historian with topic: {topic}")
        try:
            data = self.vip.rpc.call('platform.historian', 'query', topic=topic, count=20, order="LAST_TO_FIRST").get(
                timeout=10)
            return data if data else _log.info("No data received.")
        except Exception as e:
            _log.error(f"Failed to fetch data: {e}")

    @RPC.export
    def algorithm_output_topics_endpoint(self, path: Optional[str] = None, *args, **kwargs):
        """
        RPC method to retrieve topics related to algorithm outputs.

        :param path: The path for the topic.
        :param args: Additional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A list of topics related to algorithm outputs.
        """
        _log.info(f"in algorithm_output_topics_endpoint with path {path} args: {args} kwargs:{kwargs}")
        if not path:
            try:
                result = self.vip.rpc.call('platform.historian', 'get_topic_list').get(timeout=4)
                return [r[:r.rfind("/")] for r in result if r.startswith("ofc_analysis")]
            except Exception as e:
                _log.error(f"Failed to retrieve algorithm output topics: {e}")

        action_topic = f"{path[1:]}/action"
        reason_topic = f"{path[1:]}/reason"

        action_data = self.get_topic_data_from_historian(action_topic)
        reason_data = self.get_topic_data_from_historian(reason_topic)

        action_values = {ts: v for ts, v in action_data.get("values")}
        reason_values = {ts: v for ts, v in reason_data.get("values")}

        all_timestamps = sorted(set(action_values.keys()).union(reason_values.keys()))

        return [{"timestamp": ts, "action": action_values.get(ts), "reason": reason_values.get(ts)} for ts in
                all_timestamps]


def main():
    """
    Main method called to start the agent.
    """
    utils.vip_main(OFCWebAgent)


if __name__ == '__main__':
    # Entry point for the script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
