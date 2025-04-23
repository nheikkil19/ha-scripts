from abc import ABC, abstractmethod
from datetime import datetime, time
from time import sleep

import appdaemon.plugins.hass.hassapi as hass
import pytz
from config import TIME_ZONE, get_heating_optimizer_config


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
        self.yesterday_prices = []
        self.last_stats_update = get_datetime_now()
        self.last_switch_state = self.get_switch_state()
        self.last_active_seconds = 0
        self.cost = 0
        self.on_hours = []
        self.details = ""
        self.optimizer = self.__class__.__name__
        self.listen_state(self.automation_state_changed, self.input_boolean_name)

        self.run_hourly(self.do_hourly_update, start=self.start)
        self.do_hourly_update({})

        self.run_every(
            self.update_optimizer_information,
            start="now",
            interval=5 * 60,
        )
        self.update_optimizer_information({})

    def do_hourly_update(self, kwargs):
        if self.get_state(self.input_boolean_name) == "on":
            action = self.update_state()
        # Call e.g. update cost or other info here
        if action is not None:
            self.operate_switch(action)

    @abstractmethod
    def update_state(self) -> bool:
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
        self.log(f"Last updated prices: {self.prices_updated}")
        if self.prices_updated.date() != get_datetime_now().date():  # Get new prices when the day changes
            self.yesterday_prices = self.prices[:24]  # Used to check if prices are updated. Use only one day prices
            for _ in range(10):  # Set a limit to the number of attempts
                self.prices = self.get_state(self.price_sensor, attribute="today")
                if self.prices != self.yesterday_prices:  # Prices have changed
                    self.prices_updated = get_datetime_now()
                    break
                sleep(1)  # Wait for 1 second before trying again
            self.error("Failed to get new prices after maximum attempts")
        if tomorrow:
            tomorrow_prices = self.get_state(self.price_sensor, attribute="tomorrow")
            self.prices += tomorrow_prices if len(tomorrow_prices) == 24 else []
        self.log(f"New prices: {self.prices}")
        return self.prices

    def automation_state_changed(self, entity, attribute, old, new, kwargs):
        if new == "on":
            self.log("Automation turned on")
            self.update_state({})
        else:
            self.log("Automation turned off")
            self.switch_turn_off()

    def update_optimizer_information(self, kwargs):
        now = day_start = get_datetime_now()
        if now.date() != self.last_stats_update.date():
            self.log("New day started, resetting stats")
            self.cost = 0
            self.last_active_seconds = 0

        if self.last_switch_state:
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            last_update_or_day = max(self.last_stats_update, day_start)

            seconds = (now - last_update_or_day).total_seconds()
            self.last_active_seconds += seconds

            cost = seconds * self.calculate_real_price(self.prices[now.hour]) / 3600
            self.cost += cost
            self.last_switch_state = self.get_switch_state()

        hours = self.last_active_seconds // 3600
        minutes = self.last_active_seconds % 3600 // 60
        active_time = f"{hours:.0f} h {minutes:.0f} min"
        cost_string = f"{self.cost:.6f} snt"

        self.last_stats_update = now

        self.set_state(
            self.optimizer_sensor,
            state=self.optimizer,
            attributes={
                "details": self.details,
                "cost": cost_string,
                "on_hours": self.on_hours,
                "active_time": active_time,
            },
        )
        self.log(f"Updated optimizer information: cost={cost_string}, active_time={active_time}, on_hours={self.on_hours}")

    def update_on_hours(self, schedule: list[bool], offset: int = 0):
        self.on_hours = []
        for i, on in enumerate(schedule):
            if on:
                self.on_hours.append((i + offset) % 24)

    def print_on_hours(self):
        log_str = "On hours: " + ", ".join([str(hour) for hour in self.on_hours])
        self.log(log_str)

    def update_cost(self, is_on: bool):
        hour = get_datetime_now().hour
        if hour == 0:
            self.cost = 0
        self.cost += is_on * self.calculate_real_price(self.prices[hour])

    def calculate_real_price(self, price: float) -> float:
        multiplier = self.config.get("cost_multiplier", 1)
        offset = self.config.get("offset", 0)
        return (price + offset) * multiplier

    def get_switch_state(self) -> bool:
        return self.get_state(self.heating_switch, default=False) == "on"


def benchmark_function(logger, func, *args, **kwargs):
    start_time = datetime.now()
    result = func(*args, **kwargs)
    end_time = datetime.now()
    elapsed_time = (end_time - start_time).total_seconds()
    logger(f"Function {func.__name__} took {elapsed_time:.2f} seconds to execute.")
    return result


def get_datetime_now():
    return datetime.now(tz=pytz.timezone(TIME_ZONE))


def get_next_n_minutes(n: int = 5):
    now = get_datetime_now()
    minutes = now.minute // n * (n + 1)

    return now.replace(minute=minutes, second=0, microsecond=0)
