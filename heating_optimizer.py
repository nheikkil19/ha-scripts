from datetime import time

from generic_heating_optimizer import GenericHeatingOptimizer
from programs import BaseProgram, Sections, TotalCheapest


class HeatingOptimizer(GenericHeatingOptimizer):

    def initialize(self):
        super().initialize()
        self.listen_state(self.automation_state_changed, self.input_boolean_name)

        self.select_daily_program({})
        self.run_daily(
            self.select_daily_program,
            start=time(0, 0, 30),
            constrain_input_boolean=self.input_boolean_name,
        )
        self.update_state({})
        self.run_hourly(self.update_state, start=self.start)

    def update_state(self, kwargs):
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
        self.print_schedule(self.schedule)

        self.update_data(selected_schedule, selected_name, min_cost)

    def should_turn_on(self) -> bool:
        current_hour = self.get_datetime_now().hour
        return self.schedule[current_hour]

    def print_schedule(self, schedule: list[bool]):
        log_str = "On hours: "
        for i, on in enumerate(schedule):
            if on:
                log_str += f"{i}, "
        log_str = log_str[:-2]
        self.log(log_str)

    def update_data(self, schedule, name, total_cost):
        sensor_name = self.config["optimizer_sensor"]
        state = "on" if self.get_state(self.input_boolean_name) == "on" else "off"
        on_hours = [i for i, on in enumerate(schedule) if on]
        self.set_state(
            sensor_name,
            state=state,
            attributes={"name": name, "total_cost": total_cost, "on_hours": on_hours},
        )

    def automation_state_changed(self, entity, attribute, old, new, kwargs):
        if new == "on":
            self.select_daily_program({})
            self.log("Automation turned on")
            self.update_state({})
        else:
            self.log("Automation turned off")
            self.switch_turn_off()

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
