from abc import ABC, abstractmethod
from datetime import datetime, time

import appdaemon.plugins.hass.hassapi as hass
import pytz
from config import TIME_ZONE, get_heating_optimizer_config
from time import sleep


# TODO: Implement selecting between optimizers and making disabling global

class GenericHeatingOptimizer(hass.Hass, ABC):

    def initialize(self):
        self.update_interval = 3600  # How often state is updated
        self.start = time(0, 1, 0)  # When to start the first update, default 1 minute after midnight
        self.config = get_heating_optimizer_config()
        self.heating_switch = self.config["heating_switch"]
        self.input_boolean_name = self.config["input_boolean_name"]
        self.price_sensor = self.config["price_sensor"]
        self.prices_updated = datetime.min
        self.prices = []

    @abstractmethod
    def update_state(self, kwargs):
        pass

    def is_automation_on(self) -> bool:
        return self.get_state(self.input_boolean_name) == "on"

    # TODO: Combine these
    def switch_turn_on(self):
        if self.get_state(self.heating_switch) == "off":
            self.log("Turning on heating")
            self.turn_on(self.heating_switch)
        else:
            self.log("Heating is already on")

    def switch_turn_off(self):
        if self.get_state(self.heating_switch) == "on":
            self.log("Turning off heating")
            self.turn_off(self.heating_switch)
        else:
            self.log("Heating is already off")

    def get_datetime_now(self):
        return datetime.now(tz=pytz.timezone(TIME_ZONE))

    def get_prices(self, tomorrow: bool = False) -> list:
        # TODO: Refactor this with for loop
        if self.prices_updated.date() != self.get_datetime_now().date():
            self.yesterday_prices = self.prices[:24]  # Used to check if prices are updated. Use only one day prices
            attempts = 0
            MAX_ATTEMPTS = 10  # Set a limit to the number of attempts
            while self.yesterday_prices == self.prices and attempts < MAX_ATTEMPTS:
                self.prices = self.get_state(self.price_sensor, attribute="today")
                sleep(1)  # Wait for 1 second before trying again
                attempts += 1
            if attempts == MAX_ATTEMPTS:
                self.error("Failed to get new prices after maximum attempts")
            else:
                if tomorrow:
                    self.prices += self.get_state(self.price_sensor, attribute="tomorrow", default=[])
                self.prices_updated = self.get_datetime_now()
        self.log(f"New prices: {self.prices}")
        return self.prices
