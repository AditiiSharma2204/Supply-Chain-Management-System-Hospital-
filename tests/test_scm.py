import itertools
import random
import subprocess
import sys
from pathlib import Path

import pytest

from scm import (
    cheapest_supplier,
    exponential_smoothing,
    forecast,
    greedy_route_planning,
    linear_trend,
    moving_average,
    optimal_route_planning,
    supplier_costs,
    unit_capacity,
)

ROOT = Path(__file__).resolve().parent.parent

SUPPLIERS = [
    {'supplier_id': 201, 'supplier_name': 'Supplier A', 'price_per_unit_inr': 10.5},
    {'supplier_id': 202, 'supplier_name': 'Supplier B', 'price_per_unit_inr': 12.0},
]


def make_orders():
    return [
        {'item_id': 101, 'quantity': 50, 'priority': 4, 'forecasted_quantity': 60},
        {'item_id': 102, 'quantity': 30, 'priority': 5, 'forecasted_quantity': 35},
        {'item_id': 103, 'quantity': 20, 'priority': 3, 'forecasted_quantity': 25},
    ]


def test_report_example_greedy():
    plan = greedy_route_planning(make_orders(), SUPPLIERS, 1500, 100)
    assert [o['item_id'] for o in plan.selected] == [102, 101]
    assert plan.total_cost == pytest.approx(997.5)
    assert plan.stock_left == 5
    assert [(o['item_id'], reason) for o, reason in plan.skipped] == [(103, 'Not enough stock')]


def test_greedy_reports_budget_reason():
    plan = greedy_route_planning(make_orders(), SUPPLIERS, 400, 1000)
    assert [o['item_id'] for o in plan.selected] == [102]
    assert dict((o['item_id'], r) for o, r in plan.skipped) == {101: 'Over budget', 103: 'Over budget'}


def test_cheapest_supplier_and_costs():
    assert cheapest_supplier(SUPPLIERS)['supplier_id'] == 201
    costs = supplier_costs(make_orders(), SUPPLIERS)
    assert [c['total_price_inr'] for c in costs] == [pytest.approx(120 * 10.5), pytest.approx(120 * 12.0)]


def test_no_suppliers_is_an_error():
    with pytest.raises(ValueError):
        greedy_route_planning(make_orders(), [], 100, 100)


def test_unit_capacity():
    assert unit_capacity(1500, 100, 10.5) == 100
    assert unit_capacity(1500, 1000, 10.5) == 142      # 142 * 10.5 = 1491
    assert unit_capacity(0.3, 10, 0.1) == 3            # float rounding guard
    assert unit_capacity(100, 0, 1) == 0


def test_greedy_accepts_order_costing_exactly_the_budget():
    order = {'item_id': 1, 'priority': 3, 'forecasted_quantity': 3}
    supplier = {'supplier_id': 1, 'supplier_name': 'S', 'price_per_unit_inr': 0.1}
    assert greedy_route_planning([order], [supplier], 0.3, 10).selected == [order]


def test_optimal_beats_greedy_when_greedy_is_myopic():
    orders = [
        {'item_id': 1, 'priority': 5, 'forecasted_quantity': 60},
        {'item_id': 2, 'priority': 4, 'forecasted_quantity': 50},
        {'item_id': 3, 'priority': 4, 'forecasted_quantity': 50},
    ]
    suppliers = [{'supplier_id': 1, 'supplier_name': 'S', 'price_per_unit_inr': 1.0}]
    greedy = greedy_route_planning(orders, suppliers, 1000, 100)
    optimal = optimal_route_planning(orders, suppliers, 1000, 100)
    assert greedy.total_priority == 5
    assert optimal.total_priority == 8
    assert {o['item_id'] for o in optimal.selected} == {2, 3}
    assert optimal.stock_left == 0


def brute_force_best(orders, capacity):
    best = (0, 0)  # (priority, -units)
    for r in range(len(orders) + 1):
        for combo in itertools.combinations(orders, r):
            units = sum(o['forecasted_quantity'] for o in combo)
            if units <= capacity:
                best = max(best, (sum(o['priority'] for o in combo), -units))
    return best


@pytest.mark.parametrize('seed', range(40))
def test_optimal_matches_brute_force(seed):
    rng = random.Random(seed)
    orders = [
        {'item_id': i, 'priority': rng.randint(1, 5), 'forecasted_quantity': rng.randint(0, 80)}
        for i in range(rng.randint(1, 9))
    ]
    price = rng.choice([0.5, 1.0, 7.25, 10.5])
    suppliers = [{'supplier_id': 1, 'supplier_name': 'S', 'price_per_unit_inr': price}]
    budget, stock = rng.uniform(0, 600), rng.randint(0, 300)

    plan = optimal_route_planning(orders, suppliers, budget, stock)
    capacity = unit_capacity(budget, stock, price)
    assert (plan.total_priority, -plan.total_units) == brute_force_best(orders, capacity)
    assert plan.total_cost <= budget + 1e-9
    assert plan.stock_left >= 0
    assert plan.total_priority >= greedy_route_planning(orders, suppliers, budget, stock).total_priority


def test_forecasting_methods():
    history = [10, 20, 30, 40]
    assert moving_average(history, 2) == 35
    assert exponential_smoothing(history, 1.0) == 40
    assert exponential_smoothing([10, 20], 0.5) == 15
    assert linear_trend(history) == pytest.approx(50)
    assert forecast(history, 'Linear trend') == 50
    assert forecast([5, 5, 5], 'Moving average', window=3) == 5
    assert forecast([30, 20, 10, 0], 'Linear trend') == 0   # never negative
    with pytest.raises(ValueError):
        forecast([], 'Moving average')


def test_cli_reproduces_report_output():
    result = subprocess.run(
        [sys.executable, 'main.py'],
        input=(ROOT / 'sample_input.txt').read_text(),
        capture_output=True, text=True, cwd=ROOT, check=True,
    )
    assert result.stdout.endswith(
        "Selected Distribution Routes:\n"
        "Item ID: 102, Forecasted Quantity: 35, Priority: 5\n"
        "Item ID: 101, Forecasted Quantity: 60, Priority: 4\n"
    )
