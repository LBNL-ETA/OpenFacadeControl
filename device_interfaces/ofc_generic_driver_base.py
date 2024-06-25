
from volttron.platform.messaging.health import STATUS_GOOD
from platform_driver.interfaces import BaseInterface, BaseRegister, BasicRevert
from volttron.platform.agent import utils
import logging

utils.setup_logging()
_log = logging.getLogger(__name__)


class OFCGenericRegister(BaseRegister):
    def __init__(self, read_only, point_name, units, reg_type, get_request_function, post_request_function=lambda x: x,
                 default_value=None, description=''):
        super(OFCGenericRegister, self).__init__("byte", read_only, point_name, units, description='')

        _log.info('OFCWebRegister init. locals:\n\t{v}\n'.format(v=locals()))

        self.reg_type = reg_type
        # python_type is used for the metedata returned.  It defaults to int
        self.python_type = reg_type
        self.get_request_f = get_request_function
        self.post_request_f = post_request_function

        if default_value is None:
            self._value = self.get_request_f()
        else:
            try:
                _log.info("python_type: {r}, default value: {v}".format(r=self.python_type, v=default_value))
                self._value = self.python_type(default_value)
            except ValueError:
                self._value = self.python_type()


    @property
    def value(self):
        return self.get_request_f()

    @value.setter
    def value(self, v):
        self.post_request_f(v)


class OFCGenericInterface(BasicRevert, BaseInterface):
    def __init__(self, **kwargs):
        super(OFCGenericInterface, self).__init__(**kwargs)

    def get_point(self, point_name):
        register = self.get_register_by_name(point_name)
        return register.value

    def _set_point(self, point_name, value):
        register = self.get_register_by_name(point_name)
        if register.read_only:
            raise RuntimeError(
                "Trying to write to a point configured read only: " + point_name)

        register.value = register.reg_type(value)
        return register.value

    def _scrape_all(self):
        result = {}

        for register in self.point_map.values():
            result[register.point_name] = register.value

        _log.info("_scrape_all result {r}".format(r=result))
        return result

    def post_config(self):
        _log.info(f"Calling self.vip.health.set_status with STATUS_GOOD")
        #self.vip.health.set_status(STATUS_GOOD, f"Configuration of agent {self.id} successful")
        self.vip.health.set_status(STATUS_GOOD, f"Configuration of agent successful")
        _log.info(f"Finished calling self.vip.health.set_status with STATUS_GOOD")
