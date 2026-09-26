"""Hospital Supply Chain Management - interactive Streamlit dashboard.

Run with:  streamlit run streamlit_app.py
"""

import datetime as dt

import altair as alt
import pandas as pd
import streamlit as st

from scm import (
    FORECAST_METHODS,
    forecast,
    greedy_route_planning,
    optimal_route_planning,
    supplier_costs,
)

st.set_page_config(page_title="Hospital Supply Chain", page_icon="🏥", layout="wide")

TEAL, TEAL_LIGHT, GREY, AMBER = "#0F766E", "#5EEAD4", "#CBD5E1", "#F59E0B"

st.markdown(
    """
    <style>
      .block-container { padding-top: 2rem; }
      .hero {
        background: linear-gradient(120deg, #0F766E 0%, #115E59 55%, #134E4A 100%);
        color: #fff; border-radius: 16px; padding: 1.6rem 2rem; margin-bottom: 1.2rem;
      }
      .hero h1 { color: #fff; margin: 0; font-size: 2rem; }
      .hero p { margin: .35rem 0 0; opacity: .9; }
      [data-testid="stMetric"] {
        background: #F0FDFA; border: 1px solid #CCFBF1;
        border-radius: 12px; padding: .8rem 1rem;
      }
      .pill { display: inline-block; padding: .1rem .6rem; border-radius: 999px;
              font-size: .8rem; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------
# Sample data
# ----------------------------------------------------------------------

PRESETS = {
    "Project report example": {
        "orders": [
            (101, "Surgical gloves (box)", 50, 4, 60),
            (102, "N95 masks (box)", 30, 5, 35),
            (103, "IV saline 500 ml", 20, 3, 25),
        ],
        "suppliers": [(201, "Supplier A", 10.5), (202, "Supplier B", 12.0)],
        "budget": 1500.0,
        "stock": 100,
    },
    "City hospital (10 items)": {
        "orders": [
            (101, "Surgical gloves (box)", 120, 4, 130),
            (102, "N95 masks (box)", 90, 5, 110),
            (103, "IV saline 500 ml", 200, 5, 220),
            (104, "Syringes 5 ml (pack)", 150, 3, 140),
            (105, "Gauze rolls", 80, 2, 75),
            (106, "Paracetamol 500 mg (strip)", 300, 3, 320),
            (107, "Insulin vials", 40, 5, 45),
            (108, "Blood bags", 60, 4, 70),
            (109, "Disinfectant 5 L", 25, 2, 30),
            (110, "Oxygen masks", 70, 4, 65),
        ],
        "suppliers": [(201, "MedLine India", 18.0), (202, "CarePlus Pharma", 16.5), (203, "HealthKart B2B", 17.25)],
        "budget": 10000.0,
        "stock": 900,
    },
}

ORDER_COLUMNS = ["Item ID", "Item", "Quantity", "Priority", "Forecast"]
SUPPLIER_COLUMNS = ["ID", "Supplier", "₹/unit"]
MONTHS = 6


def month_labels(n=MONTHS):
    first = dt.date.today().replace(day=1)
    labels = []
    for i in range(n, 0, -1):
        year, month = divmod(first.month - 1 - i, 12)
        labels.append(dt.date(first.year + year, month + 1, 1).strftime("%b %Y"))
    return labels


def sample_history(item_id, base):
    """Six months of plausible usage around `base`, same every run for an item."""
    pattern = [0.82, 0.9, 0.95, 0.88, 1.0, 1.07]
    shift = (item_id % 5) * 0.02
    return [max(0, round(base * (p + shift))) for p in pattern]


def load_preset(name):
    preset = PRESETS[name]
    st.session_state.orders = pd.DataFrame(preset["orders"], columns=ORDER_COLUMNS)
    st.session_state.suppliers = pd.DataFrame(preset["suppliers"], columns=SUPPLIER_COLUMNS)
    st.session_state.history = pd.DataFrame(
        [sample_history(r[0], r[2]) for r in preset["orders"]],
        index=[r[0] for r in preset["orders"]],
        columns=month_labels(),
    )
    st.session_state.budget = preset["budget"]
    st.session_state.stock = preset["stock"]
    st.session_state.version = st.session_state.get("version", 0) + 1


if "orders" not in st.session_state:
    load_preset("Project report example")

# ----------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------

with st.sidebar:
    st.header("⚙️ Scenario")
    preset = st.selectbox("Sample data", list(PRESETS))
    if st.button("Load sample data", use_container_width=True):
        load_preset(preset)
        st.rerun()

    st.divider()
    budget = st.number_input("Maximum budget (₹)", min_value=0.0, step=100.0, format="%.2f", key="budget")
    stock = st.number_input("Current stock (units)", min_value=0, step=10, key="stock")
    st.divider()
    st.caption(
        "Edit orders and suppliers in the first tab. Everything else updates instantly. "
        "Built as a Design and Analysis of Algorithms project at SRM IST."
    )

st.markdown(
    """
    <div class="hero">
      <h1>🏥 Hospital Supply Chain Management</h1>
      <p>Forecast demand for medical supplies, compare supplier costs, and plan which orders to
      distribute within the budget and stock - greedy vs. optimal.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_data, tab_forecast, tab_costs, tab_routes, tab_about = st.tabs(
    ["📋 Orders & suppliers", "📈 Demand forecast", "💰 Supplier costs", "🚚 Route planning", "ℹ️ About"]
)

# ----------------------------------------------------------------------
# Orders & suppliers
# ----------------------------------------------------------------------

with tab_data:
    left, right = st.columns([5, 3], gap="large")
    with left:
        st.subheader("Orders")
        orders_df = st.data_editor(
            st.session_state.orders,
            key=f"orders_editor_{st.session_state.version}",
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "Item ID": st.column_config.NumberColumn(min_value=1, step=1, required=True, width="small"),
                "Item": st.column_config.TextColumn(),
                "Quantity": st.column_config.NumberColumn("Qty", min_value=0, step=1, required=True),
                "Priority": st.column_config.NumberColumn(
                    min_value=1, max_value=5, step=1, required=True, help="5 = most urgent", width="small"
                ),
                "Forecast": st.column_config.NumberColumn(
                    "Forecast", min_value=0, step=1, help="Forecasted units needed next period", width="small"
                ),
            },
        )
    with right:
        st.subheader("Suppliers")
        suppliers_df = st.data_editor(
            st.session_state.suppliers,
            key=f"suppliers_editor_{st.session_state.version}",
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn(min_value=1, step=1, required=True, width="small"),
                "Supplier": st.column_config.TextColumn(required=True),
                "₹/unit": st.column_config.NumberColumn(
                    min_value=0.01, step=0.25, format="₹%.2f", required=True
                ),
            },
        )

# Clean the edited tables into the dict format the algorithms use.
orders_df = orders_df.dropna(subset=["Item ID", "Quantity", "Priority"]).copy()
orders_df["Forecast"] = orders_df["Forecast"].fillna(orders_df["Quantity"])
orders_df["Item"] = orders_df["Item"].fillna("").astype(str)
orders_df = orders_df.astype({"Item ID": int, "Quantity": int, "Priority": int, "Forecast": int})
suppliers_df = suppliers_df.dropna().copy()

problems = []
if orders_df.empty:
    problems.append("Add at least one order.")
if suppliers_df.empty:
    problems.append("Add at least one supplier with a price.")
if orders_df["Item ID"].duplicated().any():
    problems.append("Item IDs must be unique.")

orders = [
    {
        "item_id": int(r["Item ID"]),
        "item_name": r["Item"] or f"Item {int(r['Item ID'])}",
        "quantity": int(r["Quantity"]),
        "priority": int(r["Priority"]),
        "forecasted_quantity": int(r["Forecast"]),
    }
    for _, r in orders_df.iterrows()
]
suppliers = [
    {
        "supplier_id": int(r["ID"]),
        "supplier_name": str(r["Supplier"]),
        "price_per_unit_inr": float(r["₹/unit"]),
    }
    for _, r in suppliers_df.iterrows()
]

with tab_data:
    if problems:
        for p in problems:
            st.warning(p)
    else:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Orders", len(orders))
        c2.metric("Forecasted demand", f"{sum(o['forecasted_quantity'] for o in orders):,}")
        c3.metric("Suppliers", len(suppliers))
        c4.metric("Budget", f"₹{budget:,.0f}")
        c5.metric("Stock", f"{stock:,}")

if problems:
    for tab in (tab_forecast, tab_costs, tab_routes):
        with tab:
            st.info("Fix the orders and suppliers in the first tab to see this view.")
    st.stop()

# ----------------------------------------------------------------------
# Demand forecast
# ----------------------------------------------------------------------

with tab_forecast:
    history = st.session_state.history.reindex([o["item_id"] for o in orders])
    for o in orders:  # new items start with a flat history at the ordered quantity
        if history.loc[o["item_id"]].isna().all():
            history.loc[o["item_id"]] = [o["quantity"]] * MONTHS
    history = history.fillna(0).astype(int)

    st.caption("Past monthly usage per item (editable). Pick a method to forecast next month's demand.")
    c1, c2 = st.columns([1, 2], gap="large")
    with c1:
        method = st.radio("Forecasting method", list(FORECAST_METHODS), horizontal=False)
        params = {}
        if method == "Moving average":
            params["window"] = st.slider("Window (months)", 2, MONTHS, 3)
        elif method == "Exponential smoothing":
            params["alpha"] = st.slider("Smoothing factor α", 0.1, 0.9, 0.5, 0.1)
        names = {o["item_id"]: f"{o['item_id']} · {o['item_name']}" for o in orders}
        chosen = st.selectbox("Item to chart", list(names), format_func=names.get)

    history_edit = st.data_editor(
        history.rename(index=names),
        key=f"history_editor_{st.session_state.version}",
        use_container_width=True,
        column_config={m: st.column_config.NumberColumn(min_value=0, step=1) for m in history.columns},
    )
    history_edit.index = history.index
    history_edit = history_edit.fillna(0).astype(int)

    forecasts = {i: forecast(history_edit.loc[i].tolist(), method, **params) for i in history_edit.index}

    with c2:
        series = history_edit.loc[chosen]
        next_label = "Next month"
        chart_df = pd.DataFrame(
            {"Month": list(series.index) + [next_label], "Units": list(series.values) + [forecasts[chosen]],
             "Type": ["Actual"] * len(series) + ["Forecast"]}
        )
        order_of_months = list(series.index) + [next_label]
        base = alt.Chart(chart_df).encode(
            x=alt.X("Month:N", sort=order_of_months, title=None), y=alt.Y("Units:Q", title="Units used")
        )
        line = base.transform_filter(alt.datum.Type == "Actual").mark_line(point=True, color=TEAL, strokeWidth=3)
        bridge = alt.Chart(chart_df.tail(2)).mark_line(strokeDash=[6, 4], color=AMBER, strokeWidth=3).encode(
            x=alt.X("Month:N", sort=order_of_months), y="Units:Q"
        )
        point = base.transform_filter(alt.datum.Type == "Forecast").mark_point(
            size=160, filled=True, color=AMBER
        )
        label = base.transform_filter(alt.datum.Type == "Forecast").mark_text(
            dy=-16, fontWeight="bold", color=AMBER
        ).encode(text="Units:Q")
        st.altair_chart((line + bridge + point + label).properties(height=300), use_container_width=True)

    compare = pd.DataFrame(
        {
            "Item": [names[o["item_id"]] for o in orders],
            "Current forecast": [o["forecasted_quantity"] for o in orders],
            f"{method} forecast": [forecasts[o["item_id"]] for o in orders],
        }
    )
    compare["Change"] = compare.iloc[:, 2] - compare["Current forecast"]
    st.dataframe(compare, hide_index=True, use_container_width=True)

    if st.button(f"Use {method.lower()} forecasts for all orders", type="primary"):
        updated = orders_df.copy()
        updated["Forecast"] = updated["Item ID"].map(forecasts)
        st.session_state.orders = updated
        st.session_state.suppliers = suppliers_df
        st.session_state.history = history_edit
        st.session_state.version += 1
        st.toast("Forecasts applied to the orders.", icon="✅")
        st.rerun()

# ----------------------------------------------------------------------
# Supplier costs
# ----------------------------------------------------------------------

with tab_costs:
    costs = pd.DataFrame(supplier_costs(orders, suppliers)).sort_values("total_price_inr")
    best, worst = costs.iloc[0], costs.iloc[-1]
    demand = sum(o["forecasted_quantity"] for o in orders)

    saving = worst["total_price_inr"] - best["total_price_inr"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Cheapest supplier", best["supplier_name"])
    c1.caption(f"₹{best['price_per_unit_inr']:,.2f} per unit")
    c2.metric("Cost of forecasted demand", f"₹{best['total_price_inr']:,.2f}")
    c2.caption(f"{demand:,} units at the cheapest price")
    c3.metric("Saving vs. most expensive", f"₹{saving:,.2f}")
    if worst["total_price_inr"]:
        c3.caption(f"{saving / worst['total_price_inr']:.1%} cheaper than {worst['supplier_name']}")

    costs["Choice"] = ["Cheapest" if i == 0 else "Other" for i in range(len(costs))]
    costs["Label"] = costs["total_price_inr"].map(lambda v: f"₹{v:,.2f}")
    bars = alt.Chart(costs).mark_bar(cornerRadiusEnd=6, height=28).encode(
        x=alt.X("total_price_inr:Q", title="Total price for forecasted demand (₹)"),
        y=alt.Y("supplier_name:N", sort="x", title=None),
        color=alt.Color("Choice:N", scale=alt.Scale(domain=["Cheapest", "Other"], range=[TEAL, GREY]), legend=None),
        tooltip=[
            alt.Tooltip("supplier_name:N", title="Supplier"),
            alt.Tooltip("price_per_unit_inr:Q", title="Price / unit (₹)", format=",.2f"),
            alt.Tooltip("total_price_inr:Q", title="Total (₹)", format=",.2f"),
        ],
    )
    text = bars.mark_text(align="left", dx=6, fontWeight="bold").encode(text="Label:N", color=alt.value("#334155"))
    st.altair_chart((bars + text).properties(height=70 + 45 * len(costs)), use_container_width=True)
    st.caption("Route planning prices every order at the cheapest supplier's unit price.")

# ----------------------------------------------------------------------
# Route planning
# ----------------------------------------------------------------------

with tab_routes:
    greedy = greedy_route_planning(orders, suppliers, budget, stock)
    optimal = optimal_route_planning(orders, suppliers, budget, stock)
    total_priority = sum(o["priority"] for o in orders)

    st.markdown(
        f"Every unit is priced at **₹{greedy.unit_price:,.2f}** (cheapest supplier). "
        "**Greedy** takes orders from highest priority down, skipping any that don't fit. "
        "**Optimal** solves the 0/1 knapsack exactly to serve the most total priority."
    )

    def plan_metrics(col, title, plan, other=None):
        with col:
            st.markdown(f"#### {title}")
            m1, m2 = st.columns(2)
            better = other is not None and plan.total_priority != other.total_priority
            m1.metric(
                "Orders served",
                f"{len(plan.selected)} / {len(orders)}",
                f"{len(plan.selected) - len(other.selected):+d} vs greedy" if better else None,
            )
            m2.metric(
                "Priority served",
                f"{plan.total_priority} / {total_priority}",
                f"{plan.total_priority - other.total_priority:+d} vs greedy" if better else None,
            )
            m3, m4 = st.columns(2)
            m3.metric("Cost", f"₹{plan.total_cost:,.2f}")
            m4.metric("Stock left", f"{plan.stock_left:,} units")
            used = plan.total_cost / budget if budget else 0
            st.progress(min(used, 1.0), text=f"Budget used: {used:.0%}")

    g_col, o_col = st.columns(2, gap="large")
    plan_metrics(g_col, "Greedy (project algorithm)", greedy)
    plan_metrics(o_col, "Optimal (knapsack)", optimal, other=greedy)

    if optimal.total_priority > greedy.total_priority:
        st.success(
            f"The optimal plan serves **{optimal.total_priority - greedy.total_priority} more priority points** "
            "than greedy by choosing a different combination of orders - greedy can't undo an early choice "
            "that uses up budget or stock."
        )
    else:
        st.info("Greedy already finds an optimal selection for this scenario.")

    greedy_ids = {o["item_id"] for o in greedy.selected}
    optimal_ids = {o["item_id"] for o in optimal.selected}
    reasons = {o["item_id"]: r for o, r in greedy.skipped}

    rows = []
    for o in sorted(orders, key=lambda o: o["priority"], reverse=True):
        rows.append(
            {
                "Item ID": o["item_id"],
                "Item": o["item_name"],
                "Priority": o["priority"],
                "Forecasted qty": o["forecasted_quantity"],
                "Cost": f"₹{o['forecasted_quantity'] * greedy.unit_price:,.2f}",
                "Greedy": "✅ Selected" if o["item_id"] in greedy_ids else f"❌ {reasons[o['item_id']]}",
                "Optimal": "✅ Selected" if o["item_id"] in optimal_ids else "—",
            }
        )
    st.markdown("#### Distribution plan")
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Priority": st.column_config.ProgressColumn(min_value=0, max_value=5, format="%d"),
        },
    )

    # Running cost of the greedy plan against the budget.
    if greedy.selected:
        steps, running = [], 0.0
        for o in greedy.selected:
            running += o["forecasted_quantity"] * greedy.unit_price
            steps.append({"Step": f"{len(steps) + 1}. {o['item_name']}", "Running cost": running})
        steps_df = pd.DataFrame(steps)
        bars = alt.Chart(steps_df).mark_bar(color=TEAL, cornerRadiusEnd=4).encode(
            x=alt.X("Step:N", sort=None, title=None, axis=alt.Axis(labelAngle=-30, labelLimit=180)),
            y=alt.Y("Running cost:Q", title="Running cost (₹)"),
            tooltip=[alt.Tooltip("Step:N"), alt.Tooltip("Running cost:Q", title="Running cost (₹)", format=",.2f")],
        )
        rule = alt.Chart(pd.DataFrame({"Budget": [budget]})).mark_rule(color=AMBER, strokeDash=[6, 4], size=2).encode(
            y="Budget:Q"
        )
        st.markdown("#### Greedy: running cost vs. budget")
        st.altair_chart((bars + rule).properties(height=300), use_container_width=True)

    csv = pd.DataFrame(rows).to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download distribution plan (CSV)", csv, "distribution_plan.csv", "text/csv")

# ----------------------------------------------------------------------
# About
# ----------------------------------------------------------------------

with tab_about:
    st.markdown(
        """
        ### How it works

        1. **Orders** list each item's quantity, priority (1–5) and forecasted demand.
        2. **Demand forecasting** predicts next month's demand from past usage using a moving average,
           exponential smoothing or a linear trend.
        3. **Cost optimisation** prices the forecasted demand at every supplier and picks the cheapest.
        4. **Route planning** decides which orders to distribute within the budget and current stock.

        ### Algorithms

        | Approach | Time complexity | Result |
        |---|---|---|
        | Greedy by priority (original project) | O(n log n) | Fast, usually good, not always optimal |
        | 0/1 knapsack DP over total priority | O(n · P), P = sum of priorities ≤ 5n | Optimal |

        Because every unit costs the same (the cheapest supplier's price), the budget and stock limits combine
        into one capacity in units, which turns the selection into a 0/1 knapsack: weight = forecasted quantity,
        value = priority. Priorities are small, so the DP over total priority is fast even for large stock levels.

        ### Credits

        Design and Analysis of Algorithms project, SRM Institute of Science and Technology, Kattankulathur
        (November 2023), under the guidance of Dr. Rajkumar K.
        Team: **Aditii Sharma**, **Parth Bhunia**, **Arnav Gupta**.
        """
    )
