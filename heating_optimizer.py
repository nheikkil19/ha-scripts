import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, timedelta
import pytz
from abc import ABC, abstractmethod

TOTAL_CHEAPEST_HOURS = 8
SECTION_LENGHTS = [3, 9, 9, 3]
ON_HOURS = [0, 3, 3, 0]


class HeatingOptimizer(hass.Hass):

    def initialize(self):
        self.heating_switch = "switch.bathroom_switch"
        self.nordpool_data = self.entities.sensor.nordpool_kwh_fi_eur_3_10_024

        start_time = self.get_start_time()
        self.log(f"Start time: {start_time}")

        self.select_daily_program({})
        self.run_at(self.select_daily_program, start="00:00:30")

        self.check_and_control_heating({})
        self.run_every(self.check_and_control_heating, start=start_time, interval=3600)
        # self.run_every(self.check_and_control_heating, start="now", interval=60)

    def check_and_control_heating(self, kwargs):
        self.log("Checking and controlling heating")
        self.print_schedule(self.schedule)
        if self.should_turn_on():
            self.switch_turn_on()
        else:
            self.switch_turn_off()

    def select_daily_program(self, kwargs):
        todays_prices = self.get_todays_prices()

        total_cheapest = TotalCheapest(todays_prices, TOTAL_CHEAPEST_HOURS)
        sections = Sections(todays_prices, SECTION_LENGHTS, ON_HOURS)

        total_cheapest_schedule, total_cheapest_cost = total_cheapest.evaluate()
        sections_schedule, sections_cost = sections.evaluate()

        self.log(f"Total cheapest cost: {total_cheapest_cost}")
        self.log(f"Sections cost: {sections_cost}")

        if total_cheapest_cost < sections_cost:
            self.log("Selecting total cheapest program")
            self.schedule = total_cheapest_schedule
        else:
            self.log("Selecting sections program")
            self.schedule = sections_schedule

    def should_turn_on(self):
        current_hour = self.get_datetime_now().hour
        return self.schedule[current_hour]

    def get_todays_prices(self) -> list:
        return self.nordpool_data.attributes.today

    def get_start_time(self):
        now = self.get_datetime_now()
        start_time = now.replace(minute=1, second=0, microsecond=0) + timedelta(hours=1)
        return start_time

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
        return datetime.now(tz=pytz.timezone("Europe/Helsinki"))

    def print_schedule(self, schedule: list[bool]):
        log_str = "On hours: "
        for i, on in enumerate(schedule):
            if on:
                log_str += f"{i}, "
        log_str = log_str[:-2]
        self.log(log_str)


class BaseProgram(ABC):
    def __init__(self, prices: list):
        self.prices = prices

    @abstractmethod
    def evaluate(self) -> list[bool]:
        pass


class TotalCheapest(BaseProgram):
    def __init__(self, prices: list, n: int):
        super().__init__(prices)
        self.n = n

    def evaluate(self) -> tuple[list[bool], int]:
        schedule = [False] * len(self.prices)
        nth_cheapest = sorted(self.prices)[self.n - 1] if self.n > 0 else -float("inf")
        cost = 0
        count = 0
        for i, price in enumerate(self.prices):
            if count == self.n:
                break
            if price <= nth_cheapest:
                cost += price
                count += 1
                schedule[i] = True
        return schedule, cost


class Sections(BaseProgram):
    def __init__(self, prices: list, section_lengths: list, on_hours: list):
        super().__init__(prices)
        if sum(section_lengths) != 24:
            raise ValueError("Sum of section lengths must be 24")
        if len(on_hours) != len(section_lengths):
            raise ValueError("Need to specify on hours for each section length")

        self.section_lengths = section_lengths
        self.on_hours = on_hours

    def evaluate(self) -> tuple[list[bool], int]:
        schedule = [False] * len(self.prices)

        total_cost = 0
        previous_section_end = 0
        for section_length, on_hour in zip(self.section_lengths, self.on_hours):
            section_prices = self.prices[
                previous_section_end : previous_section_end + section_length
            ]
            section = TotalCheapest(section_prices, on_hour)
            section_schedule, cost = section.evaluate()
            for i, on in enumerate(section_schedule):
                schedule[previous_section_end + i] = on
            previous_section_end += section_length
            total_cost += cost
        return schedule, total_cost
