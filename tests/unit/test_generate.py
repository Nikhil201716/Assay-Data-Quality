"""The generator must be deterministic -- same seed, same data -- or nothing
downstream reproduces."""

from pipeline.generate import generate


def test_generation_is_deterministic():
    a = generate()
    b = generate()
    assert a == b


def test_clean_data_shapes():
    s = generate()
    assert len(s["customers"]) == 40
    assert len(s["products"]) == 25
    assert len(s["orders"]) == 300
    # every order references a real customer and product
    cids = {c["id"] for c in s["customers"]}
    pids = {p["id"] for p in s["products"]}
    for o in s["orders"]:
        assert o["customer_id"] in cids
        assert o["product_id"] in pids
        assert 1 <= o["quantity"] <= 20
        assert o["unit_price"] > 0
