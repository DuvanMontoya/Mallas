# Smoke sintético

El chequeo operacional no autenticado vive en `scripts/smoke.py`.

```powershell
python scripts/smoke.py --base-url http://localhost:8000
python scripts/smoke.py --base-url http://localhost:8000 --web-url http://localhost:3000
```

Comprueba:

- `GET /api/v1/health/live` → `200` y `status=ok`;
- `GET /api/v1/health/ready` → `200` y `database=ok`;
- opcionalmente la URL web → respuesta HTTP 2xx/3xx.

El smoke no llama endpoints de producto autenticados, no guarda cookies, no imprime
headers, no registra cuerpos y limita el texto de error. Un readiness `503`
es un fallo operacional útil y debe abrir el runbook correspondiente.
