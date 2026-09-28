"""Seeded synthetic sources for the retail-orders pipeline, with known-clean
ground truth so injected defects can be scored against a right answer.

Three source tables -- customers, products, orders -- generated deterministically
from a fixed seed. The clean data satisfies every quality rule; the defect
injector mutates a copy to introduce exactly one realistic data defect at a time.
"""

from __future__ import annotations

import copy
import random

SEED = 20260928
COUNTRIES = ["US", "UK", "DE", "IN", "JP", "CA", "AU", "FR"]
CATEGORIES = ["books", "kitchen", "electronics", "toys", "garden"]
N_CUSTOMERS = 40
N_PRODUCTS = 25
N_ORDERS = 300


def generate() -> dict:
    """Return clean source tables as {'customers': [...], 'products': [...], 'orders': [...]}."""
    rng = random.Random(SEED)

    customers = []
    for i in range(1, N_CUSTOMERS + 1):
        customers.append({
            "id": i,
            "name": f"Customer {i}",
            "email": f"customer{i}@example.com",
            "country": rng.choice(COUNTRIES),
            "signup_date": f"20{rng.randint(18, 25):02d}-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}",
        })

    products = []
    for i in range(1, N_PRODUCTS + 1):
        products.append({
            "id": i,
            "name": f"Product {i}",
            "category": rng.choice(CATEGORIES),
            "price": round(rng.uniform(5.0, 200.0), 2),
        })

    orders = []
    for i in range(1, N_ORDERS + 1):
        prod = rng.choice(products)
        orders.append({
            "id": i,
            "customer_id": rng.randint(1, N_CUSTOMERS),
            "product_id": prod["id"],
            "quantity": rng.randint(1, 20),
            "unit_price": prod["price"],           # price snapshot at order time
            "order_date": f"2026-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}",
        })

    return {"customers": customers, "products": products, "orders": orders}


def clone(sources: dict) -> dict:
    return copy.deepcopy(sources)
