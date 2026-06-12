# FD04 - Informe de arquitectura

## Estilo

La solución combina arquitectura por capas con patrón Adapter.

```text
CLI / TUI / API
       |
Modelos y servicios de aplicación
       |
AdapterRegistry + BaseAdapter
       |
Drivers de motores
```

## Componentes

| Componente | Responsabilidad |
|---|---|
| `query_analyzer/adapters/` | Conexión, extracción y normalización por motor |
| `query_analyzer/config/` | Perfiles y cifrado |
| `query_analyzer/core/` | Diagnóstico e IA opcional |
| `query_analyzer/cli/` | Interfaz de comandos |
| `query_analyzer/tui/` | Interfaz terminal interactiva |
| `query_analyzer/api/` | FastAPI, schemas y endpoints |

## Flujo de análisis

```text
Solicitud
  -> validar entrada
  -> construir ConnectionConfig
  -> AdapterRegistry.create
  -> connect
  -> execute_explain
  -> QueryAnalysisReport
  -> presentar o serializar
  -> disconnect
```

## Modelo factual

Los adaptadores convierten resultados específicos en `PlanNode` y
`QueryAnalysisReport`. La normalización no debe añadir evaluaciones de calidad.
Valores ausentes permanecen como `None` o se omiten según el contrato.

## IA

`AIAnalyzer` acepta configuración por entorno o parámetros explícitos. Su salida
se convierte en `AIAnalysisResult` y se almacena separada de las métricas.

## API

`query_analyzer.api.app:app` expone rutas bajo `/api/v1/analyzer`. Los schemas
usan `SecretStr` para credenciales. Los errores internos se registran de forma
sanitizada y la respuesta pública utiliza mensajes genéricos.

## Seguridad

- Cifrado local de perfiles.
- Sanitización de URIs, contraseñas, tokens y claves.
- Liberación de conexiones mediante context manager.
- Sin persistencia de claves recibidas por API.
- Servidor API enlazado a `127.0.0.1` por defecto.

## Calidad

- Ruff para formato y lint.
- mypy para tipado.
- pytest para pruebas unitarias e integración.
- Docker Compose para motores locales.

## Decisiones

1. No existe un `ScoringEngine`.
2. No existe un detector central de antipatrones.
3. Cada motor conserva sus datos originales además del formato normalizado.
4. La interpretación pertenece a IA opcional, no al núcleo factual.
