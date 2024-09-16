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
from flask import Flask, request, jsonify
import threading

# Volttron
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core, RPC

utils.setup_logging()
_log = logging.getLogger(__name__)

__version__ = "0.1"


def create_read_only_server(simulated_values, port, url):
    """
    Create a read-only Flask server that simulates returning values for a specific endpoint.

    :param simulated_values: A list of tuples with simulated (timestamp, value) data.
    :param port: Port number to run the server on.
    :param url: URL route for fetching simulated data.
    """
    app = Flask(f"OFC Simulation Server {port}")
    simulated_values_index = 0

    def get_point():
        """
        Return the next simulated value and timestamp.
        """
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
    """
    Create a read-write Flask server that allows retrieving and updating a value.

    :param port: Port number to run the server on.
    :param url: URL route for accessing the value.
    :param value_field: The field name to retrieve or update.
    :param default_value: Default value for the field if not set.
    """
    app = Flask(f"OFC Simulation Server {port}")
    value = default_value

    def get_value():
        """
        Return the current value.
        """
        return {value_field: value}

    def set_value():
        """
        Update the value based on a POST request containing JSON data.
        """
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
    """
    Create a server (either read-only or read-write) in a separate thread.

    :param endpoint: The URL endpoint to handle.
    :param port: The port number for the server.
    :param api_key: An optional API key for authentication (currently not used).
    :param server_type: Type of server to create (either read-only or read-write).
    :param value_field: Field name for the value (for read-write servers).
    :param simulated_values: Simulated data for read-only servers.
    :return: A threading.Thread object for the server.
    """
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
    Load configuration from the given config path and instantiate an OFCSimulationServerManager agent.

    :param config_path: Path to the configuration file.
    :param kwargs: Additional keyword arguments passed to the agent.
    :return: Instance of OFCSimulationServerManager agent.
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
    Manages the simulation servers for the OFC (Occupancy, Façade, and Control) system.

    This agent handles server creation, configuration, and control, allowing dynamic creation
    of read-only and read-write servers based on agent configuration.

    Attributes:
        server_threads (dict): Dictionary mapping server configuration names to threads.
        config (dict): The agent's configuration settings.
    """

    def __init__(self, config, **kwargs):
        """
        Initialize the OFCSimulationServerManager agent.

        :param config: Dictionary containing configuration values for the agent.
        :param kwargs: Additional keyword arguments.
        """
        super(OFCSimulationServerManager, self).__init__(**kwargs)
        self.server_threads = {}

        _log.info(f"In __init__ with config: {config} kwargs:{kwargs}")
        self.config = config
        self.vip.config.subscribe(self.configure, actions=["NEW", "UPDATE"], pattern="config")
        self.vip.config.subscribe(self.add_server, actions=["NEW", "UPDATE"], pattern="servers/*")
        self.vip.config.subscribe(self.remove_server, actions="DELETE", pattern="servers/*")

    def fetch_all_configs(self):
        """
        Fetch all configurations from the configuration store.

        :return: A dictionary of all configuration data.
        """
        config_list = self.vip.rpc.call('config.store', 'manage_list_configs', self.core.identity).get(timeout=4)
        configs = {}
        for config in config_list:
            configs[config] = self.fetch_config(config)
        return configs

    def fetch_config(self, config_name):
        """
        Fetch a specific configuration by name from the configuration store.

        :param config_name: Name of the configuration to fetch.
        :return: The configuration data.
        """
        try:
            config = self.vip.rpc.call('config.store', 'manage_get', self.core.identity, config_name).get(timeout=4)
            _log.info(f"Config {config_name}: {config}")
            return config
        except Exception as e:
            _log.error(f"Error fetching config {config_name}: {e}")

    @Core.receiver('onstart')
    def onstart(self, sender, **kwargs):
        """
        Called when the agent starts.

        :param sender: The sender of the onstart event.
        :param kwargs: Additional arguments.
        """
        _log.info(f"In onstart self.config: {self.config} sender: {sender} kwargs: {kwargs}")
        _log.info(f"Finished onstart self.config: {self.config} sender: {sender} kwargs: {kwargs}")

    def configure(self, config_name, action, contents):
        """
        Handle configuration updates.

        :param config_name: Name of the configuration being updated.
        :param action: Action performed on the configuration (e.g., "NEW", "UPDATE").
        :param contents: The contents of the configuration.
        """
        pass

    def add_server(self, config_name, action, contents):
        """
        Add a new server based on the configuration provided.

        :param config_name: Name of the server configuration.
        :param action: Action performed on the server configuration (e.g., "NEW", "UPDATE").
        :param contents: The configuration details for the server.
        """
        _log.info(f"In add_server with config_name: {config_name} action:{action}, contents: {contents}")
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
        _log.info(f"Finished add_server")

    def remove_server(self, config_name, action, contents):
        """
        Remove an existing server.

        :param config_name: Name of the server configuration.
        :param action: Action performed on the server configuration ("DELETE").
        :param contents: The contents of the server configuration (not used).
        """
        _log.info(f"In remove_server with config_name: {config_name} action:{action}, contents: {contents}")
        existing_server = self.server_threads.get(config_name)
        if existing_server:
            existing_server.stop()
            del self.server_threads[config_name]
        _log.info(f"Finished remove_server")

    @RPC.export
    def reset_all_servers(self, *args, **kwargs):
        """
        Reset all servers (placeholder method).
        """
        pass

    @RPC.export
    def stop_server(self, server_config_name: str, *args, **kwargs):
        """
        Stop a specific server by name.

        :param server_config_name: The name of the server configuration to stop.
        :param args: Additional arguments.
        :param kwargs: Additional keyword arguments.
        """
        _log.info(f"In stop_server with server_config_name {server_config_name} args: {args} kwargs:{kwargs}")
        existing_server = self.server_threads.get(server_config_name)
        if existing_server:
            existing_server.stop()

    @RPC.export
    def reset_server(self, server_config_name: str, *args, **kwargs):
        """
        Reset a specific server by name by fetching the configuration and reconfiguring the server.

        :param server_config_name: The name of the server configuration to reset.
        :param args: Additional arguments.
        :param kwargs: Additional keyword arguments.
        """
        _log.info(f"In reset_server with server_config_name {server_config_name} args: {args} kwargs: {kwargs}")
        try:
            server_config = self.vip.config.get(config_name=server_config_name)
            self.configure(server_config_name, "UPDATE", server_config)
        except Exception as e:
            _log.error(f"Error resetting server {server_config_name}: {e}")


def main():
    """
    Main method called to start the agent.
    """
    utils.vip_main(ofc_simulation_server_manager, version=__version__)


if __name__ == '__main__':
    # Entry point for the script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
