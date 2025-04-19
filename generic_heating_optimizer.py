from abc import ABC, abstractmethod
from datetime import datetime, time
from time import sleep

import appdaemon.plugins.hass.hassapi as hass
import pytz
from config import TIME_ZONE, get_heating_optimizer_config

# TODO: Implement selecting between optimizers and making disabling global


class ActiveTime:
    def __init__(self, hour_min_string: str):
        hours = hour_min_string.split("h")[0]
        if "m" in hour_min_string:
            minutes = hour_min_string.split("h")[1].split("m")[0]
        else:
            minutes = 0
        self.hours = int(hours)
        self.minutes = int(minutes)
        self.last_update = get_datetime_now()

    def update(self, hours: int = 0, minutes: int = 0):
        if self.last_update.date() != get_datetime_now().date():
            self.hours = 0
            self.minutes = 0
        MINUTES_IN_HOUR = 60
        new_minutes = self.minutes + minutes
        self.minutes = new_minutes % MINUTES_IN_HOUR
        overflow_hours = new_minutes // MINUTES_IN_HOUR
        self.hours += overflow_hours + hours

    def get_active_time_string(self):
        return f"{self.hours}h" + (f"{self.minutes}m" if self.minutes else "")


class GenericHeatingOptimizer(hass.Hass, ABC):

    def initialize(self):
        self.update_interval = 3600  # How often state is updated
        self.start = time(0, 1, 0)  # When to start the first update, default 1 minute after midnight
        self.config = get_heating_optimizer_config()
        self.heating_switch = self.config["heating_switch"]
        self.input_boolean_name = self.config["input_boolean_name"]
        self.price_sensor = self.config["price_sensor"]
        self.optimizer_sensor = self.config["optimizer_sensor"]  # Sensor to store the selected program
        self.prices_updated = datetime.min
        self.prices = []
        self.active_time = ActiveTime(self.get_state(self.optimizer_sensor, attribute="active_time", default="0h"))
        self.cost = self.get_state(self.optimizer_sensor, attribute="cost", default=0)
        self.on_hours = []
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

    def get_prices(self, tomorrow: bool = False) -> list:
        if self.prices_updated.date() != get_datetime_now().date():
            self.yesterday_prices = self.prices[:24]  # Used to check if prices are updated. Use only one day prices
            for _ in range(10):  # Set a limit to the number of attempts
                self.prices = self.get_state(self.price_sensor, attribute="today")
                if self.prices != self.yesterday_prices:  # Prices have changed
                    if tomorrow:
                        tomorrow_prices = self.get_state(self.price_sensor, attribute="tomorrow")
                        self.prices += tomorrow_prices if len(tomorrow_prices) == 24 else []  # self.prices
                    self.prices_updated = get_datetime_now()
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

    def update_optimizer_information(self, optimizer_name: str, details: str):
        self.print_on_hours()
        self.set_state(
            self.optimizer_sensor,
            state=optimizer_name,
            attributes={
                "details": details,
                "cost": self.cost,
                "on_hours": self.on_hours,
                "active_time": self.active_time.get_active_time_string(),
            },
        )

    def update_on_hours(self, schedule: list[bool], offset: int = 0):
        """Get the on hours of the schedule"""
        self.on_hours = []
        for i, on in enumerate(schedule):
            if on:
                self.on_hours.append((i + offset) % 24)

    def print_on_hours(self):
        log_str = "On hours: " + ", ".join([str(hour) for hour in self.on_hours])
        self.log(log_str)

    def update_cost(self, is_on: bool):
        if get_datetime_now().hour == 0:
            self.cost = 0
        self.cost += self.config["cost_multiplier"] * is_on


def benchmark_function(logger, func, *args, **kwargs):
    start_time = datetime.now()
    result = func(*args, **kwargs)
    end_time = datetime.now()
    elapsed_time = (end_time - start_time).total_seconds()
    logger(f"Function {func.__name__} took {elapsed_time:.2f} seconds to execute.")
    return result


def get_datetime_now():
    return datetime.now(tz=pytz.timezone(TIME_ZONE))
