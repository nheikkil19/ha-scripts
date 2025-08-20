"""
Calculates MPC (Model Predictive Control) heating and cooling rates for heating optimization.
Follows switch states and temperature changes.
"""

import appdaemon.plugins.hass.hassapi as hass
from config import TIME_ZONE, get_heating_optimizer_config
from datetime import datetime
import pytz
import math


MIN_TIMEDELTA = 0.25  # Minimum timedelta in hours to consider for rate updates
MIN_UPDATE_INTERVAL = 15 * 60  # Minimum update interval in seconds

HEATING_RATE = 0.6  # C/h
COOLING_RATE = 0.25  # C/h
K = 0.05  # Tuning constant for alpha_eff calculation

def get_datetime_now():
    return datetime.now(tz=pytz.timezone(TIME_ZONE))


class HeatingRateUpdater(hass.Hass):

    def initialize(self):
        self.config = get_heating_optimizer_config()
        self.prev_temp = float(self.get_state(self.config["temperature_sensor"]))
        self.last_update = get_datetime_now()
        self.heating_rate = self.get_float_from_sensor("mpc_heating_rate", HEATING_RATE)
        self.cooling_rate = self.get_float_from_sensor("mpc_cooling_rate", COOLING_RATE)

        self.listen_state(self.update_rates, self.config["heating_switch"])
        self.log(f"Initialized with heating_rate: {self.heating_rate}, cooling_rate: {self.cooling_rate}")

    def update_rates(self, entity, attribute, old, new, kwargs):
        self.heating_rate = self.get_float_from_sensor("mpc_heating_rate", HEATING_RATE)
        self.cooling_rate = self.get_float_from_sensor("mpc_cooling_rate", COOLING_RATE)

        timedelta = (get_datetime_now() - self.last_update).total_seconds() / 3600  # hours
        if timedelta <= MIN_TIMEDELTA:
            self.log("Ignoring update due to small timedelta: {:.2f} minutes".format(timedelta))
            return

        current_temp = float(self.get_state(self.config["temperature_sensor"]))
        tempdelta_per_hour = (current_temp - self.prev_temp) / timedelta  # Positive if heating on

        # Use exponential weighting to keep alpha_eff bounded between 0 and 1,
        # ensuring stability regardless of timedelta size.
        alpha_eff = 1 - math.exp(-K * timedelta)

        if old == "on" and new == "off":
            self.log(f"On -> Off detected. Old: {self.heating_rate} C/h, Latest rate: {tempdelta_per_hour:.2f} C/h, Alpha: {alpha_eff:.2f}")
            heating_rate = self.heating_rate * (1 - alpha_eff) + tempdelta_per_hour * alpha_eff
            if heating_rate <= 0 or heating_rate > HEATING_RATE + 1:
                self.log(f"Suspicious heating rate {heating_rate}. Not updated.")
                return
            self.heating_rate = heating_rate
            self.set_state(self.config["mpc_heating_rate"], state=self.heating_rate)
            self.log(f"Updated heating rate: {self.heating_rate} C/h")

        elif old == "off" and new == "on":
            self.log(f"Off -> On detected. Old: {self.cooling_rate} C/h, Latest rate: {tempdelta_per_hour:.2f} C/h, Alpha: {alpha_eff:.2f}")
            cooling_rate = self.cooling_rate * (1 - alpha_eff) - tempdelta_per_hour * alpha_eff
            if cooling_rate <= 0 or cooling_rate > COOLING_RATE + 1:
                self.log(f"Suspicious cooling rate {cooling_rate}. Not updated.")
                return
            self.cooling_rate = cooling_rate
            self.set_state(self.config["mpc_cooling_rate"], state=self.cooling_rate)
            self.log(f"Updated cooling rate: {self.cooling_rate} C/h")

        else:
            self.log(f"Invalid state change: {old} -> {new}. No rate update performed.")
            return

        self.prev_temp = current_temp
        self.last_update = get_datetime_now()
        # self.push_current_rates_to_ha()

    def get_float_from_sensor(self, sensor_name: str, default: float = 0.0) -> float:
        sensor = self.config.get(sensor_name, None)
        if sensor is not None:
            value: str = self.get_state(sensor, default=default)
            value = float(value.replace(",", "."))
            return value
        return default

    def push_current_rates_to_ha(self):
        self.set_state(self.config["mpc_heating_rate"], state=self.heating_rate)
        self.set_state(self.config["mpc_cooling_rate"], state=self.cooling_rate)
