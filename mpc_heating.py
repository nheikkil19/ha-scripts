import itertools
from datetime import time
from config import get_heating_optimizer_config
from generic_heating_optimizer import GenericHeatingOptimizer

# Ideas for improvement:
# - Update every 15 minutes


class MpcHeating(GenericHeatingOptimizer):

    def initialize(self):
        self.config = get_heating_optimizer_config()
        self.price_sensor = self.config["price_sensor"]
        self.heating_switch = self.config["heating_switch"]
        # self.run_every(self.optimize_mpc, start=time(0, 1, 0), interval=60*15)
        self.run_hourly(self.update_state, start=time(0, 1, 0))
        self.update_state({})

    def update_state(self, kwargs):
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
            self.print_schedule(best_schedule)
        else:
            self.log("No valid schedule found")

        # Do first action
        if best_schedule[0]:
            self.switch_turn_on()
        else:
            self.switch_turn_off()

    def get_todays_and_tomorrows_prices(self) -> list:
        """
        Get today's and tomorrow's prices
        """
        todays_prices = self.get_state(self.price_sensor, attribute="today")
        tomorrow_prices = self.get_state(self.price_sensor, attribute="tomorrow", default=[])
        self.log("Today's and tomorrow's prices: " + str(todays_prices + tomorrow_prices))
        return todays_prices + tomorrow_prices

    def print_schedule(self, schedule: list[bool]):
        log_str = "On hours: "
        current_hour = self.get_datetime_now().hour
        for i, on in enumerate(schedule):
            if on:
                log_str += f"{i + current_hour}, "
        log_str = log_str[:-2]
        self.log(log_str)
