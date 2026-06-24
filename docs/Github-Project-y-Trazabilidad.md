# GitHub Project y Trazabilidad

## Regla para las tareas

Toda tarea del proyecto debe incluir:

1. Historia `Como / Quiero / Para`.
2. Criterios de aceptación identificados.
3. Dos escenarios `Dado / Cuando / Entonces` por criterio crítico.
4. Motor o interfaz afectada.
5. Evidencia de prueba, reporte o documentación.
6. Versión objetivo.

## Flujo del tablero

| Estado | Condición |
|---|---|
| Backlog | Historia redactada y alcance identificado |
| Ready | Criterios, motores y escenarios revisados |
| In progress | Implementación iniciada |
| In review | Pruebas y evidencia disponibles |
| Done | Criterios cumplidos, CI exitosa y documentación actualizada |

## Trazabilidad mínima

| Artefacto | Relación esperada |
|---|---|
| FD03 | Requisito funcional o no funcional |
| Código | Módulo o adaptador que implementa el requisito |
| Prueba | Caso unitario, contrato, integración, BDD o interfaz |
| Workflow | Evidencia automatizada |
| FD05 | Resultado consolidado |

El formulario `.github/ISSUE_TEMPLATE/user-story.yml` aplica esta estructura a nuevas historias.
