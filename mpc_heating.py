from generic_heating_optimizer import GenericHeatingOptimizer, get_datetime_now
from mpc_raw import solve_mpc

# Ideas for improvement:
# - Update every 15 minutes
# - Add daily cost

HORIZON = 32
MIN_TEMP = 22
MAX_TEMP = 27
COOLING_RATE = 0.25  # °C/h
HEATING_RATE = 0.6  # °C/h


class MpcHeating(GenericHeatingOptimizer):

    def initialize(self):
        super().initialize()

    def update_state(self) -> bool:
        self.optimizer = self.__class__.__name__
        self.details = "MPC with Horizon " + str(HORIZON)
        action = self.get_next_action_cvxpy()
        if action is None:
            self.log("No valid schedule found. Do nothing.")
            return None
        # Turn on/off the switch based on the first hour of the schedule
        self.operate_switch(action)
        return action

    def get_next_action_cvxpy(self):
        prices = self.get_prices(tomorrow=True)
        prices_from_now = prices[get_datetime_now().hour:get_datetime_now().hour + HORIZON]
        real_prices = [self.calculate_real_price(price) for price in prices_from_now]
        current_temp = float(self.get_state(self.config["temperature_sensor"]))
        horizon = min(len(real_prices), HORIZON)
        u = solve_mpc(horizon, MIN_TEMP, MAX_TEMP, HEATING_RATE, COOLING_RATE, real_prices, current_temp)
        if not u:
            self.log("No valid schedule found. Do nothing.")
            return None
        action = u[0]
        schedule = u
        self.update_on_hours(schedule, offset=get_datetime_now().hour)
        self.log("Optimal heating actions: " + ", ".join(map(lambda x: str(int(x)), u)))
        return action
