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

    """
    try:
        config = utils.load_config(config_path)
    except Exception as e:
        config = {}

    if not config:
        _log.info("Using Agent defaults for starting configuration.")

    return OFCGenericControlAlgorithm(config, **kwargs)


class OFCGenericControlAlgorithm(Agent):
    def __init__(self, config, **kwargs):
        super(OFCGenericControlAlgorithm, self).__init__(**kwargs)
        self.control_inputs = ["Occupancy", "Glare", "Illuminance", "Solar Radiation"]
        self.control_outputs = ["Light", "Façade State"]
        self.config = config
        self.control_ct = 0
        self.counter = 0
        self.vip.config.subscribe(self.configure, actions=["NEW", "UPDATE"], pattern="config")

    @Core.receiver('onstart')
    def onstart(self, sender, **kwargs):
        pass

    def configure(self, config_name, action, contents):
        _log.info(f"in configure with config_name: {config_name} action:{action}, contents: {contents}")

        self.algorithm_params = contents

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

    def get_all_input_data(self, inputs):
        result = {input_type: {topic: [] for topic in topics} for input_type, topics in inputs.items()}

        for input_type, list_of_topics in inputs.items():
            for topic in list_of_topics:
                data = self.get_topic_data_from_historian(topic)
                if data:
                    result[input_type][topic] = data.get("values")

        return result

    def process_input_data(self, input_data):
        _log.info(f"in process_input_data with input_data: {input_data}")
        averages = {}
        for input_type, input_type_data_all in input_data.items():
            # Collect all numbers from all lists under the current category
            all_values = [value[1] for item_list in input_type_data_all.values() for value in item_list]
            all_values = [x for x in all_values if x is not None]
            if len(all_values) > 0:  # To avoid division by zero
                averages[input_type] = sum(all_values) / len(all_values)
            else:
                averages[input_type] = 0  # or you might choose to return None or omit the category
        return averages

    def calculate_state(self, input_data):
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
        # When a control request signal is received calculate a new state and call the sender's do_control RPC
        # method with the result
        _log.info(f"_handle_area_control_request message: {message}")
        area = message.get("area")
        endpoints = message.get("endpoints")
        input_data = self.get_all_input_data(endpoints)
        _log.info(f"input_data after get_all_input_data: {input_data}")
        input_data = self.process_input_data(input_data)
        _log.info(f"input_data after process_input_data: {input_data}")
        states = self.calculate_state(input_data)
        _log.info(f"states: {states}")

        topic = "analysis/ofc_analysis/{id}".format(id=self.core.identity)

        now = utils.format_timestamp(datetime.datetime.utcnow())

        headers = {"from": self.core.identity,
                   headers_mod.DATE: now,
                   headers_mod.TIMESTAMP: now
                   }

        light_level = states["Light"]["value"]
        light_level_reason = states["Light"]["reason"]
        facade_state = states["Façade State"]["value"]
        facade_state_reason = states["Façade State"]["reason"]

        msg = {"area": area, "action": f"Set light level: {light_level} facade state: {facade_state}",
               "reason": f"Light level reason: {light_level_reason}, Facade state reason: {facade_state_reason}"}

        _log.info(f"Before self.vip.pubsub.publish('pubsub', {topic}, {headers}, {msg})")
        self.vip.pubsub.publish('pubsub', topic, headers, msg)
        _log.info(f"Before self.vip.rpc({sender}, 'do_control', {area}, {light_level}, {facade_state})")
        self.vip.rpc(sender, "do_control", area, light_level, facade_state)


def main():
    """Main method called to start the agent."""
    utils.vip_main(ofc_generic_control_algorithm,
                   version=__version__)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
