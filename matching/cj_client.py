"""Cliente básico para la API oficial de CJdropshipping.

Registro: crea una cuenta normal en https://cjdropshipping.com/, luego en
tu dashboard busca la sección "API" (a veces bajo Settings / "My CJ") y
genera tu API Key ahí -- es una única cadena con formato
"CJUserNum@api@xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" (no hay key+secret por
separado). Copia esa cadena completa a CJ_API_KEY en .env.

Auth: POST /authentication/getAccessToken con body {"apiKey": "..."} (ver
https://developers.cjdropshipping.com/), devuelve un accessToken válido
~15 días que se manda como header "CJ-Access-Token" en las demás llamadas.
"""
from __future__ import annotations

from typing import Any, Optional

import requests

from common.config import settings
from common.logging_conf import get_logger
from common.retry import raise_for_rate_limit, with_backoff

logger = get_logger(__name__)

BASE_URL = "https://developers.cjdropshipping.com/api2.0/v1"


class CJClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.cj_api_key
        self._access_token: Optional[str] = None
        if not self.api_key:
            logger.warning("CJ_API_KEY no configurada: las llamadas fallarán.")

    @with_backoff()
    def get_access_token(self) -> str:
        if self._access_token:
            return self._access_token
        url = f"{BASE_URL}/authentication/getAccessToken"
        resp = requests.post(url, json={"apiKey": self.api_key}, timeout=15)
        raise_for_rate_limit(resp)
        data = resp.json()
        token = data.get("data", {}).get("accessToken")
        if not token:
            raise RuntimeError(f"CJ no devolvió accessToken: {data}")
        self._access_token = token
        logger.info("CJ: access token obtenido correctamente.")
        return token

    @with_backoff()
    def search_products(self, keyword: str, page_size: int = 10) -> dict[str, Any]:
        """Busca productos por keyword en el catálogo de CJ."""
        token = self.get_access_token()
        url = f"{BASE_URL}/product/list"
        headers = {"CJ-Access-Token": token}
        params = {"productName": keyword, "pageSize": page_size}
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        raise_for_rate_limit(resp)
        return resp.json()

    def test_connection(self, sample_keyword: str = "phone case") -> bool:
        """Prueba mínima: autenticación + 1 búsqueda de ejemplo."""
        try:
            data = self.search_products(sample_keyword, page_size=1)
            ok = bool(data)
            logger.info("CJ test_connection: %s", "OK" if ok else "respuesta vacía")
            return ok
        except Exception as exc:  # noqa: BLE001
            logger.error("CJ test_connection falló: %s", exc)
            return False


if __name__ == "__main__":
    CJClient().test_connection()
