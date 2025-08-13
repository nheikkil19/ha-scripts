from generic_heating_optimizer import GenericHeatingOptimizer, get_datetime_now
from mpc_raw import solve_mpc

# Ideas for improvement:
# - Update every 15 minutes
# - Add override boolean. If boolean is on, script will not change the state. State is controlled by other automation.

HORIZON = 32
MIN_TEMP = 23
MAX_TEMP = 27
COOLING_RATE = 0.25  # °C/h
HEATING_RATE = 0.6  # °C/h


class MpcHeating(GenericHeatingOptimizer):

    def initialize(self):
        super().initialize()

    def update_state(self) -> bool:
        self.optimizer = self.__class__.__name__
        action = self.get_next_action_cvxpy()
        if action is None:
            self.log("No valid schedule found. Do nothing.")
            return None
        # Turn on/off the switch based on the first hour of the schedule
        return action

    def get_next_action_cvxpy(self):
        # Get prices
        prices = self.get_prices(tomorrow=True)
        prices_from_now = prices[get_datetime_now().hour:get_datetime_now().hour + HORIZON]
        real_prices = [self.calculate_real_price(price) for price in prices_from_now]
        self.log(f"Real prices: {[round(x, 3) for x in real_prices]}")

        # Update horizon
        horizon = min(len(real_prices), HORIZON)
        self.set_mpc_details(horizon)
        # Get MPC parameters
        min_temp = self.get_float_from_mpc_sensor("mpc_min_temp", MIN_TEMP)
        max_temp = self.get_float_from_mpc_sensor("mpc_max_temp", MAX_TEMP)
        heating_rate = self.get_float_from_mpc_sensor("mpc_heating_rate", HEATING_RATE)
        cooling_rate = self.get_float_from_mpc_sensor("mpc_cooling_rate", COOLING_RATE)
        self.log(
            f"Using MPC with min_temp: {min_temp}, max_temp: {max_temp}, heating_rate: {heating_rate}, "
            f"cooling_rate: {cooling_rate}, horizon: {horizon}"
        )
        # Get current temperature
        current_temp = float(self.get_state(self.config["temperature_sensor"]))
        self.log(f"Current temp: {current_temp} degree C")
        if current_temp < min_temp:
            self.log("Current temperature is below minimum. Force heating on.")
            u = [1]
        elif max_temp < current_temp:
            self.log("Current temperature is above maximum. Force heating off.")
            u = [0]
        else:
            u = solve_mpc(horizon, min_temp, max_temp, heating_rate, cooling_rate, real_prices, current_temp)
        if not u:
            return None
        action = u[0]
        schedule = u
        self.update_on_hours(schedule, offset=get_datetime_now().hour)
        self.log("Optimal heating actions: " + ", ".join(map(lambda x: str(int(x)), u)))
        return action

    def set_mpc_details(self, horizon: int = HORIZON):
        self.details = "MPC with Horizon " + str(horizon)

    def get_float_from_mpc_sensor(self, sensor_name: str, default: float = 0.0) -> float:
        sensor = self.config.get(sensor_name, None)
        if sensor is not None:
            value: str = self.get_state(sensor, default=default)
            value = float(value.replace(",", "."))
            return value
        return default


# Continue from stash
