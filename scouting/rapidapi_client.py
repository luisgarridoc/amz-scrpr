"""Cliente básico para un endpoint de RapidAPI de datos de Amazon.

Free tier: crea cuenta en rapidapi.com, suscríbete (plan Basic/free) a un API
de "Amazon Data" (ej. "Real-Time Amazon Data"), y copia la "X-RapidAPI-Key"
desde la pestaña "Endpoints" del API elegido. El host (X-RapidAPI-Host)
depende del API concreto que elijas — configúralo en RAPIDAPI_AMAZON_HOST.
"""
from __future__ import annotations

from typing import Any, Optional

import requests

from common.config import settings
from common.logging_conf import get_logger
from common.retry import raise_for_rate_limit, with_backoff

logger = get_logger(__name__)


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
    def search_products(self, keyword: str, country: str = "US") -> dict[str, Any]:
        """Busca productos por keyword (endpoint de ejemplo: /search).

        NOTA: el path y los parámetros exactos dependen del API de RapidAPI
        que elijas — ajusta esta función al contrato real una vez suscrito.
        """
        url = f"https://{self.host}/search"
        params = {"query": keyword, "country": country}
        resp = requests.get(url, headers=self._headers(), params=params, timeout=15)
        raise_for_rate_limit(resp)
        return resp.json()

    def test_connection(self, sample_keyword: str = "wireless earbuds") -> bool:
        """Prueba mínima: 1 búsqueda de ejemplo para verificar credenciales."""
        try:
            data = self.search_products(sample_keyword)
            ok = bool(data)
            logger.info("RapidAPI test_connection: %s", "OK" if ok else "respuesta vacía")
            return ok
        except Exception as exc:  # noqa: BLE001
            logger.error("RapidAPI test_connection falló: %s", exc)
            return False


if __name__ == "__main__":
    RapidAPIAmazonClient().test_connection()
