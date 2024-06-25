from platform_driver.interfaces.ofc_generic_driver_base import OFCGenericInterface, OFCGenericRegister
import logging
import csv
import requests
import random

_log = logging.getLogger(__name__)

type_mapping = {"string": str,
                "int": int,
                "integer": int,
                "float": float,
                "bool": bool,
                "boolean": bool}

def get_hunter_douglas(host, device_id, api_key):
    url = '{}/api/shade/{}'.format(host, device_id)

    headers = {
        'accept': 'application/json',
        'APPID': str(device_id),
        'APIKEY': str(api_key),
        'content-type': 'application/json'
    }

    _log.info(f"Making get request to: {url}")

    try:
        response = requests.get(url=url, headers=headers)
        _log.debug(f"Got response {response}")
        response = response.json()
        value = response.get("value")
        return value
    except Exception as e:
        _log.error(f"Error attempting to get Hunter Douglas illuminance host: {host} device id: {device_id} error: {e}")


class Interface(OFCGenericInterface):
    def __init__(self, **kwargs):
        super(Interface, self).__init__(**kwargs)
        self.host_name = None

    def configure(self, config_dict, registry_config_str):
        _log.info("config_dict:\t {v}\n".format(v=config_dict))
        _log.info("registry_config_str:\t {v}\n".format(v=registry_config_str))
        self.host_name = config_dict.get("host_name")
        self.api_key = config_dict.get("api_key")
        self.parse_registers(registry_config_str)
        self.post_config()

    def parse_registers(self, registers):
        _log.info(f"in parse_registers with registers:{registers}")
        if not registers:
            raise RuntimeError(f"Missing registers for {self.host_name}")
        # Skip lines that have no address yet.
        for register_config in registers:
            # Skip lines that have no address yet.
            if not register_config['Point Name']:
                continue

            read_only = register_config['Writable'].lower() != 'true'
            point_name = register_config['Volttron Point Name']
            description = register_config.get('Notes', '')
            units = register_config['Units']
            default_value = register_config.get("Starting Value", 42)
            if not default_value:
                default_value = None
            type_name = register_config.get("Type", 'string')
            reg_type = type_mapping.get(type_name, str)
            register_id = register_config.get('id')

            def get_request_function():
                return get_hunter_douglas(host=self.host_name, device_id=register_id, api_key=None)

            register = OFCGenericRegister(
                read_only=read_only,
                point_name=point_name,
                units=units,
                reg_type=reg_type,
                get_request_function=get_request_function,
                post_request_function=None,
                default_value=default_value,
                description=description)

            if default_value is not None:
                self.set_default(point_name, register.value)

            self.insert_register(register)
