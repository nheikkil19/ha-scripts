"""
Calculates MPC (Model Predictive Control) heating and cooling rates for heating optimization.
Follows switch states and temperature changes.
"""

import appdaemon.plugins.hass.hassapi as hass
from config import TIME_ZONE, get_heating_optimizer_config
from datetime import datetime
import pytz
import math
from enum import Enum

MIN_TIMEDELTA = 0.25  # Minimum timedelta in hours to consider for rate updates
MAX_TIMEDELTA = 12  # Maximum timedelta in hours to consider for rate updates

HEATING_RATE = 0.6  # C/h
COOLING_RATE = -0.25  # C/h
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
        if timedelta < MIN_TIMEDELTA or MAX_TIMEDELTA < timedelta:
            self.log(f"Ignoring update due too small or large timedelta: {timedelta:.2f} hours")
            return

        current_temp = float(self.get_state(self.config["temperature_sensor"]))
        tempdelta_per_hour = (current_temp - self.prev_temp) / timedelta  # Positive if heating on

        class Rate(Enum):
            HEATING = "heating"
            COOLING = "cooling"

        def update_rate(rate: Rate):
            # Use exponential weighting to keep alpha_eff bounded between 0 and 1,
            # ensuring stability regardless of timedelta size.
            alpha_eff = 1 - math.exp(-K * timedelta)

            current_rate = self.heating_rate if rate == Rate.HEATING else self.cooling_rate
            self.log(f"{rate.value} rate update detected. Old: {current_rate} C/h, ")
            self.log(f"Latest rate: {tempdelta_per_hour:.2f} C/h, Alpha: {alpha_eff:.2f}")
            new_rate = current_rate * (1 - alpha_eff) + tempdelta_per_hour * alpha_eff

            if abs(new_rate - current_rate) > 0.5:
                self.log(f"Rate change too large: {new_rate} C/h. Not updating.")
                return
            if new_rate * current_rate <= 0:  # Cooling rate should be negative and heating positive
                self.log(f"Invalid rate change: {new_rate} C/h. Not updating.")
                return

            if rate == Rate.HEATING:
                self.heating_rate = new_rate
                self.set_state(self.config["mpc_heating_rate"], state=self.heating_rate)
            else:
                self.cooling_rate = new_rate
                self.set_state(self.config["mpc_cooling_rate"], state=self.cooling_rate)
            self.log(f"Updated {rate.value} rate: {new_rate} C/h")

        state = (old, new)
        if state == ("on", "off"):
            update_rate(Rate.HEATING)
        elif state == ("off", "on"):
            update_rate(Rate.COOLING)
        else:
            self.log(f"Invalid state change: {old} -> {new}. No rate update performed.")
            return

        self.prev_temp = current_temp
        self.last_update = get_datetime_now()

    def get_float_from_sensor(self, sensor_name: str, default: float = 0.0) -> float:
        sensor = self.config.get(sensor_name, None)
        if sensor is not None:
            value: str = self.get_state(sensor, default=default)
            value = float(value.replace(",", "."))
            return value
        return default
