import itertools
# import cvxpy as cp
# import numpy as np

from generic_heating_optimizer import GenericHeatingOptimizer, benchmark_function

# Ideas for improvement:
# - Update every 15 minutes
# - Add daily cost

ENABLED = True

HORIZON = 18
MIN_TEMP = 23
MAX_TEMP = 27
COOLING_RATE = 0.34  # °C/h
HEATING_RATE = 0.44  # °C/h


class MpcHeating(GenericHeatingOptimizer):

    def initialize(self):
        self.cost = 0  # Keep track of the cost
        super().initialize()

    def update_state(self, kwargs):
        if self.get_state(self.input_boolean_name) == "off" or not ENABLED:
            self.log("Automation is off or disabled. Do nothing.")
            return
        ret = benchmark_function(self.log, self.get_schedule_brute_force)
        best_schedule, best_cost = ret
        if not best_schedule:
            self.log("No valid schedule found. Do nothing.")
            return
        self.log(f"Best schedule: {best_schedule}, Cost: {best_cost}, Horizon: {HORIZON}")
        on_hours = self.get_on_hours(best_schedule, offset=self.get_datetime_now().hour)
        self.print_schedule(on_hours)
        # Turn on/off the switch based on the first hour of the schedule
        self.operate_switch(best_schedule[0])
        self.update_cost(best_schedule[0])  # Update cost based on the first hour
        self.update_optimizer_information(on_hours, self.__class__.__name__, f"MPC with Horizon {HORIZON}", self.cost)

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

    def update_cost(self, is_on: bool):
        if self.get_datetime_now().hour == 0:
            self.cost = 0
        self.cost += self.config["cost_multiplier"] * is_on
