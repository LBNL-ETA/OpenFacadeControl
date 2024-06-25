import logging
import os, os.path
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

    """

    def __init__(self, config_path, **kwargs):
        super(OFCWebAgent, self).__init__(enable_web=True,
                                          **kwargs)
        self.vip.config.subscribe(self.configure, actions=["NEW", "UPDATE"], pattern="config")

    def configure(self, config_name, action, contents):
        _log.info(f"in configure with config_name: {config_name} action:{action}, contents: {contents}")

    @Core.receiver("onstart")
    def onstart(self, sender, **kwargs):
        _log.info(f"in onstart with sender: {sender} kwargs:{kwargs}")
        self.vip.web.register_path("/ofc_ui", os.path.join(WEBROOT))

    @RPC.export
    def hello(self):
        return "hello"

    @RPC.export
    def controller_endpoint(self, env, data):
        """
        The default response is application/json so our endpoint returns appropriately
        with a json based response.
        """
        _log.info(f"in controller_endpoint with env: {env} kwargs:{data}")
        result = self.vip.rpc.call(
            'ofs.area_controller', 'endpoints').get(
            timeout=4)

        # Note we aren't using a valid json request to get the following output
        # id will need to be grabbed from data etc
        return jsonrpc.json_result("controller", result)

    def get_ofc_agents(self):
        agent_list = self.vip.rpc.call(
            'control',
            'list_agents'
        ).get(timeout=4)

        ofc_agents = []

        for agent in agent_list:
            identity = agent.get("identity")
            if identity and len(identity) > 4 and identity[:4] == "ofc.":
                ofc_agents.append(identity)

        return ofc_agents


    @RPC.export
    def areas(self, path: Optional[str] = None, *args, **kwargs):
        _log.info(f"in areas with path {path} args: {args} kwargs:{kwargs}")
        try:
            if not path:
                ofc_agents = self.get_ofc_agents()
                area_controllers = [x for x in ofc_agents if ".controller." in x]
                controller_configs = {}
                for controller in area_controllers:
                    config = self.config_files(controller, "config")
                    controller_configs[controller] = config
                paths = []
                paths = [v.get("Area") for _, v in controller_configs.items()]
                return paths
            if path == "schema":
                schema_file_path = os.path.join(WEBROOT, "ofc_ui", "schemas", "ofc_area_controller_schema.json")  # "/home/ubuntu/PycharmProjects/volttron/configs/schemas/ofc_area_controller_schema.json"
                with open(schema_file_path) as f:
                    contents = f.read()
                    contents = json.loads(contents)
                    return contents

            contents = self.config_files(path, "config")
            return contents
        except Exception as e:
            print("Error: {e}".format(e=e))

    def test_add_device(self):
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
            # Make an RPC call to store the configuration data
            result = self.vip.rpc.call('config.store', 'manage_store',
                                       'platform.driver',
                                       'devices/LBNL/71T/test_room/dynamic_cree_light',
                                       config_data).get(timeout=10)
            _log.info("Config stored successfully: {}".format(result))
        except Exception as e:
            _log.info("Error storing config: {}".format(e))

    @RPC.export
    def control_algorithms(self, path: Optional[str] = None, *args, **kwargs):
        _log.info(f"in control_algorithms with path {path} args: {args} kwargs:{kwargs}")

        if not path:
            ofc_agents = self.get_ofc_agents()
            controller_algorithms = [x for x in ofc_agents if ".control_algorithm." in x]
            return controller_algorithms

        if path == "schema":
            schema_file_path = os.path.join(WEBROOT, "ofc_ui", "schemas", "ofc_control_algorithm_schema.json")
            with open(schema_file_path) as f:
                contents = f.read()
                contents = json.loads(contents)
                return contents

        contents = self.config_files(path, "config")
        return contents


    @RPC.export
    def config_files(self, agent: Optional[str] = "platform.driver",  path: Optional[str] = None, *args, **kwargs):
        _log.info(f"in config_files with path {path} args: {args} kwargs:{kwargs}")
        if not path:
            try:
                # RPC call to list configurations
                configs = self.vip.rpc.call(
                    'config.store',
                    'manage_list_configs',
                    agent
                ).get(timeout=4)
                configs = [x for x in configs if x.startswith("devices/")]
                return configs
            except Exception as e:
                print(f"Failed to list configurations: {e}")

        if path == "schema":
            schema_file_path = os.path.join(WEBROOT, "ofc_ui", "schemas", "ofc_component_schema.json")
            with open(schema_file_path) as f:
                contents = f.read()
                contents = json.loads(contents)
                return contents

        try:
            configs = self.vip.rpc.call(
                'config.store',
                'manage_get',
                agent,
                path
            ).get(timeout=4)
            configs = json.loads(configs)
            return configs
        except Exception as e:
            print(f"Failed to list configurations: {e}")

    @RPC.export
    def topics_endpoint(self, *args, **kwargs):
        _log.info(f"in topics_endpoint with args: {args} kwargs:{kwargs}")
        result = self.vip.rpc.call(
            'platform.historian', 'get_topic_list').get(
            timeout=4)

        result = [r for r in result if len(r) < 12 or (len(r) >= 12 and r[:12] != "ofc_analysis")]

        return result

    def get_topic_data_from_historian(self, topic):
        _log.info(f"in get_topic_data_from_historian with topic: {topic}")
        try:
            data = self.vip.rpc.call(
                'platform.historian',
                'query',
                topic=topic,
                count=20,  # Maximum number of data points to return
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
    def algorithm_output_topics_endpoint(self, path: Optional[str] = None, *args, **kwargs):
        _log.info(f"in algorithm_output_topics_endpoint with path {path} args: {args} kwargs:{kwargs}")
        if not path:
            try:
                result = self.vip.rpc.call(
                    'platform.historian', 'get_topic_list').get(
                    timeout=4)
            except Exception as e:
                _log.info(f"Failed to fetch data: {str(e)}")

            result = [r for r in result if len(r) > 12 and r[:12] == "ofc_analysis"]

            result = [r[:r.rfind("/")] for r in result]
            result = list(set(result))
            return result

        path = path[1:]
        action_topic = f"{path}/action"
        reason_topic = f"{path}/reason"

        action_data = self.get_topic_data_from_historian(action_topic)
        reason_data = self.get_topic_data_from_historian(reason_topic)

        action_data = action_data.get("values")
        reason_data = reason_data.get("values")

        action_data = {ts: v for ts, v in action_data}
        reason_data = {ts: v for ts, v in reason_data}

        all_timestamps = set(action_data.keys()).union(set(reason_data.keys()))

        # Create the merged list
        merged_list = []
        for timestamp in sorted(all_timestamps):
            action = action_data.get(timestamp)  # Returns None if the timestamp is not found
            reason = reason_data.get(timestamp)  # Returns None if the timestamp is not found
            merged_list.append({"timestamp": timestamp, "action": action, "reason": reason})

        return merged_list


def main():
    utils.vip_main(OFCWebAgent)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
