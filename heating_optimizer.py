from datetime import datetime, time
from time import sleep

import appdaemon.plugins.hass.hassapi as hass
import pytz

from config import get_heating_optimizer_config, TIME_ZONE
from programs import BaseProgram, Sections, TotalCheapest

# Example config in config.py:
# HEATING_CONFIG = {
#     "heating_switch": "switch.bathroom_switch",  # The entity ID of the switch that controls the heating
#     "input_boolean_name": "input_boolean.heating_automation",  # The entity ID of the input that controls the automation
#     "optimizer_sensor": "sensor.heating_optimizer",  # The entity ID of the sensor that displays the optimization data
#     "price_data": "sensor.nordpool_kwh_fi_eur_3_10_024",  # The entity ID of the sensor that provides the price data
#     "offset": 1,  # An offset value to adjust the prices
#     "cost_multiplier": 1,  # A multiplier based on power consumption
#     "programs": [
#         {"type": "section", "on_hours": [0, 3, 3, 0], "section_lengths": [3, 9, 9, 3]},
#         {"type": "section", "on_hours": [8], "section_lengths": [24]},
#     ]
# }


class HeatingOptimizer(hass.Hass):

    def initialize(self):
        self.config = get_heating_optimizer_config()
        self.prices_updated = datetime.min
        self.todays_prices = []
        self.heating_switch = self.config["heating_switch"]
        self.input_boolean_name = self.config["input_boolean_name"]
        self.price_data = self.config["price_data"]

        self.listen_state(self.automation_state_changed, self.input_boolean_name)

        self.select_daily_program({})
        self.run_daily(
            self.select_daily_program,
            start=time(0, 0, 30),
            constrain_input_boolean=self.input_boolean_name,
        )

        self.check_and_control_heating({})
        self.run_hourly(self.check_and_control_heating, start=time(0, 1, 0))

    def check_and_control_heating(self, kwargs):
        self.config = get_heating_optimizer_config()
        self.select_daily_program({})
        if self.should_turn_on() and self.get_state(self.input_boolean_name) == "on":
            self.switch_turn_on()
        else:
            self.switch_turn_off()

    def select_daily_program(self, kwargs):
        todays_prices = self.get_todays_prices()
        min_cost = float("inf")
        selected_schedule = None

        for program in self.get_programs(todays_prices):
            schedule, cost = program.evaluate()
            cost *= self.config.get("cost_multiplier", 1)
            self.log(f"{program.name} cost: {cost}")

            if cost < min_cost:
                min_cost = cost
                selected_schedule = schedule
                selected_name = program.name

        self.log(f"Selected program: {selected_name}")
        self.schedule = selected_schedule
        self.print_schedule(self.schedule)

        self.update_data(selected_schedule, selected_name, min_cost)

    def should_turn_on(self):
        current_hour = self.get_datetime_now().hour
        return self.schedule[current_hour]

    def get_todays_prices(self) -> list:
        if self.prices_updated.date() != self.get_datetime_now().date():
            self.yesterday_prices = self.todays_prices
            attempts = 0
            MAX_ATTEMPTS = 10  # Set a limit to the number of attempts
            while self.yesterday_prices == self.todays_prices and attempts < MAX_ATTEMPTS:
                self.todays_prices = self.get_state(self.price_data, attribute="today")
                self.prices_updated = self.get_datetime_now()
                self.log(f"New prices: {self.todays_prices}")
                sleep(1)
                attempts += 1
            if attempts == MAX_ATTEMPTS:
                self.log("Failed to get new prices after maximum attempts")
        return self.todays_prices

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

    def print_schedule(self, schedule: list[bool]):
        log_str = "On hours: "
        for i, on in enumerate(schedule):
            if on:
                log_str += f"{i}, "
        log_str = log_str[:-2]
        self.log(log_str)

    def update_data(self, schedule, name, total_cost):
        sensor_name = self.config["optimizer_sensor"]
        state = "on" if self.get_state(self.input_boolean_name) == "on" else "off"
        on_hours = [i for i, on in enumerate(schedule) if on]
        self.set_state(
            sensor_name,
            state=state,
            attributes={"name": name, "total_cost": total_cost, "on_hours": on_hours},
        )

    def automation_state_changed(self, entity, attribute, old, new, kwargs):
        if new == "on":
            self.select_daily_program({})
            self.log("Automation turned on")
            self.check_and_control_heating({})
            self.set_state(self.config["optimizer_sensor"], state="on")
        else:
            self.log("Automation turned off")
            self.switch_turn_off()
            self.set_state(self.config["optimizer_sensor"], state="off")

    def get_programs(self, prices: list) -> list[BaseProgram]:
        programs = self.config["programs"]
        offset = self.config.get("offset", 0)
        prices = [price + offset for price in prices]
        ret = []
        for program in programs:
            if program["type"] == "total_cheapest":
                ret.append(TotalCheapest(prices, program["n"]))
            elif program["type"] == "section":
                ret.append(
                    Sections(prices, program["section_lengths"], program["on_hours"])
                )
            else:
                raise ValueError(f"Unknown program type: {program['type']}")
        return ret
