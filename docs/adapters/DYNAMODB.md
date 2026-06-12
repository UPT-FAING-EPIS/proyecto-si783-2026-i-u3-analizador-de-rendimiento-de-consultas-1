# Adaptador DynamoDB

El adaptador DynamoDB transforma una operación declarativa en un
`QueryAnalysisReport` factual. No calcula score ni produce advertencias o
recomendaciones deterministas.

## Configuración

Use un perfil con motor `dynamodb`. Las credenciales se resuelven mediante la
configuración proporcionada y el SDK de AWS.

## Datos reportados

Según la operación, el reporte puede incluir:

- nombre de operación;
- tabla;
- modo de lectura;
- capacidad consumida cuando está disponible;
- parámetros normalizados;
- plan descriptivo.

## Ejemplo conceptual

```python
report = adapter.execute_explain(
    '{"operation":"Query","table":"orders","key_condition":{"customer_id":"42"}}'
)

print(report.plan_summary)
print(report.metrics)
```

La interpretación de si una operación conviene para una carga determinada debe
basarse en sus métricas, diseño de claves, capacidad y contexto. La IA opcional
puede generar observaciones, pero permanece separada de los datos del adaptador.

## Límites

- DynamoDB no ofrece un árbol `EXPLAIN` SQL.
- Algunas métricas requieren ejecutar o simular una operación.
- El adaptador no modifica tablas ni crea índices.
