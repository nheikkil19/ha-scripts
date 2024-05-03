import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, timedelta
import pytz
from programs import TotalCheapest, Sections

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
