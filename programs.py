from abc import ABC, abstractmethod


class BaseProgram(ABC):
    def __init__(self, prices: list):
        self._prices = prices
        self._name = ""

    @abstractmethod
    def evaluate(self) -> list[bool]:
        pass

    @property
    def name(self) -> str:
        return self._name


class TotalCheapest(BaseProgram):
    def __init__(self, prices: list, n: int):
        # raise NotImplementedError("Implement me!")
        super().__init__(prices)
        self._on_hours = n
        self._name = "TotalCheapest"

    def evaluate(self) -> tuple[list[bool], int]:
        schedule = [False] * len(self._prices)
        sorted_prices = sorted(self._prices)
        if self._on_hours <= 0:
            return schedule, 0
        elif len(sorted_prices) < self._on_hours:
            return [True] * len(schedule), sum(sorted_prices)
        nth_cheapest = sorted_prices[self._on_hours - 1]
        cost = 0
        count = 0
        for i, price in enumerate(self._prices):
            if count == self._on_hours:
                break
            if price <= nth_cheapest:
                cost += price
                count += 1
                schedule[i] = True
        return schedule, cost

class Sections(BaseProgram):
    def __init__(self, prices: list, section_lengths: list, on_hours: list):
        super().__init__(prices)
        if sum(section_lengths) != len(prices):
            raise ValueError("Sum of section lengths must be equal to the number of prices")
        if len(on_hours) != len(section_lengths):
            raise ValueError("Need to specify on hours for each section length")

        self._section_lengths = section_lengths
        self._on_hours = on_hours
        self._name = "Sections"

    def evaluate(self) -> tuple[list[bool], int]:
        schedule = [False] * len(self._prices)

        total_cost = 0
        previous_section_end = 0
        for section_length, on_hour in zip(self._section_lengths, self._on_hours):
            section_prices = self._prices[
                previous_section_end : previous_section_end + section_length
            ]
            section = TotalCheapest(section_prices, on_hour)
            section_schedule, cost = section.evaluate()
            for i, on in enumerate(section_schedule):
                schedule[previous_section_end + i] = on
            previous_section_end += section_length
            total_cost += cost
        return schedule, total_cost
