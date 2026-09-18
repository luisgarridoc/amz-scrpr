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
    def search_products(self, keyword: str, page_size: int = 10, page: int = 1) -> dict[str, Any]:
        """Busca productos por keyword libre en el catálogo de CJ.

        Usa /product/listV2 (no /product/list: ese endpoint viejo ignora el
        filtro de texto y devuelve productos irrelevantes -- confirmado
        probándolo en vivo). listV2 sí hace búsqueda real por keyword vía el
        parámetro `keyWord` (con W mayúscula).
        """
        token = self.get_access_token()
        url = f"{BASE_URL}/product/listV2"
        headers = {"CJ-Access-Token": token}
        params = {"keyWord": keyword, "page": page, "size": page_size}
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


def build_product_url(pid: str) -> str:
    """URL pública del producto en CJ a partir de su id.

    NOTA: /product/listV2 no devuelve una URL directa. Este patrón
    ("/product/-p-{id}.html") es el que usa el sitio de CJ, pero no está
    confirmado contra documentación oficial -- si en algún momento no
    resuelve, revísalo contra una URL real copiada del sitio.
    """
    return f"https://cjdropshipping.com/product/-p-{pid}.html"


def parse_product_list(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Convierte la respuesta de /product/listV2 en candidatos de matching:
    {pid, title, price, url, image, is_free_shipping}.

    La respuesta viene anidada como data.content[].productList[] (cada
    entrada de "content" agrupa resultados de una keyword). Descarta items
    sin id o con sellPrice no numérico.
    """
    content = response.get("data", {}).get("content", []) or []
    products = []
    for group in content:
        for item in group.get("productList", []) or []:
            pid = item.get("id")
            if not pid:
                continue
            try:
                price = float(item.get("sellPrice"))
            except (TypeError, ValueError):
                continue
            products.append(
                {
                    "pid": pid,
                    "title": item.get("nameEn") or "",
                    "price": price,
                    "url": build_product_url(pid),
                    "image": item.get("bigImage"),
                    "is_free_shipping": item.get("addMarkStatus") == 1,
                }
            )
    return products


if __name__ == "__main__":
    CJClient().test_connection()
