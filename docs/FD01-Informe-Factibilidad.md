<center>

![Logo UPT](./media/logo-upt.png)

**UNIVERSIDAD PRIVADA DE TACNA**

**FACULTAD DE INGENIERÍA**

**Escuela Profesional de Ingeniería de Sistemas**

**Informe de Factibilidad**

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

Informe de Factibilidad

Versión *1.1*

| CONTROL DE VERSIONES | | | | | |
|:---:|:---|:---|:---|:---:|:---|
| Versión | Hecha por | Revisada por | Aprobada por | Fecha | Motivo |
| 1.0 | ACV, FYG | ACV, FYG | P. Cuadros Q. | 2026-04-04 | Versión inicial |
| 1.1 | ACV, FYG | ACV, FYG | P. Cuadros Q. | 2026-06-23 | Actualización factual y formato institucional |

# FD01 - Informe de factibilidad

## Identificación

- Proyecto: Query Analyzer
- Versión documentada: 2.2.0
- Plataforma: Python 3.14+
- Interfaces: CLI, TUI y API REST local

## Problema

Los motores de bases de datos entregan planes y métricas con formatos distintos.
La inspección manual exige conocer cada motor, reunir datos dispersos y evitar
comparaciones engañosas entre valores que no tienen el mismo significado.

## Solución propuesta

Query Analyzer unifica el acceso a motores SQL y NoSQL mediante adaptadores.
Cada adaptador obtiene la evidencia disponible y construye un
`QueryAnalysisReport` con:

- consulta y motor;
- tiempo observado;
- plan normalizado;
- plan original;
- métricas disponibles;
- fecha de análisis;
- interpretación opcional mediante IA.

El sistema no genera una puntuación 0-100 ni clasifica automáticamente la calidad
de la consulta. Esa decisión evita presentar heurísticas como hechos.

## Factibilidad técnica

La arquitectura utiliza:

- Python 3.14;
- Pydantic para contratos;
- Typer y Rich para CLI;
- Textual para TUI;
- FastAPI y Uvicorn para API;
- drivers oficiales o ampliamente utilizados;
- Docker para integración local.

La separación por adaptadores permite añadir motores sin cambiar el contrato
principal. Las pruebas unitarias, Ruff y mypy validan el núcleo.

## Factibilidad operativa

El usuario puede:

1. Crear un perfil cifrado.
2. Diagnosticar la conexión.
3. Ejecutar el análisis.
4. revisar plan, métricas y datos originales.
5. Exportar el reporte.
6. Solicitar interpretación de IA de manera opcional.

La herramienta funciona localmente y no requiere almacenar credenciales en un
servicio externo. La API recibe secretos por solicitud y no los persiste.

## Riesgos

| Riesgo | Tratamiento |
|---|---|
| Métricas diferentes entre motores | Documentar semántica y evitar un score común |
| Motores sin `EXPLAIN` formal | Reportar solo datos realmente disponibles |
| Exposición de credenciales | Cifrado, `SecretStr` y sanitización |
| Interpretaciones incorrectas de IA | Separar IA de datos factuales |
| Dependencias opcionales difíciles de compilar | Instalación y soporte documentados |

## Conclusión

El proyecto es técnicamente viable. El valor principal está en normalizar y
presentar evidencia verificable de múltiples motores, no en emitir diagnósticos
automáticos sin contexto.
