from datetime import time

from generic_heating_optimizer import GenericHeatingOptimizer
from programs import BaseProgram, Sections, TotalCheapest

ENABLED = False


class HeatingOptimizer(GenericHeatingOptimizer):

    def initialize(self):
        super().initialize()

        self.select_daily_program({})
        self.run_daily(
            self.select_daily_program,
            start=time(0, 0, 30),
            constrain_input_boolean=self.input_boolean_name,
        )

    def update_state(self, kwargs):
        if self.get_state(self.input_boolean_name) == "off" or not ENABLED:
            self.log("Automation is off or disabled. Do nothing.")
            return

        self.select_daily_program({})  # In case update was not successful earlier
        if self.should_turn_on() and self.get_state(self.input_boolean_name) == "on":
            self.switch_turn_on()
        else:
            self.switch_turn_off()

    def select_daily_program(self, kwargs):
        todays_prices = self.get_prices()
        min_cost = float("inf")
        selected_schedule = None

        for program in self.get_programs(todays_prices):
            schedule, cost = program.evaluate()
            cost *= self.config.get("cost_multiplier", 1)
            self.log(f"{program.name} cost: {cost}")

            if cost < min_cost:
                min_cost = cost
                selected_schedule = schedule
                selected_name = program.name

        self.log(f"Selected program: {selected_name}")
        self.schedule = selected_schedule

        on_hours = self.get_on_hours(self.schedule)
        self.print_schedule(on_hours)
        self.update_optimizer_information(on_hours, self.__class__.__name__, selected_name, min_cost)

    def should_turn_on(self) -> bool:
        current_hour = self.get_datetime_now().hour
        return self.schedule[current_hour]

    def get_programs(self, prices: list) -> list[BaseProgram]:
        programs = self.config["programs"]
        offset = self.config.get("offset", 0)
        prices = [price + offset for price in prices]
        ret = []
        for program in programs:
            if program["type"] == "total_cheapest":
                ret.append(TotalCheapest(prices, program["n"]))
            elif program["type"] == "section":
                ret.append(Sections(prices, program["section_lengths"], program["on_hours"]))
            else:
                raise ValueError(f"Unknown program type: {program['type']}")
        return ret
