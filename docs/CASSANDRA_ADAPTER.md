# Adaptador Cassandra

El adaptador Cassandra presenta información factual de una consulta CQL y de la
traza disponible. No asigna score ni genera advertencias deterministas.

## Dependencia

`cassandra-driver` es opcional debido a sus restricciones de compilación en
algunos entornos Windows con Python 3.14.

## Datos reportados

Cuando el driver y el servidor lo permiten:

- consulta CQL;
- tiempo observado;
- eventos de traza;
- coordinador y réplicas;
- métricas normalizadas;
- resumen descriptivo.

## Uso conceptual

```python
report = adapter.execute_explain(
    "SELECT * FROM events WHERE user_id = '42' LIMIT 20"
)

print(report.plan_summary)
print(report.metrics)
```

La herramienta no ejecuta cambios de esquema ni afirma automáticamente que una
consulta sea eficiente. La interpretación opcional mediante IA se almacena en
`ai_analysis` y no altera las métricas observadas.
