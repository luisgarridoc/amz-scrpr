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


def _get_int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    return int(val)


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
    # Modo de scouting: "best_sellers" (por categoria de Amazon Best Sellers,
    # ver https://www.amazon.com/Best-Sellers/zgbs) o "search" (por keyword
    # libre -- util para nichos sin categoria propia en Amazon, ej. "padel").
    scouting_mode: str = os.getenv("SCOUTING_MODE", "best_sellers")
    scouting_category: str = os.getenv("SCOUTING_CATEGORY", "electronics")
    scouting_keyword: str = os.getenv("SCOUTING_KEYWORD", "")
    scouting_country: str = os.getenv("SCOUTING_COUNTRY", "US")

    cj_api_key: str = os.getenv("CJ_API_KEY", "")

    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

    amazon_commission_pct: float = _get_float("AMAZON_COMMISSION_PCT", 15.0)
    min_gap_pct: float = _get_float("MIN_GAP_PCT", 50.0)
    # Limita cuantos productos de Amazon se pasan a MATCHING (Claude+CJ) por
    # corrida -- cada uno gasta varias llamadas de API, y el scouting real
    # puede traer decenas de productos de golpe.
    max_products_per_run: int = _get_int("MAX_PRODUCTS_PER_RUN", 5)

    test_mode: bool = _get_bool("TEST_MODE", True)

    cache_path: str = os.getenv("CACHE_PATH", "common/cache.sqlite3")


settings = Settings()
