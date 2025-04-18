import itertools
import appdaemon.plugins.hass.hassapi as hass
from datetime import time
from heating_optimizer import HeatingOptimizer

from config import get_heating_optimizer_config

# Ideas for improvement:
# - Update every 15 minutes
# - Replace old heating optimizer or make abstract with basic functionality


class MpcHeating(HeatingOptimizer):

    def initialize(self):
        self.config = get_heating_optimizer_config()
        self.price_data = self.config["price_data"]
        self.heating_switch = self.config["heating_switch"]
        # self.run_every(self.optimize_mpc, start=time(0, 1, 0), interval=60*15)
        self.run_hourly(self.optimize_mpc, start=time(0, 1, 0))
        self.optimize_mpc({})

    def optimize_mpc(self, kwargs):
        horizon = 9
        min_temp = 22
        max_temp = 25

        cooling_rate = 0.2  # °C/h
        heating_rate = 0.1  # °C/h

        current_temp = float(self.get_state(self.config["temperature_sensor"]))
        prices = self.get_todays_and_tomorrows_prices()
        current_hour = self.get_datetime_now().hour
        prices_from_now = prices[current_hour:current_hour + horizon]

        best_schedule = None
        best_cost = float("inf")

        for schedule in itertools.product([0, 1], repeat=horizon):
            temp = current_temp
            valid = True
            total_cost = 0

            for t in range(horizon):
                heating = schedule[t]
                if heating:
                    temp += heating_rate
                    total_cost += prices_from_now[t]
                else:
                    temp -= cooling_rate

                    if temp < min_temp or temp > max_temp:
                        valid = False
                        break

            if valid and total_cost < best_cost:
                best_cost = total_cost
                best_schedule = schedule

        if best_schedule:
            self.log(f"Best schedule: {best_schedule}, Cost: {best_cost}")
            self.schedule = best_schedule
            self.print_schedule(self.schedule)
        else:
            self.log("No valid schedule found")

        # Do first action
        if self.schedule[0]:
            self.switch_turn_on()
        else:
            self.switch_turn_off()

    def get_todays_and_tomorrows_prices(self) -> list:
        """
        Get today's and tomorrow's prices
        """
        todays_prices = self.get_state(self.price_data, attribute="today")
        tomorrow_prices = self.get_state(self.price_data, attribute="tomorrow", default=[])
        self.log("Today's and tomorrow's prices: " + str(todays_prices + tomorrow_prices))
        return todays_prices + tomorrow_prices
