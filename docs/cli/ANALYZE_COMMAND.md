# Comando `qa analyze`

`qa analyze` ejecuta el mecanismo de explicación disponible en el motor asociado
a un perfil y presenta los datos observados. No asigna puntuaciones ni declara
automáticamente que una consulta es buena o mala.

## Uso

```bash
qa analyze "SELECT * FROM users" --profile local-postgres
```

También puede utilizarse el perfil predeterminado:

```bash
qa analyze "SELECT 1"
```

Opciones vigentes:

```bash
qa analyze --help
```

## Flujo

1. Carga el perfil.
2. Valida la consulta.
3. Conecta el adaptador.
4. Ejecuta `EXPLAIN` o el mecanismo equivalente.
5. Normaliza el plan y las métricas disponibles.
6. Añade interpretación de IA solamente cuando está configurada.

## Salida

El reporte `QueryAnalysisReport` incluye:

- `engine`
- `query`
- `execution_time_ms`
- `plan_tree`
- `plan_summary`
- `raw_plan`
- `metrics`
- `analyzed_at`
- `ai_analysis`, opcional

La disponibilidad y significado de las métricas depende del motor.

## IA

Configure `QA_AI_BASE_URL`, `QA_AI_API_KEY` y `QA_AI_MODEL` para habilitar
interpretación asistida. Resumen, observaciones y recomendaciones de IA se
muestran separados de los datos factuales.

## Errores

Los errores de conexión deben diagnosticarse con:

```bash
qa profile test NOMBRE
```

No incluya contraseñas en comandos compartidos, capturas o logs.
