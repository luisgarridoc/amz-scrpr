# amz-scrpr — Detector de oportunidades de dropshipping (Amazon vs CJdropshipping)

Pipeline en Python para detectar productos en tendencia en Amazon cuyo precio
de proveedor en CJdropshipping deja un margen (gap) atractivo. **v1: solo
research/detección — no contacta proveedores ni publica productos.**

## Arquitectura

```
scouting/   -> obtiene productos en tendencia de Amazon (Keepa / RapidAPI)
matching/   -> encuentra el equivalente en CJdropshipping (Claude + API de CJ)
calc/       -> calcula margen bruto y gap_pct
output/     -> escribe el CSV final, ordenado y filtrado
common/     -> config (.env), logging, retry/backoff, caché SQLite
```

Flujo: `scouting -> matching -> calc -> output` (ver `main.py`).

## Instalación

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # y completa tus API keys
```

Por defecto `TEST_MODE=true`: el pipeline usa los productos hardcodeados de
`scouting/sample_data.py` y no gasta cuota de ninguna API externa.

## Verificar credenciales antes de correr el pipeline completo

```bash
python test_connections.py
```

Con `TEST_MODE=true` solo revisa que las keys existan en `.env`. Pon
`TEST_MODE=false` para hacer 1 llamada real de prueba a cada API (Keepa,
RapidAPI, CJdropshipping, Claude) y confirmar que las credenciales son
válidas.

## Qué necesitas registrar en cada plataforma

Para v1 solo son **3 keys imprescindibles**: RapidAPI, CJdropshipping y
Anthropic/Claude. Keepa es opcional (ver nota abajo).

### 1. Keepa (https://keepa.com) — OPCIONAL, sin plan gratis
1. La API de Keepa **no tiene tier gratis**: Keepa Pro (~29€/mes) es solo la
   extensión de navegador; la API de datos arranca en **~49€/mes** (plan
   Starter, 20 tokens/minuto). Ver [Plans & Tokens](https://keepa.com/api-docs/plans-tokens.html).
2. Por eso el pipeline usa `SCOUTING_SOURCE=rapidapi` por defecto y **no
   requiere Keepa** para correr. Solo regístrate y paga la API de Keepa si
   más adelante quieres su histórico de precios/BSR más completo — en ese
   caso pon `SCOUTING_SOURCE=keepa` y `KEEPA_API_KEY` en `.env`.

### 2. RapidAPI (https://rapidapi.com)
1. Crea una cuenta en rapidapi.com.
2. Busca en el marketplace un API de "Amazon Data" (ej. "Real-Time Amazon
   Data", "Amazon Product Data") y suscríbete a su **plan Basic/free**.
3. En la pestaña **Endpoints** del API elegido, copia:
   - `X-RapidAPI-Key` -> `RAPIDAPI_KEY` en `.env`
   - `X-RapidAPI-Host` -> `RAPIDAPI_AMAZON_HOST` en `.env`
4. Ojo: cada API de RapidAPI tiene su propio contrato de endpoints/params;
   `scouting/rapidapi_client.py` trae un método de ejemplo (`/search`) que
   deberás ajustar al API real que elijas.

### 3. CJdropshipping (https://cjdropshipping.com)
1. Crea una cuenta normal en cjdropshipping.com.
2. Solicita acceso de API en https://developers.cjdropshipping.com/.
3. CJ autentica con email + password/API-key contra un endpoint que
   devuelve un `accessToken` (válido ~unos días, hay que renovarlo).
4. Pon esas credenciales en `CJ_API_KEY` / `CJ_API_SECRET` en `.env`.

### 4. Anthropic / Claude (https://console.anthropic.com)
1. Crea una cuenta en console.anthropic.com y añade método de pago (la API
   de Claude es de pago por uso, no tiene free tier de llamadas ilimitadas).
2. Genera una API key en **API Keys** y ponla en `ANTHROPIC_API_KEY`.
3. `ANTHROPIC_MODEL` es configurable en `.env` (default `claude-sonnet-5`).

## Probar cada cliente de forma aislada

```bash
python -m scouting.keepa_client
python -m scouting.rapidapi_client
python -m matching.cj_client
python -m matching.claude_client
```

Cada uno corre su propio `test_connection()` (1 sola llamada) y loggea el
resultado.

## Correr el pipeline en modo de prueba

```bash
python main.py
```

Con `TEST_MODE=true`, usa `scouting/sample_data.py` como fuente y el paso
de matching real todavía está como placeholder (no está conectado a
Claude/CJ en `main.py` — eso se conecta en el siguiente paso, una vez
tengamos categoría de prueba y credenciales confirmadas).

## Tests unitarios (sin red)

```bash
pip install pytest
pytest tests/
```

## Configuración de negocio

En `.env`:
- `AMAZON_COMMISSION_PCT` (default `15`): % de comisión de Amazon.
- `MIN_GAP_PCT` (default `50`): umbral mínimo de `gap_pct` para aparecer en
  el CSV final.

## Próximos pasos (no implementados aún, a propósito)

- Conectar `run_matching()` en `main.py` a `ClaudeMatchingClient` +
  `CJClient` real (generar variantes, buscar en CJ, validar match, cachear).
- Conectar `run_scouting()` a Keepa/RapidAPI real una vez confirmada la
  categoría de producto de prueba.
- Nada de scraping de Amazon sin API (fuera de alcance de v1).
