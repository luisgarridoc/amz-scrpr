"""Carga de configuración y variables de entorno para todo el pipeline."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _get_float(name: str, default: float) -> float:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    return float(val)


@dataclass(frozen=True)
class Settings:
    # Fuente de scouting activa: "rapidapi" (default, tiene planes free/baratos)
    # o "keepa" (la API de Keepa es 100% de pago, desde 49EUR/mes -- opcional).
    scouting_source: str = os.getenv("SCOUTING_SOURCE", "rapidapi")

    keepa_api_key: str = os.getenv("KEEPA_API_KEY", "")

    rapidapi_key: str = os.getenv("RAPIDAPI_KEY", "")
    rapidapi_amazon_host: str = os.getenv(
        "RAPIDAPI_AMAZON_HOST", "real-time-amazon-data.p.rapidapi.com"
    )
    # Categoria de Amazon Best Sellers a usar en el scouting real (ver
    # https://www.amazon.com/Best-Sellers/zgbs para nombres de categoria/subcategoria).
    scouting_category: str = os.getenv("SCOUTING_CATEGORY", "electronics")

    cj_api_key: str = os.getenv("CJ_API_KEY", "")

    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

    amazon_commission_pct: float = _get_float("AMAZON_COMMISSION_PCT", 15.0)
    min_gap_pct: float = _get_float("MIN_GAP_PCT", 50.0)

    test_mode: bool = _get_bool("TEST_MODE", True)

    cache_path: str = os.getenv("CACHE_PATH", "common/cache.sqlite3")


settings = Settings()
