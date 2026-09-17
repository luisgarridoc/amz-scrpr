"""Decorador de reintentos con backoff exponencial para llamadas a APIs externas.

Las APIs free-tier (Keepa, RapidAPI, CJ) suelen devolver 429 / 503 cuando se
excede el rate limit. Este helper centraliza la política de reintento.
"""
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

import requests

from common.logging_conf import get_logger

logger = get_logger(__name__)


def with_backoff(max_attempts: int = 4, min_wait: float = 2, max_wait: float = 30):
    """Reintenta en errores de red / rate limit con backoff exponencial.

    Ej: intento 1 falla -> espera ~2s, intento 2 -> ~4s, intento 3 -> ~8s...
    """
    return retry(
        reraise=True,
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(
            (requests.exceptions.RequestException, RateLimitError)
        ),
        before_sleep=lambda retry_state: logger.warning(
            "Reintentando (%s/%s) tras error: %s",
            retry_state.attempt_number,
            max_attempts,
            retry_state.outcome.exception(),
        ),
    )


class RateLimitError(Exception):
    """Se lanza cuando una API responde 429 (rate limit excedido)."""


def raise_for_rate_limit(response: requests.Response) -> None:
    if response.status_code == 429:
        raise RateLimitError(f"Rate limit alcanzado: {response.status_code} {response.text[:200]}")
    response.raise_for_status()
