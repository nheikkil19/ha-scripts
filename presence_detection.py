from datetime import datetime
import appdaemon.plugins.hass.hassapi as hass
import pytz
import router
from config import INTERESTING_DEVICES


class PresenceDetection(hass.Hass):

    def initialize(self):
        self.run_every(self.is_device_present, datetime.now(tz=pytz.timezone("Europe/Helsinki")), 300)
        self.is_device_present({})

    def is_device_present(self, kwargs):
        # Implement logic to check if interesting device is in router devices
        presence = False
        self.log("Checking presence")
        router_devices = router.get_network_devices()
        self.log(INTERESTING_DEVICES)
        self.log(router_devices)
        for device in router_devices:
            if device in [dev.lower() for dev in INTERESTING_DEVICES]:
                self.log(f"{device} is present")
                presence = True
        if presence:
            self.log("Presence set to on")
            self.set_state("input_boolean.presence", state="on")
        else:
            self.log("Presence set to off")
            self.set_state("input_boolean.presence", state="off")
