"""Set de productos Amazon hardcodeados para depurar el pipeline sin gastar
cuota de Keepa / RapidAPI.

Sustituye o amplía esta lista con productos reales de la categoría elegida
para las pruebas (ver conversación con el usuario sobre qué categoría usar).
"""

SAMPLE_AMAZON_PRODUCTS = [
    {
        "asin": "B0BSHF7WHW",
        "title": "Mini masajeador de cuello portátil recargable",
        "price": 29.99,
        "reviews": 4200,
        "bsr": 850,
    },
    {
        "asin": "B0C1H26C46",
        "title": "Organizador de cables magnético para escritorio (set 6 uds)",
        "price": 14.99,
        "reviews": 1800,
        "bsr": 2100,
    },
    {
        "asin": "B0BXYZ1234",
        "title": "Luz LED clip para lectura nocturna recargable USB",
        "price": 12.49,
        "reviews": 3100,
        "bsr": 1500,
    },
]
