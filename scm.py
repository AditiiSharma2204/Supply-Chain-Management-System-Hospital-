"""Core supply chain logic shared by the CLI (main.py) and the web app.

Orders and suppliers are plain dicts, as in the original project:
    order    = {'item_id', 'quantity', 'priority', 'forecasted_quantity', ...}
    supplier = {'supplier_id', 'supplier_name', 'price_per_unit_inr', ...}
"""

import math
from dataclasses import dataclass, field

# Money is compared with a tiny tolerance so that, e.g., 3 units at Rs 0.10
# fit a Rs 0.30 budget despite floating-point rounding (0.1 * 3 > 0.3).
EPS = 1e-9

# ----------------------------------------------------------------------
# Supplier costs
# ----------------------------------------------------------------------


def cheapest_supplier(suppliers):
    if not suppliers:
        raise ValueError("At least one supplier is needed to price orders.")
    return min(suppliers, key=lambda s: s['price_per_unit_inr'])


def supplier_costs(orders, suppliers):
    """Total price (INR) of the whole forecasted demand at each supplier."""
    demand = sum(order['forecasted_quantity'] for order in orders)
    return [{**s, 'total_price_inr': demand * s['price_per_unit_inr']} for s in suppliers]


# ----------------------------------------------------------------------
# Route planning
# ----------------------------------------------------------------------


@dataclass
class Plan:
    selected: list
    skipped: list = field(default_factory=list)  # (order, reason) pairs
    unit_price: float = 0.0
    total_cost: float = 0.0
    stock_left: int = 0

    @property
    def total_priority(self):
        return sum(order['priority'] for order in self.selected)

    @property
    def total_units(self):
        return sum(order['forecasted_quantity'] for order in self.selected)


def greedy_route_planning(orders, suppliers, max_budget, current_stock):
    """Highest priority first; take each order that fits the budget and stock.

    O(n log n) for the sort. This is the algorithm from the original project.
    """
    unit_price = cheapest_supplier(suppliers)['price_per_unit_inr']
    sorted_orders = sorted(orders, key=lambda x: x['priority'], reverse=True)
    current_cost = 0
    selected, skipped = [], []

    for order in sorted_orders:
        cost = order['forecasted_quantity'] * unit_price
        if current_cost + cost > max_budget + EPS:
            skipped.append((order, 'Over budget'))
        elif current_stock < order['forecasted_quantity']:
            skipped.append((order, 'Not enough stock'))
        else:
            current_cost += cost
            current_stock -= order['forecasted_quantity']
            selected.append(order)

    return Plan(selected, skipped, unit_price, current_cost, current_stock)


def unit_capacity(max_budget, current_stock, unit_price):
    """Most units that fit both the budget and the stock."""
    if unit_price <= 0:
        return max(current_stock, 0)
    affordable = math.floor(max_budget / unit_price)
    while affordable > 0 and affordable * unit_price > max_budget + EPS:  # guard float rounding
        affordable -= 1
    while (affordable + 1) * unit_price <= max_budget + EPS:
        affordable += 1
    return max(min(affordable, current_stock), 0)


def optimal_route_planning(orders, suppliers, max_budget, current_stock):
    """Exact selection that maximises total priority served (0/1 knapsack).

    Every unit costs the cheapest supplier's price, so the budget and stock
    limits combine into one capacity in units. Because priorities are small
    (1-5), a DP over total priority - "fewest units needed to reach priority
    v" - runs in O(n * total_priority) regardless of how large the stock is.
    Ties are broken by using fewer units (and so less money).
    """
    unit_price = cheapest_supplier(suppliers)['price_per_unit_inr']
    capacity = unit_capacity(max_budget, current_stock, unit_price)
    max_value = sum(o['priority'] for o in orders)
    INF = float('inf')

    min_units = [0] + [INF] * max_value
    take = []  # take[i][v]: order i is used in the best way to reach value v
    for order in orders:
        w, p = order['forecasted_quantity'], order['priority']
        row = [False] * (max_value + 1)
        for v in range(max_value, p - 1, -1):
            if min_units[v - p] + w < min_units[v]:
                min_units[v] = min_units[v - p] + w
                row[v] = True
        take.append(row)

    best = max(v for v in range(max_value + 1) if min_units[v] <= capacity)
    chosen, v = set(), best
    for i in range(len(orders) - 1, -1, -1):
        if take[i][v]:
            chosen.add(i)
            v -= orders[i]['priority']

    selected = sorted((orders[i] for i in chosen), key=lambda o: o['priority'], reverse=True)
    skipped = [(o, 'Not in optimal set') for i, o in enumerate(orders) if i not in chosen]
    units = sum(o['forecasted_quantity'] for o in selected)
    return Plan(selected, skipped, unit_price, units * unit_price, current_stock - units)


# ----------------------------------------------------------------------
# Demand forecasting
# ----------------------------------------------------------------------


def moving_average(history, window=3):
    recent = history[-window:]
    return sum(recent) / len(recent)


def exponential_smoothing(history, alpha=0.5):
    level = history[0]
    for value in history[1:]:
        level = alpha * value + (1 - alpha) * level
    return level


def linear_trend(history):
    """Least-squares line through the history, extended one period ahead."""
    n = len(history)
    if n < 2:
        return history[0]
    mean_x, mean_y = (n - 1) / 2, sum(history) / n
    sxx = sum((x - mean_x) ** 2 for x in range(n))
    slope = sum((x - mean_x) * (y - mean_y) for x, y in enumerate(history)) / sxx
    return mean_y + slope * (n - mean_x)


FORECAST_METHODS = {
    'Moving average': moving_average,
    'Exponential smoothing': exponential_smoothing,
    'Linear trend': linear_trend,
}


def forecast(history, method='Moving average', **params):
    """Next-period demand as a whole, non-negative number of units."""
    if not history:
        raise ValueError("Demand history is empty.")
    return max(0, math.ceil(round(FORECAST_METHODS[method](list(history), **params), 6)))
