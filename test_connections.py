"""Script de verificación de credenciales.

Corre un test mínimo contra cada API (1 sola llamada por servicio) para
confirmar que las keys en .env funcionan, ANTES de construir/ejecutar el
pipeline completo. No usar en TEST_MODE si quieres evitar cualquier gasto
de cuota: en ese caso solo revisa que las keys existan.

Uso:
    python test_connections.py
"""
from common.config import settings
from common.logging_conf import get_logger

logger = get_logger("test_connections")


def main() -> None:
    logger.info("TEST_MODE=%s", settings.test_mode)

    results = {}

    if settings.test_mode:
        logger.info(
            "TEST_MODE activo: NO se llama a ninguna API externa. "
            "Pon TEST_MODE=false en .env para probar credenciales reales."
        )
        required = [
            ("RapidAPI", settings.rapidapi_key),
            ("CJdropshipping", settings.cj_api_key and settings.cj_api_secret),
            ("Anthropic/Claude", settings.anthropic_api_key),
        ]
        for name, key in required:
            results[name] = "key presente" if key else "FALTA key en .env"
        if settings.scouting_source == "keepa":
            results["Keepa (opcional, de pago)"] = (
                "key presente" if settings.keepa_api_key else "FALTA key en .env"
            )
    else:
        from matching.claude_client import ClaudeMatchingClient
        from matching.cj_client import CJClient
        from scouting.rapidapi_client import RapidAPIAmazonClient

        results["RapidAPI"] = RapidAPIAmazonClient().test_connection()
        results["CJdropshipping"] = CJClient().test_connection()
        results["Anthropic/Claude"] = ClaudeMatchingClient().test_connection()
        if settings.scouting_source == "keepa":
            from scouting.keepa_client import KeepaClient

            results["Keepa (opcional, de pago)"] = KeepaClient().test_connection()

    logger.info("Resultado de verificación de credenciales:")
    for name, status in results.items():
        logger.info("  %-20s -> %s", name, status)


if __name__ == "__main__":
    main()
