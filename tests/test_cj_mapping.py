"""Test unitario puro (sin red) del parseo de /product/listV2 de CJdropshipping.

Fixture basada en una respuesta real (keyword "stainless steel water bottle").
La respuesta viene anidada: data.content[].productList[].
"""
from matching.cj_client import build_product_url, parse_product_list

SAMPLE_RESPONSE = {
    "code": 200,
    "result": True,
    "data": {
        "content": [
            {
                "keyWord": "stainless steel water bottle",
                "productList": [
                    {
                        "id": "2100554014971047937",
                        "nameEn": "Stainless Steel Insulated Water Bottle with Straw",
                        "sku": "CJ001",
                        "bigImage": "https://cf.cjdropshipping.com/img1.jpg",
                        "sellPrice": "9.50",
                        "addMarkStatus": 1,
                    },
                    {
                        "id": "2100554099999999999",
                        "nameEn": "Silicone Folding Water Bottle",
                        "sellPrice": "3.28",
                        "addMarkStatus": 0,
                    },
                    {
                        # sin id -> se descarta
                        "nameEn": "Producto roto sin id",
                        "sellPrice": "5.00",
                    },
                    {
                        "id": "999",
                        "nameEn": "Producto con precio invalido",
                        "sellPrice": None,
                    },
                ],
            }
        ]
    },
}


def test_parse_product_list_maps_fields_and_url():
    products = parse_product_list(SAMPLE_RESPONSE)
    by_id = {p["pid"]: p for p in products}

    assert set(by_id) == {"2100554014971047937", "2100554099999999999"}

    p = by_id["2100554014971047937"]
    assert p["price"] == 9.5
    assert p["title"] == "Stainless Steel Insulated Water Bottle with Straw"
    assert p["is_free_shipping"] is True
    assert p["url"] == build_product_url("2100554014971047937")

    assert by_id["2100554099999999999"]["is_free_shipping"] is False


def test_parse_product_list_skips_missing_id_or_price():
    products = parse_product_list(SAMPLE_RESPONSE)
    titles = {p["title"] for p in products}
    assert "Producto roto sin id" not in titles
    assert "Producto con precio invalido" not in titles
