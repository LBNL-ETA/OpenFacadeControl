from platform_driver.interfaces.ofc_generic_driver_base import OFCGenericInterface, OFCGenericRegister
import logging
import requests
import random

_log = logging.getLogger(__name__)

type_mapping = {"string": str,
                "int": int,
                "integer": int,
                "float": float,
                "bool": bool,
                "boolean": bool}

def post_cree(host, device_id, api_key, val):
    url = "{}/smartcast-api/v1/spaces/{}/actuator".format(host, device_id)
    setpoint = int(float(val) * 100)
    content = {'light_level': setpoint}

    headers = {
        'accept': 'application/json',
        'APPID': str(device_id),
        'APIKEY': str(api_key),
        'content-type': 'application/json'
    }

    _log.info('Sending url {}\n\theaders = {}\n\tjson = {}'.format(url, headers, content))

    try:
        response = requests.post(url=url, headers=headers, json=content, verify=False)
        _log.info("Got response: {response}")
    except Exception as e:
        _log.error(f"Error attempting to set Cree light host: {host} device id: {device_id} error: {e}")

def get_cree(host, device_id, api_key):
    url = "{}/smartcast-api/v1/spaces/{}/actuator".format(host, device_id)

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
        value = response.get("light_level")
        return value
    except Exception as e:
        _log.error(f"Error attempting to get Cree light host: {host} device id: {device_id} error: {e}")


class Interface(OFCGenericInterface):
    def __init__(self, **kwargs):
        super(Interface, self).__init__(**kwargs)

        self.host_name = None
        self.api_key = None

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

        for register_config in registers:
            if not register_config['Point Name']:
                return

            read_only = register_config['Writable'].lower() != 'true'
            point_name = register_config['Volttron Point Name']
            description = register_config.get('Notes', '')
            units = register_config['Units']
            default_value = register_config.get("Starting Value", 1)
            type_name = register_config.get("Type", 'string').lower()
            reg_type = type_mapping.get(type_name, str)
            register_id = register_config.get('id')

            def get_request_function():
                return get_cree(host=self.host_name, device_id=register_id, api_key=self.api_key)

            def post_request_function(val):
                return post_cree(host=self.host_name, device_id=register_id, api_key=self.api_key, val=val)

            register = OFCGenericRegister(
                read_only=read_only,
                point_name=point_name,
                units=units,
                reg_type=reg_type,
                get_request_function=get_request_function,
                post_request_function=post_request_function,
                default_value=default_value,
                description=description)

            if default_value is not None:
                self.set_default(point_name, register.value)

            self.insert_register(register)
