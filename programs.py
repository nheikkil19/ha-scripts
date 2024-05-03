from abc import ABC, abstractmethod


class BaseProgram(ABC):
    def __init__(self, prices: list):
        self.prices = prices

    @abstractmethod
    def evaluate(self) -> list[bool]:
        pass


class TotalCheapest(BaseProgram):
    def __init__(self, prices: list, n: int):
        super().__init__(prices)
        self.n = n

    def evaluate(self) -> tuple[list[bool], int]:
        schedule = [False] * len(self.prices)
        nth_cheapest = sorted(self.prices)[self.n - 1] if self.n > 0 else -float("inf")
        cost = 0
        count = 0
        for i, price in enumerate(self.prices):
            if count == self.n:
                break
            if price <= nth_cheapest:
                cost += price
                count += 1
                schedule[i] = True
        return schedule, cost


class Sections(BaseProgram):
    def __init__(self, prices: list, section_lengths: list, on_hours: list):
        super().__init__(prices)
        if sum(section_lengths) != 24:
            raise ValueError("Sum of section lengths must be 24")
        if len(on_hours) != len(section_lengths):
            raise ValueError("Need to specify on hours for each section length")

        self.section_lengths = section_lengths
        self.on_hours = on_hours

    def evaluate(self) -> tuple[list[bool], int]:
        schedule = [False] * len(self.prices)

        total_cost = 0
        previous_section_end = 0
        for section_length, on_hour in zip(self.section_lengths, self.on_hours):
            section_prices = self.prices[
                previous_section_end : previous_section_end + section_length
            ]
            section = TotalCheapest(section_prices, on_hour)
            section_schedule, cost = section.evaluate()
            for i, on in enumerate(section_schedule):
                schedule[previous_section_end + i] = on
            previous_section_end += section_length
            total_cost += cost
        return schedule, total_cost
