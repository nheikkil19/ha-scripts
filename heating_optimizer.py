import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, timedelta
import pytz


class HeatingOptimizer(hass.Hass):
    def initialize(self):
        self.heating_switch = "switch.bathroom_switch"

        start_time = self.get_start_time()
        self.run_every(self.check_and_control_heating, start=start_time, interval=3600)
        # self.run_every(self.check_and_control_heating, start="now", interval=60)

    def check_and_control_heating(self, kwargs):
        self.log("Checking and controlling heating")
        if self.is_nth_cheapest_hour(0):
            self.switch_turn_on()
        else:
            self.switch_turn_off()


    def get_todays_prices(self) -> list:
        return self.entities.sensor.nordpool_kwh_fi_eur_3_10_024.attributes.today

    def get_tomorrows_prices(self) -> list:
        return self.entities.sensor.nordpool_kwh_fi_eur_3_10_024.attributes.tomorrow

    def get_current_price(self) -> float:
        current_hour = self.get_current_datetime().hour
        self.log(f"Current hour: {current_hour}")
        return self.get_todays_prices()[current_hour]

    def get_start_time(self):
        now = self.get_current_datetime()
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

    def get_hour_price_rank(self) -> int:
        todays_prices = self.get_todays_prices()
        current_price = self.get_current_price()
        for i, price in enumerate(sorted(todays_prices)):
            if price > current_price:
                return i
        return len(todays_prices)

    def is_nth_cheapest_hour(self, n) -> bool:
        rank = self.get_hour_price_rank()
        self.log(f"Current price rank: {rank}")
        return rank <= n

    def get_current_datetime(self):
        return datetime.now(tz=pytz.timezone("Europe/Helsinki"))
