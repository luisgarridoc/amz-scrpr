"""Cliente para la API "Real-Time Amazon Data" de RapidAPI
(https://rapidapi.com/letscrape-6bRBa3QguO5/api/real-time-amazon-data).

Free tier: plan Basic ($0/mes, 100 requests/mes). La key (X-RapidAPI-Key) y
el host (X-RapidAPI-Host) se sacan del panel "Header Parameters" o del
"Code Snippets" en el Playground del API, una vez suscrito.

Dos formas de SCOUTING:
  - /best-sellers: ranking de más vendidos por categoría de Amazon
    (parámetros confirmados desde el Playground: language, country, type,
    page, fields, category). Útil cuando el nicho coincide con una
    categoría real de Amazon Best Sellers.
  - /search: búsqueda libre por keyword (parámetros confirmados en vivo:
    query, country, page). Útil para nichos que no tienen categoría propia
    en Amazon (ej. "padel" no existe como categoría de Best Sellers en
    amazon.com, pero sí hay cientos de productos buscables).

Importante: usa siempre country="US" salvo que sepas que CJdropshipping
también te va a cotizar en la misma moneda que uses aquí -- mezclar EUR de
Amazon.es con USD de CJ rompe el cálculo de margen.
"""
from __future__ import annotations

from typing import Any, Optional

import requests

from common.config import settings
from common.logging_conf import get_logger
from common.retry import raise_for_rate_limit, with_backoff

logger = get_logger(__name__)

# Tipos de listado soportados por /best-sellers.
BEST_SELLERS_TYPES = (
    "BEST_SELLERS",
    "GIFT_IDEAS",
    "MOST_WISHED_FOR",
    "MOVERS_AND_SHAKERS",
    "NEW_RELEASES",
)


class RapidAPIAmazonClient:
    def __init__(self, api_key: Optional[str] = None, host: Optional[str] = None):
        self.api_key = api_key or settings.rapidapi_key
        self.host = host or settings.rapidapi_amazon_host
        if not self.api_key:
            logger.warning("RAPIDAPI_KEY no configurada: las llamadas fallarán.")

    def _headers(self) -> dict[str, str]:
        return {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.host,
        }

    @with_backoff()
    def get_best_sellers(
        self,
        category: str,
        list_type: str = "BEST_SELLERS",
        page: str = "1",
        country: str = "US",
        language: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> dict[str, Any]:
        """Trae el ranking de más vendidos de una categoría (ej. "electronics",
        o subcategoría "software/229535" tal como aparece en la URL de
        Amazon Best Sellers).
        """
        url = f"https://{self.host}/best-sellers"
        params: dict[str, Any] = {
            "category": category,
            "type": list_type,
            "page": page,
            "country": country,
        }
        if language:
            params["language"] = language
        if fields:
            params["fields"] = fields
        resp = requests.get(url, headers=self._headers(), params=params, timeout=15)
        raise_for_rate_limit(resp)
        return resp.json()

    @with_backoff()
    def search_products(self, keyword: str, country: str = "US", page: str = "1") -> dict[str, Any]:
        """Busca productos por keyword libre (endpoint /search).

        NOTA: a diferencia de /best-sellers (contrato ya confirmado desde el
        Playground), este método usa parámetros de ejemplo -- confírmalos
        contra la pestaña "Search" del Playground antes de depender de él.
        """
        url = f"https://{self.host}/search"
        params = {"query": keyword, "country": country, "page": page}
        resp = requests.get(url, headers=self._headers(), params=params, timeout=15)
        raise_for_rate_limit(resp)
        return resp.json()

    def test_connection(self, sample_category: str = "electronics") -> bool:
        """Prueba mínima: 1 llamada a /best-sellers para verificar credenciales."""
        try:
            data = self.get_best_sellers(sample_category)
            ok = bool(data)
            logger.info("RapidAPI test_connection: %s", "OK" if ok else "respuesta vacía")
            return ok
        except Exception as exc:  # noqa: BLE001
            logger.error("RapidAPI test_connection falló: %s", exc)
            return False


def _parse_price(raw: Optional[str]) -> Optional[float]:
    """Convierte precios con formato US ("$1,249.00") o europeo ("49,90 €")
    a float. Detecta el separador decimal viendo cuál (',' o '.') aparece
    último en la cadena. Devuelve None si no es parseable (o es null)."""
    if not raw:
        return None
    cleaned = "".join(ch for ch in raw if ch.isdigit() or ch in ",.-")
    if not cleaned:
        return None
    last_comma, last_dot = cleaned.rfind(","), cleaned.rfind(".")
    if last_comma > last_dot:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def map_best_sellers_to_products(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Convierte la respuesta de /best-sellers al esquema interno del pipeline:
    {title, asin, price, reviews, bsr}. Descarta items sin precio (product_price
    null) ya que calc.gap_calculator los necesita.
    """
    items = response.get("data", {}).get("best_sellers", [])
    products = []
    for item in items:
        price = _parse_price(item.get("product_price"))
        if price is None:
            continue
        products.append(
            {
                "asin": item["asin"],
                "title": item["product_title"],
                "price": price,
                "reviews": item.get("product_num_ratings") or 0,
                "bsr": item.get("rank"),
            }
        )
    return products


def map_search_to_products(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Convierte la respuesta de /search al esquema interno del pipeline:
    {title, asin, price, reviews, bsr}. /search no trae ranking de ventas,
    así que bsr queda en None (columna vacía en el CSV final). Descarta
    items sin precio.
    """
    items = response.get("data", {}).get("products", [])
    products = []
    for item in items:
        price = _parse_price(item.get("product_price"))
        if price is None:
            continue
        products.append(
            {
                "asin": item["asin"],
                "title": item["product_title"],
                "price": price,
                "reviews": item.get("product_num_ratings") or 0,
                "bsr": None,
            }
        )
    return products


if __name__ == "__main__":
    RapidAPIAmazonClient().test_connection()
