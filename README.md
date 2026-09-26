# Supply Chain Management System for a Hospital

A command-line supply chain management system for a hospital. It forecasts demand for medical supplies, works out supplier costs, and plans distribution routes that stay within a budget and the current stock level.

This was built as a Design and Analysis of Algorithms (DAA) project at SRM Institute of Science and Technology, Kattankulathur (November 2023), under the guidance of Dr. Rajkumar K, Department of Data Science and Business Systems.

**Team**

- Aditii Sharma (RA2211027010093)
- Parth Bhunia (RA2211027010096)
- Arnav Gupta (RA2211027010125)

## Features

- **Order input:** item ID, quantity and priority (1–5) for each order.
- **Supplier input:** supplier ID, name and price per unit (INR).
- **Demand forecasting:** reads a forecasted quantity for each item.
- **Cost optimisation:** computes each supplier's total price for the forecasted demand.
- **Route planning (greedy):** chooses which orders to distribute, highest priority first, within the maximum budget and current stock.

## Running it

Requires Python 3 and no third-party packages.

```bash
python main.py
```

The program prompts for every value. To replay the example from the project report:

```bash
python main.py < sample_input.txt
```

### Example

Input (from `sample_input.txt`):

| Item ID | Quantity | Priority | Forecasted quantity |
|---|---|---|---|
| 101 | 50 | 4 | 60 |
| 102 | 30 | 5 | 35 |
| 103 | 20 | 3 | 25 |

Suppliers: 201 Supplier A at ₹10.50/unit and 202 Supplier B at ₹12.00/unit. Maximum budget ₹1500, current stock 100.

Output:

```
Selected Distribution Routes:
Item ID: 102, Forecasted Quantity: 35, Priority: 5
Item ID: 101, Forecasted Quantity: 60, Priority: 4
Item ID: 103, Forecasted Quantity: 25, Priority: 3
```

All three orders fit: at the cheapest unit price (₹10.50) they cost ₹367.50 + ₹630.00 + ₹262.50 = ₹1260, which is under the ₹1500 budget.

## Algorithm: greedy route planning

`route_planning` in [main.py](main.py):

1. Sort orders by priority, highest first.
2. Start with an empty list of distribution routes and zero cost.
3. For each order, price its forecasted quantity at the cheapest supplier's unit price.
4. Add the order if the running cost stays within the maximum budget and the current stock covers its forecasted quantity.
5. Return the selected routes.

### Time complexity

| Case | Complexity | Reason |
|---|---|---|
| Best | O(n log n) | Sorting the orders by priority |
| Average | O(n log n) | Sorting the orders by priority |
| Worst | O(n log n) | Sorting the orders by priority |

Here n is the number of orders. The loop also finds the cheapest supplier for each order, which adds O(n·m) for m suppliers; with few suppliers the sort dominates.

### Compared with other approaches

| Approach | Time complexity | Notes |
|---|---|---|
| Greedy (used here) | O(n log n) | Fast and simple; gives a good but not always optimal selection |
| Dynamic programming | O(n²) to O(2ⁿ) | Can find the optimal selection, but needs well-defined overlapping subproblems |
| Branch and bound | O(bᵈ) worst case, polynomial with good pruning | Optimal; cost depends on how well branches are pruned |

Greedy suits quick, approximate answers on small and medium inputs. Dynamic programming or branch and bound are the choice when the selection must be optimal and the extra computation is acceptable.

## Repository layout

```
.
├── main.py             # the program
├── sample_input.txt    # example input from the report
└── docs/
    ├── DAA_PROJECT(93,96,125).docx    # project report
    └── DAA ppt project(93,96,125).pptx # presentation
```
