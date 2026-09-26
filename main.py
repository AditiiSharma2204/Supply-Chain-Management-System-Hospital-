class SupplyChainManagement:
    def __init__(self, orders, suppliers):
        self.orders = orders
        self.suppliers = suppliers

    def demand_forecasting(self):
        for order in self.orders:
            order['forecasted_quantity'] = int(input(f"Enter forecasted quantity for Item ID {order['item_id']}: "))

    def optimize_costs(self):
        for supplier in self.suppliers:
            total_cost = sum(order['forecasted_quantity'] * supplier['price_per_unit_inr'] for order in self.orders)
            supplier['total_price_inr'] = total_cost

    def route_planning(self, max_budget, current_stock):
        sorted_orders = sorted(self.orders, key=lambda x: x['priority'], reverse=True)
        current_cost = 0
        distribution_routes = []

        for order in sorted_orders:
            if current_cost + order['forecasted_quantity'] * min(supplier['price_per_unit_inr'] for supplier in self.suppliers) <= max_budget:
                if current_stock >= order['forecasted_quantity']:
                    current_cost += order['forecasted_quantity'] * min(supplier['price_per_unit_inr'] for supplier in self.suppliers)
                    distribution_routes.append(order)

        return distribution_routes

orders_data = []
num_orders = int(input("Enter the number of orders: "))

for i in range(num_orders):
    item_id = int(input(f"Enter Item ID for order {i+1}: "))
    quantity = int(input(f"Enter Quantity for order {i+1}: "))
    priority = int(input(f"Enter Priority (1-5) for order {i+1}: "))

    orders_data.append({'item_id': item_id, 'quantity': quantity, 'priority': priority})

suppliers_data = []
num_suppliers = int(input("Enter the number of suppliers: "))

for i in range(num_suppliers):
    supplier_id = int(input(f"Enter Supplier ID {i+1}: "))
    supplier_name = input(f"Enter Supplier Name {i+1}: ")
    price_per_unit_inr = float(input(f"Enter Price per Unit from Supplier {i+1} (in INR): "))

    suppliers_data.append({'supplier_id': supplier_id, 'supplier_name': supplier_name, 'price_per_unit_inr': price_per_unit_inr})

max_budget = float(input("Enter the maximum budget for suppliers (in INR): "))
current_stock = int(input("Enter the current stock quantity: "))

supply_chain = SupplyChainManagement(orders_data, suppliers_data)

supply_chain.demand_forecasting()
supply_chain.optimize_costs()

distribution_routes = supply_chain.route_planning(max_budget, current_stock)

print("\nSelected Distribution Routes:")
for route in distribution_routes:
    print(f"Item ID: {route['item_id']}, Forecasted Quantity: {route['forecasted_quantity']}, Priority: {route['priority']}")
