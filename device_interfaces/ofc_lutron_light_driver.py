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

from platform_driver.interfaces.ofc_generic_driver_base import (
    OFCGenericInterface,
    OFCGenericRegister,
)
import logging
try:
    from pylutron import Lutron
except ImportError:
    raise ImportError("pylutron library is required for Lutron driver. Install with: pip install pylutron")

_log = logging.getLogger(__name__)

type_mapping = {
    "string": str,
    "int": int,
    "integer": int,
    "float": float,
    "bool": bool,
    "boolean": bool,
}


class Interface(OFCGenericInterface):
    def __init__(self, **kwargs):
        super(Interface, self).__init__(**kwargs)
        self.host = None
        self.username = None
        self.password = None
        self.lutron_client = None

    def configure(self, config_dict, registry_config_str):
        _log.info(f"Configuring Lutron interface with: {config_dict}")

        self.host = config_dict.get("host")
        self.username = config_dict.get("username")
        self.password = config_dict.get("password")

        if not all([self.host, self.username, self.password]):
            raise ValueError("Missing required Lutron configuration: host, username, password")

        self._connect_to_lutron()
        self.parse_registers(registry_config_str)
        self.post_config()
    
    def _connect_to_lutron(self):
        """Establish connection to Lutron system with retry logic"""
        try:
            _log.info(f"Connecting to Lutron system at {self.host}")
            self.lutron_client = Lutron(self.host, self.username, self.password)
            self.lutron_client.load_xml_db()
            self.lutron_client.connect()
            _log.info("Successfully connected to Lutron system")
        except Exception as e:
            _log.error(f"Failed to connect to Lutron system: {e}")
            self.lutron_client = None
            raise
    
    def _ensure_connection(self):
        """Ensure we have a valid connection, reconnect if necessary"""
        if not self.lutron_client:
            _log.warning("No Lutron connection, attempting to reconnect")
            self._connect_to_lutron()

    def parse_registers(self, registers):
        if not registers:
            raise RuntimeError(f"Missing registers for {self.host}")

        for register_config in registers:
            if not register_config["Point Name"]:
                continue

            point_name = register_config["Volttron Point Name"]
            read_only = register_config["Writable"].lower() != "true"
            units = register_config.get("Units", "")
            description = register_config.get("Notes", "")
            default_value = register_config.get("Starting Value", 0)
            type_name = register_config.get("Type", "float").lower()
            reg_type = type_mapping.get(type_name, float)

            # Lutron specific configuration
            area_name = register_config.get("area_name")
            output_number = register_config.get("output_number")
            
            if not area_name or output_number is None:
                _log.error(f"Missing required Lutron fields: area_name={area_name}, output_number={output_number}")
                continue

            # Find the specific output in the Lutron system
            output = None
            for area in self.lutron_client.areas:
                if area.name == area_name:
                    for out in area.outputs:
                        if out.number == output_number:
                            output = out
                            break
                    break

            if not output:
                _log.error(f"Could not find output {output_number} in area {area_name}")
                continue

            def get_request_function():
                try:
                    self._ensure_connection()
                    level = output.level
                    _log.debug(f"Retrieved Lutron output level: {level} for {area_name}/{output_number}")
                    return level
                except Exception as e:
                    _log.error(f"Error getting Lutron output level for {area_name}/{output_number}: {e}")
                    return 0.0

            def post_request_function(val):
                try:
                    self._ensure_connection()
                    level = float(val)
                    # Clamp value between 0.0 and 100.0 for Lutron
                    level = max(0.0, min(100.0, level))
                    output.level = level
                    _log.info(f"Set Lutron output level: {level} for {area_name}/{output_number}")
                    return level
                except Exception as e:
                    _log.error(f"Error setting Lutron output level for {area_name}/{output_number}: {e}")
                    return False

            register = OFCGenericRegister(
                read_only=read_only,
                point_name=point_name,
                units=units,
                reg_type=reg_type,
                get_request_function=get_request_function,
                post_request_function=post_request_function,
                default_value=default_value,
                description=description,
            )

            if default_value is not None:
                self.set_default(point_name, register.value)

            self.insert_register(register)

    def __del__(self):
        """Clean up Lutron connection on destruction"""
        try:
            if self.lutron_client:
                self.lutron_client.disconnect()
                _log.info("Disconnected from Lutron system")
        except Exception as e:
            _log.error(f"Error disconnecting from Lutron system: {e}")
