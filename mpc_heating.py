import itertools
from datetime import time
from generic_heating_optimizer import GenericHeatingOptimizer

# Ideas for improvement:
# - Update every 15 minutes
# - Add daily cost

HORIZON = 12
MIN_TEMP = 22
MAX_TEMP = 25
COOLING_RATE = 0.2  # °C/h
HEATING_RATE = 0.1  # °C/h


class MpcHeating(GenericHeatingOptimizer):

    def initialize(self):
        super().initialize()
        # self.run_every(self.optimize_mpc, start=time(0, 1, 0), interval=60*15)
        self.run_hourly(self.update_state, start=time(0, 1, 0))
        self.update_state({})

    def update_state(self, kwargs):
        best_schedule, best_cost = self.get_schedule_brute_force()
        if best_schedule:
            self.log(f"Best schedule: {best_schedule}, Cost: {best_cost}")
            self.print_schedule(best_schedule)
        else:
            self.log("No valid schedule found. Do nothing.")
            return
        # Turn on/off the switch based on the first hour of the schedule
        self.operate_switch(best_schedule[0])

    def get_schedule_brute_force(self) -> tuple[list[bool], float]:
        """Optimize MPC by brute force"""
        current_temp = float(self.get_state(self.config["temperature_sensor"]))
        prices = self.get_prices(tomorrow=True, tomorrow_default=[100] * 24)  # Default to high price if not available
        current_hour = self.get_datetime_now().hour
        prices_from_now = prices[current_hour:current_hour + HORIZON]

        best_schedule = None
        best_cost = float("inf")
        for schedule in itertools.product([0, 1], repeat=HORIZON):  # Iterate over all possible 2^horizon schedules
            temp = current_temp
            valid = True
            total_cost = 0
            # Simulate the schedule
            for t in range(HORIZON):
                heating = schedule[t]
                if heating:
                    temp += HEATING_RATE
                    total_cost += prices_from_now[t]
                else:
                    temp -= COOLING_RATE
                if temp < MIN_TEMP or MAX_TEMP < temp:  # Check if temp is in range
                    valid = False
                    break
            # If valid schedule, check if cost is lower
            if valid and total_cost < best_cost:
                best_cost = total_cost
                best_schedule = schedule
        return best_schedule, best_cost

    def print_schedule(self, schedule: list[bool]):
        log_str = "On hours: "
        current_hour = self.get_datetime_now().hour
        for i, on in enumerate(schedule):
            if on:
                log_str += f"{(i + current_hour) % 24}, "
        log_str = log_str[:-2]
        self.log(log_str)
