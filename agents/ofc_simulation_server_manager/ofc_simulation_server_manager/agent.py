__docformat__ = 'reStructuredText'

import sys
import logging
from flask import Flask, request, jsonify
import threading

# Volttron
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core, RPC

utils.setup_logging()
_log = logging.getLogger(__name__)

__version__ = "0.1"


def create_read_only_server(simulated_values, port, url):
    app = Flask(f"OFC Simulation Server {port}")
    simulated_values_index = 0

    def get_point():
        nonlocal simulated_values_index
        timestamp, value = simulated_values[simulated_values_index]
        simulated_values_index += 1
        if simulated_values_index >= len(simulated_values):
            simulated_values_index = 0
        result = {"timestamp": timestamp, "value": value}
        return result

    app.add_url_rule(url, url, get_point)
    app.run(debug=False, port=port, use_reloader=False)


def create_read_write_server(port, url, value_field, default_value=-1):
    app = Flask(f"OFC Simulation Server {port}")
    value = default_value

    def get_value():
        return {value_field: value}

    def set_value():
        nonlocal value
        data = request.json
        new_value = data.get(value_field)
        if new_value:
            value = new_value
            return jsonify({"message": "value updated", "value": value})
        else:
            return jsonify({"message": "value not provided"}), 400

    # Dynamically add URL rule
    app.add_url_rule(url, 'get_value', get_value, methods=['GET'])
    app.add_url_rule(url, 'set_value', set_value, methods=['POST'])
    app.run(debug=False, port=port, use_reloader=False)

read_only_server_types = ["Occupancy", "Glare", "Illuminance", "Solar Radiation"]
read_write_server_types = ["Light", "Façade State"]


def create_server_in_thread(endpoint, port, api_key, server_type, value_field=None, simulated_values=None, **kwargs):
    t = None
    if server_type in read_only_server_types:
        if server_type in simulated_values:
            simulated_values = simulated_values[server_type]
        t = threading.Thread(target=create_read_only_server, args=(simulated_values, port, endpoint))
    elif server_type in read_write_server_types:
        t = threading.Thread(target=create_read_write_server, args=(port, endpoint, value_field))
    else:
        raise RuntimeError(f"Unsupported server type: {server_type}")

    return t

def ofc_simulation_server_manager(config_path, **kwargs):
    """

    """
    try:
        config = utils.load_config(config_path)
    except Exception as e:
        config = {}

    if not config:
        _log.info("Using Agent defaults for starting configuration.")

    return OFCSimulationServerManager(config, **kwargs)


class OFCSimulationServerManager(Agent):
    """

    """

    def __init__(self, config, **kwargs):
        super(OFCSimulationServerManager, self).__init__(**kwargs)

        self.server_threads = {}

        _log.info(f"in __init__ with config: {config} kwargs:{kwargs}")
        self.config = config
        self.vip.config.subscribe(self.configure, actions=["NEW", "UPDATE"], pattern="config")
        self.vip.config.subscribe(self.add_server, actions=["NEW", "UPDATE"], pattern="servers/*")
        self.vip.config.subscribe(self.remove_server, actions="DELETE", pattern="servers/*")

    def fetch_all_configs(self):
        config_list = self.vip.rpc.call('config.store', 'manage_list_configs', self.core.identity).get(timeout=4)
        configs = {}
        for config in config_list:
            configs[config] = self.fetch_config(config)

        return configs

    def fetch_config(self, config_name):
        try:
            config = self.vip.rpc.call('config.store', 'manage_get', self.core.identity, config_name).get(
                timeout=4)
            print(f"Config {config_name}: {config}")
            return config
        except Exception as e:
            _log.error(f"Error fetching config {config_name}: {e}")

    @Core.receiver('onstart')
    def onstart(self, sender, **kwargs):
        """

        """
        _log.info(f"in onstart self.config: {self.config} sender: {sender} kwargs: {kwargs}")
        _log.info(f"Finished onstart self.config: {self.config} sender: {sender} kwargs: {kwargs}")

    def configure(self, config_name, action, contents):
        pass

    def add_server(self, config_name, action, contents):
        _log.info(f"in add_server with config_name: {config_name} action:{action}, contents: {contents}")

        try:
            existing_server = self.server_threads.get(config_name)

            if existing_server:
                existing_server.stop()

            contents["server_type"] = contents["type"]
            t = create_server_in_thread(**contents)
            self.server_threads[config_name] = t
            self.server_threads[config_name].start()
        except Exception as e:
            _log.error(f"Error in add_server: {e}")

        _log.info(f"finished add_server")

    def remove_server(self, config_name, action, contents):
        _log.info(f"in remove_server with config_name: {config_name} action:{action}, contents: {contents}")

        existing_server = self.server_threads.get(config_name)
        if existing_server:
            existing_server.stop()
            del self.server_threads[config_name]

        _log.info(f"finished remove_server")

    @RPC.export
    def reset_all_servers(self, *args, **kwargs):
        pass

    @RPC.export
    def stop_server(self, server_config_name: str, *args, **kwargs):
        _log.info(f"in stop_server with server_config_name {server_config_name} args: {args} kwargs:{kwargs}")
        existing_server = self.server_threads.get(server_config_name)
        if existing_server:
            existing_server.stop()

    @RPC.export
    def reset_server(self, server_config_name: str, *args, **kwargs):
        _log.info(f"in reset_server with server_config_name {server_config_name} args: {args} kwargs:{kwargs}")
        try:
            server_config = self.vip.config.get(config_name=server_config_name)
            self.config(server_config_name, "UPDATE", server_config)
        except Exception as e:
            print("Error: {e}".format(e=e))


def main():
    """Main method called to start the agent."""
    utils.vip_main(ofc_simulation_server_manager,
                   version=__version__)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
