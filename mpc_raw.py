"""
Solves MPC (Model Predictive Control) for heating optimization.
"""

import cvxpy as cp
import numpy as np


# Variables
def solve_mpc(
    H: int, T_min: float, T_max: float, heating_rate: float, cooling_rate: float, price_list: list, T_initial: float
) -> list:
    T = cp.Variable(H)  # Temperatures over the horizon
    u = cp.Variable(H, boolean=True)  # Heating actions (binary: 0 or 1)
    price = np.array(price_list)

    # Objective function: Minimize energy cost + comfort cost
    cost = cp.sum(cp.multiply(price, u))  # Use elementwise multiplication

    # Constraints
    constraints = []
    constraints += [T[0] == T_initial]  # Initial temperature
    for t in range(H - 1):
        # Next state is current state + heating if heating is on, -cooling if off
        constraints += [T[t + 1] == T[t] + heating_rate * u[t] - cooling_rate * (1 - u[t])]
    constraints += [T_min <= T, T <= T_max]  # Temperature bounds

    # Solve the problem
    prob = cp.Problem(cp.Minimize(cost), constraints)
    prob.solve(solver=cp.GLPK_MI)  # Use a solver that supports mixed-integer programming

    return u.value.tolist()


if __name__ == "__main__":
    # Problem data
    H = 24  # Prediction horizon (e.g., 24 hours)
    T_min, T_max = 20, 24  # Temperature bounds
    heating_rate = 0.5  # Temperature increase per hour when heating
    cooling_rate = 0.3  # Temperature decrease per hour when not heating
    price = np.random.rand(H)  # Electricity prices for the next 24 hours
    T_initial = 21  # Initial temperature

    solve_mpc(H, T_min, T_max, heating_rate, cooling_rate, price, T_initial)
