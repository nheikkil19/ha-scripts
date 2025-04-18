from abc import ABC, abstractmethod
from datetime import datetime, time
from time import sleep

import appdaemon.plugins.hass.hassapi as hass
import pytz
from config import TIME_ZONE, get_heating_optimizer_config

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
        self.listen_state(self.automation_state_changed, self.input_boolean_name)

        self.run_hourly(self.update_state, start=self.start)
        self.update_state({})

    @abstractmethod
    def update_state(self, kwargs):
        pass

    def is_automation_on(self) -> bool:
        return self.get_state(self.input_boolean_name) == "on"

    def operate_switch(self, turn_on: bool):
        state = "on" if turn_on else "off"
        self.log(f"Turning {state} heating")

        if self.get_state(self.heating_switch) == state:
            self.log(f"Heating is already {state}")
            return
        elif turn_on:
            self.turn_on(self.heating_switch)
        else:
            self.turn_off(self.heating_switch)

    def switch_turn_on(self):
        self.operate_switch(True)

    def switch_turn_off(self):
        self.operate_switch(False)

    def get_datetime_now(self):
        return datetime.now(tz=pytz.timezone(TIME_ZONE))

    def get_prices(self, tomorrow: bool = False, tomorrow_default: list = []) -> list:
        if self.prices_updated.date() != self.get_datetime_now().date():
            self.yesterday_prices = self.prices[:24]  # Used to check if prices are updated. Use only one day prices
            for _ in range(10):  # Set a limit to the number of attempts
                self.prices = self.get_state(self.price_sensor, attribute="today")
                if self.prices != self.yesterday_prices:  # Prices have changed
                    if tomorrow:
                        self.prices += self.get_state(self.price_sensor, attribute="tomorrow", default=tomorrow_default)
                    self.prices_updated = self.get_datetime_now()
                    self.log(f"New prices: {self.prices}")
                    return self.prices
                sleep(1)  # Wait for 1 second before trying again
            self.error("Failed to get new prices after maximum attempts")
        return self.prices

    def automation_state_changed(self, entity, attribute, old, new, kwargs):
        if new == "on":
            self.log("Automation turned on")
            self.update_state({})
        else:
            self.log("Automation turned off")
            self.switch_turn_off()


def benchmark_function(logger, func, *args, **kwargs):
    start_time = datetime.now()
    result = func(*args, **kwargs)
    end_time = datetime.now()
    elapsed_time = (end_time - start_time).total_seconds()
    logger(f"Function {func.__name__} took {elapsed_time:.2f} seconds to execute.")
    return result
