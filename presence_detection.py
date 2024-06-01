from datetime import datetime
import appdaemon.plugins.hass.hassapi as hass
import pytz
import router
from config import PRESENCE_CONFIG, TIME_ZONE

# PRESENCE_CONFIG = {
#     "interesting_devices": [
#         "AA:BB:CC:DD:EE:FF",
#     ],
#     "presence_sensor": "input_boolean.presence"
# }


class PresenceDetection(hass.Hass):

    def initialize(self):
        self.config = PRESENCE_CONFIG
        self.presence_sensor = self.config["presence_sensor"]
        self.interesting_devices = [dev.lower() for dev in self.config["interesting_devices"]]
        self.ip = self.config["ip"]
        self.mask = self.config["mask"]

        self.run_every(self.is_device_present, datetime.now(tz=pytz.timezone(TIME_ZONE)), 300)
        self.is_device_present({})

    def is_device_present(self, kwargs):
        # Implement logic to check if interesting device is in router devices
        presence = False
        self.log("Checking presence")
        router_devices = router.get_network_devices(self.ip, self.mask)
        # self.log(INTERESTING_DEVICES)
        # self.log(router_devices)
        for device in router_devices:
            if device.lower() in self.interesting_devices:
                self.log(f"{device} is present")
                presence = True
        if presence:
            if self.get_state(self.presence_sensor) != "home":
                self.log("Presence set to home")
                self.set_state(self.presence_sensor, state="home")
        else:
            self.log("No interesting devices found")
            if self.get_state(self.presence_sensor) != "not_home":
                self.log("Presence set to not_home")
                self.set_state(self.presence_sensor, state="not_home")
