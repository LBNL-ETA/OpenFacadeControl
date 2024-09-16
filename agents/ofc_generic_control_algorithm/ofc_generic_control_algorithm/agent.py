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
import datetime
# Volttron
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core, RPC, PubSub
from volttron.platform.messaging import headers as headers_mod


utils.setup_logging()
_log = logging.getLogger(__name__)

__version__ = "0.1"

def ofc_generic_control_algorithm(config_path, **kwargs):
    """
    Load configuration from the given config path and instantiate an OFCGenericControlAlgorithm agent.

    :param config_path: Path to the configuration file.
    :param kwargs: Additional keyword arguments passed to the agent.
    :return: Instance of OFCGenericControlAlgorithm agent.
    """
    try:
        config = utils.load_config(config_path)
    except Exception as e:
        config = {}

    if not config:
        _log.info("Using Agent defaults for starting configuration.")

    return OFCGenericControlAlgorithm(config, **kwargs)


class OFCGenericControlAlgorithm(Agent):
    """
    Generic control algorithm agent for handling input data from various sources
    and calculating the desired control states for lighting and façade management.

    Attributes:
        control_inputs (list): List of control input types (e.g., Occupancy, Glare).
        control_outputs (list): List of control output types (e.g., Light, Façade State).
        config (dict): Agent configuration settings.
        control_ct (int): Counter for tracking control actions.
        counter (int): General-purpose counter for operations.
        algorithm_params (dict): Parameters defining the control algorithm logic.
    """

    def __init__(self, config, **kwargs):
        """
        Initialize the OFCGenericControlAlgorithm agent with the given configuration.

        :param config: Dictionary containing configuration values for the agent.
        :param kwargs: Additional keyword arguments.
        """
        super(OFCGenericControlAlgorithm, self).__init__(**kwargs)
        self.control_inputs = ["Occupancy", "Glare", "Illuminance", "Solar Radiation"]
        self.control_outputs = ["Light", "Façade State"]
        self.config = config
        self.control_ct = 0
        self.counter = 0
        self.vip.config.subscribe(self.configure, actions=["NEW", "UPDATE"], pattern="config")

    @Core.receiver('onstart')
    def onstart(self, sender, **kwargs):
        """
        Core receiver that is triggered when the agent starts. Placeholder for future startup actions.

        :param sender: The source of the event.
        :param kwargs: Additional arguments.
        """
        pass

    def configure(self, config_name, action, contents):
        """
        Handles configuration updates for the agent, setting up algorithm parameters.

        :param config_name: Name of the configuration file.
        :param action: The type of action (e.g., "NEW", "UPDATE").
        :param contents: The contents of the updated configuration.
        """
        _log.info(f"In configure with config_name: {config_name} action: {action}, contents: {contents}")
        self.algorithm_params = contents

    def get_topic_data_from_historian(self, topic):
        """
        Fetch historical data for a given topic from the platform historian.

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

    def get_all_input_data(self, inputs):
        """
        Fetches all input data for the given inputs (topics).

        :param inputs: A dictionary mapping input types to a list of topics.
        :return: A dictionary with the collected data for each input type.
        """
        result = {input_type: {topic: [] for topic in topics} for input_type, topics in inputs.items()}

        for input_type, list_of_topics in inputs.items():
            for topic in list_of_topics:
                data = self.get_topic_data_from_historian(topic)
                if data:
                    result[input_type][topic] = data.get("values")

        return result

    def process_input_data(self, input_data):
        """
        Process and calculate the average values for each input type.

        :param input_data: The input data collected for different types.
        :return: A dictionary with the average value for each input type.
        """
        _log.info(f"In process_input_data with input_data: {input_data}")
        averages = {}
        for input_type, input_type_data_all in input_data.items():
            # Collect all values from lists under the current category
            all_values = [value[1] for item_list in input_type_data_all.values() for value in item_list]
            all_values = [x for x in all_values if x is not None]
            if len(all_values) > 0:
                averages[input_type] = sum(all_values) / len(all_values)
            else:
                averages[input_type] = 0  # Default to 0 if no valid data
        return averages

    def calculate_state(self, input_data):
        """
        Calculate the output control states based on input data and algorithm configuration.

        :param input_data: The average input data for each input type.
        :return: A dictionary with the desired states for the outputs (Light, Façade State).
        """
        states = {"Light": {"value": 0.1, "reason": "Default"}, "Façade State": {"value": 0, "reason": "Default"}}

        for config in self.algorithm_params:
            conditions_met = True
            conditions = ""
            for inputs in config.get("Inputs", []):
                input_type = inputs.get("Type")
                threshold = inputs.get("Threshold")
                if input_type in input_data:
                    input_value = input_data.get(input_type)
                    if input_value < threshold:
                        conditions_met = False
                        break
                    else:
                        condition_str = f"{input_type}: {input_value} >= {threshold}"
                        if len(conditions) == 0:
                            conditions = condition_str
                        else:
                            conditions += ", " + condition_str

                if not conditions_met:
                    break
            if conditions_met:
                outputs = config.get("Outputs", [])
                for output in outputs:
                    states[output.get("Type")]["value"] = output.get("Setting")
                    states[output.get("Type")]["reason"] = conditions

        return states

    @PubSub.subscribe('pubsub', "agent/ofc_generic_control_algorithm")
    def _handle_area_control_request(self, peer, sender, bus, topic, headers, message):
        """
        Handle incoming control requests and calculate the control states for the specified area.

        :param peer: The peer that sent the message.
        :param sender: The sender of the message.
        :param bus: The message bus.
        :param topic: The topic of the message.
        :param headers: Headers associated with the message.
        :param message: The message payload.
        """
        _log.info(f"_handle_area_control_request message: {message}")
        area = message.get("area")
        endpoints = message.get("endpoints")
        input_data = self.get_all_input_data(endpoints)
        _log.info(f"Input data after get_all_input_data: {input_data}")
        input_data = self.process_input_data(input_data)
        _log.info(f"Input data after process_input_data: {input_data}")
        states = self.calculate_state(input_data)
        _log.info(f"Calculated states: {states}")

        # Prepare to publish the results
        topic = "analysis/ofc_analysis/{id}".format(id=self.core.identity)
        now = utils.format_timestamp(datetime.datetime.utcnow())
        headers = {
            "from": self.core.identity,
            headers_mod.DATE: now,
            headers_mod.TIMESTAMP: now
        }

        light_level = states["Light"]["value"]
        light_level_reason = states["Light"]["reason"]
        facade_state = states["Façade State"]["value"]
        facade_state_reason = states["Façade State"]["reason"]

        msg = {
            "area": area,
            "action": f"Set light level: {light_level}, Façade state: {facade_state}",
            "reason": f"Light level reason: {light_level_reason}, Façade state reason: {facade_state_reason}"
        }

        # Publish the results and invoke RPC to control the area
        _log.info(f"Publishing control message: {msg}")
        self.vip.pubsub.publish('pubsub', topic, headers, msg)
        _log.info(f"Calling RPC method do_control on sender {sender}")
        self.vip.rpc(sender, "do_control", area, light_level, facade_state)


def main():
    """
    Main method called to start the agent.
    """
    utils.vip_main(ofc_generic_control_algorithm, version=__version__)


if __name__ == '__main__':
    # Entry point for the script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
