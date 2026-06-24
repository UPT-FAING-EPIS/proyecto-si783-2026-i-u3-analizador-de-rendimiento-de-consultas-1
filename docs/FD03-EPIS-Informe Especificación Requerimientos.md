<center>

![Logo UPT](./media/logo-upt.png)

**UNIVERSIDAD PRIVADA DE TACNA**

**FACULTAD DE INGENIERÍA**

**Escuela Profesional de Ingeniería de Sistemas**

**Informe de Especificación de Requerimientos**

**Sistema Analizador de Rendimiento de Consultas (Query Analyzer)**

Curso: *Base de Datos II*

Docente: *Patrick Cuadros Quiroga*

Integrantes:

***Carbajal Vargas, Andre Alejandro (2023077287)***

***Yupa Gómez, Fátima Sofía (2023076618)***

**Tacna - Perú**

***2026***

</center>

<div style="page-break-after: always; visibility: hidden">\pagebreak</div>

Sistema *Analizador de Rendimiento de Consultas (Query Analyzer)*

Informe de Especificación de Requerimientos

Versión *1.1*

| CONTROL DE VERSIONES | | | | | |
|:---:|:---|:---|:---|:---:|:---|
| Versión | Hecha por | Revisada por | Aprobada por | Fecha | Motivo |
| 1.0 | ACV, FYG | ACV, FYG | P. Cuadros Q. | 2026-04-29 | Versión inicial |
| 1.1 | ACV, FYG | ACV, FYG | P. Cuadros Q. | 2026-06-23 | Actualización factual y formato institucional |

# FD03 - Especificación de requisitos

## Requisitos funcionales

| ID | Requisito |
|---|---|
| RF-01 | Registrar y listar motores mediante `AdapterRegistry` |
| RF-02 | Crear, editar, probar y eliminar perfiles |
| RF-03 | Cifrar credenciales persistidas |
| RF-04 | Diagnosticar DNS, TCP, autenticación y operatividad |
| RF-05 | Ejecutar `EXPLAIN` o mecanismo equivalente |
| RF-06 | Construir `QueryAnalysisReport` factual |
| RF-07 | Mostrar plan normalizado y plan original |
| RF-08 | Mostrar métricas disponibles sin inventar valores |
| RF-09 | Exportar reportes estructurados |
| RF-10 | Mantener historial básico por perfil |
| RF-11 | Ofrecer CLI y TUI |
| RF-12 | Exponer API REST local versionada |
| RF-13 | Permitir interpretación opcional mediante IA |

## Requisitos no funcionales

| ID | Requisito |
|---|---|
| RNF-01 | Ejecutarse con Python 3.14+ |
| RNF-02 | No exponer secretos en respuestas ni logs |
| RNF-03 | Mantener tipado verificable con mypy |
| RNF-04 | Cumplir formato y lint con Ruff |
| RNF-05 | Liberar conexiones aun cuando ocurra un error |
| RNF-06 | Separar datos factuales de contenido generado por IA |
| RNF-07 | Conservar compatibilidad por adaptador |
| RNF-08 | Proporcionar errores públicos comprensibles |

## Contrato de análisis

`QueryAnalysisReport` contiene:

- `engine: str`
- `query: str`
- `execution_time_ms: float`
- `plan_tree: PlanNode | None`
- `plan_summary: str`
- `raw_plan: Any`
- `metrics: dict[str, Any]`
- `analyzed_at: datetime`
- `ai_analysis: AIAnalysisResult | None`

No contiene `score`, `warnings` deterministas ni una lista automática de
antipatrones.

## Casos de uso

### Analizar consulta

1. El usuario selecciona un perfil.
2. El sistema valida la entrada.
3. El adaptador abre la conexión.
4. El motor produce el plan o datos equivalentes.
5. El sistema normaliza y presenta el reporte.
6. La conexión se libera.

### Diagnosticar conexión

El servicio ejecuta comprobaciones progresivas y devuelve estado, duración,
fecha y mensaje sanitizado.

### Usar API

El cliente envía conexión y consulta a `/api/v1/analyzer/explain`. La API no
persiste credenciales y no devuelve excepciones internas.

### Solicitar IA

El cliente aporta proveedor, clave y modelo. La respuesta de IA se identifica
como interpretación y no modifica las métricas.

## Criterios de aceptación

- El reporte solo contiene datos obtenidos o derivados estructuralmente del plan.
- Los secretos no aparecen en errores.
- Un fallo de IA no invalida el análisis factual.
- Los adaptadores se pueden probar de forma independiente.
- CLI, TUI y API comparten los mismos modelos.
