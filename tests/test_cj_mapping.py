"""Test unitario puro (sin red) del parseo de /product/list de CJdropshipping.

Fixture basada en una respuesta real de /product/list (keyword "wireless earbuds").
"""
from matching.cj_client import build_product_url, parse_product_list

SAMPLE_RESPONSE = {
    "code": 200,
    "result": True,
    "data": {
        "list": [
            {
                "pid": "2100554014971047937",
                "productName": "[\"Wireless\",\" Headsets\",\" In-Ear\"]",
                "productNameEn": "Wireless Headsets In-Ear Neckband Headphones Sweat-proof Sport Earbuds",
                "productImage": "https://cf.cjdropshipping.com/doba-import/57368360.jpg",
                "sellPrice": "24.84",
                "isFreeShipping": False,
            },
            {
                "pid": "2100538775273648129",
                "productNameEn": "Portable Wireless Party Speaker 8in Colorful Lights",
                "sellPrice": "66.79",
                "isFreeShipping": True,
            },
            {
                # sin pid -> se descarta
                "productNameEn": "Producto roto sin pid",
                "sellPrice": "9.99",
            },
            {
                "pid": "999",
                "productNameEn": "Producto con precio invalido",
                "sellPrice": None,
            },
        ]
    },
}


def test_parse_product_list_maps_fields_and_url():
    products = parse_product_list(SAMPLE_RESPONSE)
    by_pid = {p["pid"]: p for p in products}

    assert set(by_pid) == {"2100554014971047937", "2100538775273648129"}

    p = by_pid["2100554014971047937"]
    assert p["price"] == 24.84
    assert p["title"].startswith("Wireless Headsets")
    assert p["is_free_shipping"] is False
    assert p["url"] == build_product_url("2100554014971047937")


def test_parse_product_list_skips_missing_pid_or_price():
    products = parse_product_list(SAMPLE_RESPONSE)
    titles = {p["title"] for p in products}
    assert "Producto roto sin pid" not in titles
    assert "Producto con precio invalido" not in titles
