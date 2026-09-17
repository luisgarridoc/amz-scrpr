"""Cliente para la API "Real-Time Amazon Data" de RapidAPI
(https://rapidapi.com/letscrape-6bRBa3QguO5/api/real-time-amazon-data).

Free tier: plan Basic ($0/mes, 100 requests/mes). La key (X-RapidAPI-Key) y
el host (X-RapidAPI-Host) se sacan del panel "Header Parameters" o del
"Code Snippets" en el Playground del API, una vez suscrito.

Endpoint usado para SCOUTING de "productos en tendencia": /best-sellers,
que devuelve el ranking de más vendidos por categoría de Amazon (parámetros
confirmados desde el Playground: language, country, type, page, fields,
category).
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


if __name__ == "__main__":
    RapidAPIAmazonClient().test_connection()
