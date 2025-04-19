import itertools
from mpc_raw import solve_mpc
import numpy as np

from generic_heating_optimizer import GenericHeatingOptimizer, benchmark_function, get_datetime_now

# Ideas for improvement:
# - Update every 15 minutes
# - Add daily cost

ENABLED = True

HORIZON = 24
MIN_TEMP = 23
MAX_TEMP = 27
COOLING_RATE = 0.34  # °C/h
HEATING_RATE = 0.44  # °C/h


class MpcHeating(GenericHeatingOptimizer):

    def initialize(self):
        super().initialize()

    def update_state(self, kwargs):
        if self.get_state(self.input_boolean_name) == "off" or not ENABLED:
            self.log("Automation is off or disabled. Do nothing.")
            return
        # action = self.get_next_action_brute_force()
        action = self.get_next_action_cvxpy()
        if action is None:
            self.log("No valid schedule found. Do nothing.")
            return
        # Turn on/off the switch based on the first hour of the schedule
        self.operate_switch(action)
        self.update_cost(action)  # Update cost based on the first hour
        self.update_optimizer_information(self.__class__.__name__, f"MPC with Horizon {HORIZON}")

    def get_schedule_brute_force(self) -> tuple[list[bool], float]:
        """Optimize MPC by brute force"""
        current_temp = float(self.get_state(self.config["temperature_sensor"]))
        prices = self.get_prices(tomorrow=True)  # Default to high price if not available
        current_hour = get_datetime_now().hour
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

    def get_next_action_brute_force(self) -> bool:
        best_schedule, best_cost = benchmark_function(self.log, self.get_schedule_brute_force)
        if not best_schedule:
            return None
        self.log(f"Best schedule: {best_schedule}, Cost: {best_cost}, Horizon: {HORIZON}")
        self.update_on_hours(best_schedule, offset=get_datetime_now().hour)
        action = best_schedule[0]
        return action

    def get_next_action_cvxpy(self):
        prices = self.get_prices(tomorrow=True)
        prices_from_now = prices[get_datetime_now().hour:get_datetime_now().hour + HORIZON]
        prices_np = np.array(prices_from_now)
        current_temp = float(self.get_state(self.config["temperature_sensor"]))
        horizon = min(len(prices_np), HORIZON)
        T, u, result = solve_mpc(horizon, MIN_TEMP, MAX_TEMP, HEATING_RATE, COOLING_RATE, prices_np, current_temp)
        if result is None:
            self.log("No valid schedule found. Do nothing.")
            return None
        action = u[0].value
        schedule = u.value
        self.update_on_hours(schedule, offset=get_datetime_now().hour)
        self.log("Optimal heating actions:", u.value)
        self.log("Optimal temperatures:", T.value)
        return action
