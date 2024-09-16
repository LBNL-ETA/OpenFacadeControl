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

from platform_driver.interfaces.ofc_generic_driver_base import OFCGenericInterface, OFCGenericRegister
import logging
import requests
import random
import csv

_log = logging.getLogger(__name__)

type_mapping = {"string": str,
                "int": int,
                "integer": int,
                "float": float,
                "bool": bool,
                "boolean": bool}

def get_enlighted(host, device_id, api_key):
    url = '{}/ems/api/org/fixture/v1/op/dim/abs'.format(host)

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
        value = response.get("state")
        return value
    except Exception as e:
        _log.error(f"Error attempting to get Enlighted facade host: {host} device id: {device_id} error: {e}")

def post_enlighted(host, device_id, val):
    url = f"{host}/ems/api/org/fixture/v1/op/dim/abs"
    content = {"state": val}

    _log.info('Sending url={}\n\tjson = {}'.format(url, content))

    response = requests.post(url=url, json=content, verify=False)
    _log.info("Got response: {response}")


class Interface(OFCGenericInterface):
    def __init__(self, **kwargs):
        super(Interface, self).__init__(**kwargs)

        self.host_name = None
        self.api_key = None

    def configure(self, config_dict, registry_config_str):
        _log.info("config_dict:\t {v}\n".format(v=config_dict))
        _log.info("registry_config_str:\t {v}\n".format(v=registry_config_str))

        self.host_name = config_dict.get("host_name")
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
            if not default_value:
                default_value = None
            type_name = register_config.get("Type", 'string').lower()
            reg_type = type_mapping.get(type_name, str)
            register_id = register_config.get('id')

            def get_request_function():
                return get_enlighted(host=self.host_name, device_id=register_id, api_key=None)

            def post_request_function(val):
                return post_enlighted(host=self.host_name, device_id=register_id, val=val)

            csv_path = register_config.get("csv")
            csv_column = register_config.get("csv column")

            get_function = get_request_function

            if csv_path is not None:
                get_function = get_function = lambda: self.simulated_get_request_function(csv_path, csv_column)


            register = OFCGenericRegister(
                read_only=read_only,
                point_name=point_name,
                units=units,
                reg_type=reg_type,
                get_request_function=get_function,
                post_request_function=post_request_function,
                default_value=default_value,
                description=description)

            if default_value is not None:
                self.set_default(point_name, register.value)

            self.insert_register(register)
