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


def get_zero_to_ten_volt():
    return getattr(get_zero_to_ten_volt, "value", -1)

def setet_zero_to_ten_volt(val):
    get_zero_to_ten_volt.value = val

class ZeroToTenVoltRegisterFake(BaseRegister):
    def __init__(self, read_only, pointName, units, reg_type,
                 default_value=None, description=''):
        #     register_type, read_only, pointName, units, description = ''):
        super(ZeroToTenVoltRegisterFake, self).__init__("byte", read_only, pointName, units,
                                           description='')
        self.reg_type = reg_type
        # python_type is used for the metedata returned.  It defaults to int
        self.python_type = reg_type

        if default_value is None:
            self.value = self.reg_type(random.uniform(0, 100))
        else:
            try:
                _log.info("reg_type: {r}, default value: {v}".format(r=self.reg_type, v=default_value))
                self.value = self.reg_type(default_value)
            except ValueError:
                self.value = self.reg_type()

class Interface(BasicRevert, BaseInterface):
    def __init__(self, **kwargs):
        super(Interface, self).__init__(**kwargs)

    def configure(self, config_dict, registry_config_str):
        with open("/tmp/zero_to_ten_volt.log", "w") as f:
            f.write("confic_dict:\t {v}\n".format(v=config_dict))
            f.write("registry_config_str:\t {v}\n".format(v=registry_config_str))
        self.parse_config(registry_config_str)

    def get_point(self, point_name):
        register = self.get_register_by_name(point_name)

        return register.value

    def _set_point(self, point_name, value):
        pass

    def _scrape_all(self):
        _log.info("OFC driver _scrape_all")
        result = {}
        read_registers = self.get_registers_by_type("byte", True)
        write_registers = self.get_registers_by_type("byte", False)
        for register in read_registers + write_registers:
            result[register.point_name] = register.value

        _log.info("result {r}".format(r=result))
        return result

    def parse_config(self, configDict):
        _log.info("OFC driver parse_config: {v}".format(v=configDict))
        if configDict is None:
            return


        for regDef in configDict:
            # Skip lines that have no address yet.
            if not regDef['Point Name']:
                continue

            read_only = regDef['Writable'].lower() != 'true'
            point_name = regDef['Volttron Point Name']
            description = regDef.get('Notes', '')
            units = regDef['Units']
            default_value = regDef.get("Starting Value", 42).strip()
            if not default_value:
                default_value = None
            type_name = regDef.get("Type", 'string')
            reg_type = type_mapping.get(type_name, str)

            register = ZeroToTenVoltRegisterFake(
                read_only,
                point_name,
                units,
                reg_type,
                default_value=default_value,
                description=description)

            if default_value is not None:
                self.set_default(point_name, register.value)

            self.insert_register(register)

