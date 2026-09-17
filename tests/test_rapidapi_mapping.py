"""Test unitario puro (sin red) del mapeo de /best-sellers al esquema interno.

Fixture basada en una respuesta real de la API "Real-Time Amazon Data"
(categoría "electronics").
"""
from scouting.rapidapi_client import map_best_sellers_to_products

SAMPLE_RESPONSE = {
    "status": "OK",
    "data": {
        "best_sellers": [
            {
                "rank": 1,
                "asin": "B08JHCVHTY",
                "product_title": "blink plus plan with monthly auto-renewal",
                "product_price": "$11.99",
                "product_star_rating": "4.4",
                "product_num_ratings": 280277,
            },
            {
                "rank": 44,
                "asin": "B0GR1493ZV",
                "product_title": "Apple 2026 MacBook Air 13-inch",
                "product_price": "$1,249.00",
                "product_star_rating": "4.7",
                "product_num_ratings": 1110,
            },
            {
                "rank": 28,
                "asin": "B0DN45YMP6",
                "product_title": "JBL Vibe Beam 2",
                "product_price": None,
                "product_star_rating": "4.1",
                "product_num_ratings": 7085,
            },
        ]
    },
}


def test_map_best_sellers_parses_price_and_thousands_separator():
    products = map_best_sellers_to_products(SAMPLE_RESPONSE)
    by_asin = {p["asin"]: p for p in products}

    assert by_asin["B08JHCVHTY"]["price"] == 11.99
    assert by_asin["B0GR1493ZV"]["price"] == 1249.00
    assert by_asin["B08JHCVHTY"]["bsr"] == 1
    assert by_asin["B08JHCVHTY"]["reviews"] == 280277


def test_map_best_sellers_skips_items_without_price():
    products = map_best_sellers_to_products(SAMPLE_RESPONSE)
    asins = {p["asin"] for p in products}
    assert "B0DN45YMP6" not in asins
    assert len(products) == 2
