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
4. El scouting real usa el endpoint **`/best-sellers`** de esta API (contrato
   confirmado y ya implementado en `scouting/rapidapi_client.py`), que trae el
   ranking de más vendidos por categoría de Amazon. Configura `SCOUTING_CATEGORY`
   en `.env` con la categoría que quieras probar (ej. `electronics`,
   `toys-and-games`, `home-garden` — nombres tal como aparecen en
   https://www.amazon.com/Best-Sellers/zgbs).
5. Si en el futuro usas otro API de RapidAPI (o el endpoint `/search` de este
   mismo), ajusta esa parte del cliente a su contrato real.

### 3. CJdropshipping (https://cjdropshipping.com)
1. Crea una cuenta normal en cjdropshipping.com (regístrate como si fueras a
   comprar/hacer dropshipping normal).
2. Inicia sesión y busca la sección **"API"** en tu dashboard (a veces bajo
   "My CJ" / Settings) — ahí generas tu API Key con el botón "Add API"/"Get API Key".
3. Te da una única cadena con formato `CJUserNum@api@xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   (no hay key + secret por separado, a diferencia de lo que asumí al principio).
4. Copia esa cadena completa a `CJ_API_KEY` en `.env`.
5. Nuestro cliente hace `POST /authentication/getAccessToken` con
   `{"apiKey": "..."}` y obtiene un `accessToken` válido ~15 días (se cachea
   en memoria durante la ejecución; renovarlo en corridas futuras no requiere
   cambios de tu parte, se pide automáticamente).

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
