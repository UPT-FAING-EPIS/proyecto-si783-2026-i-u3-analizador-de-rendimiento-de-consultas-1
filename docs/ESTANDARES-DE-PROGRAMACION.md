<div align="center">

![Logo UPT](./media/logo-upt.png)

**UNIVERSIDAD PRIVADA DE TACNA**

**FACULTAD DE INGENIERÍA**

**Escuela Profesional de Ingeniería de Sistemas**

<br>

# ESTÁNDARES DE PROGRAMACIÓN

## PROYECTO: ANALIZADOR DE RENDIMIENTO DE CONSULTAS

**Sistema Query Analyzer**

<br>

**Curso:** Base de Datos II

**Docente:** Mag. Patrick Cuadros Quiroga

**Integrantes:**

**Carbajal Vargas, Andre Alejandro (2023077287)**

**Yupa Gómez, Fátima Sofía (2023076618)**

<br>

**Tacna – Perú**

**2026**

</div>

<div style="page-break-after: always;"></div>

# CONTROL DE VERSIONES

| Versión | Elaborado por | Revisado por | Fecha | Motivo |
|:---:|---|---|:---:|---|
| 1.0 | AACV / FSYG | AACV / FSYG | 23/06/2026 | Primera versión formal para Query Analyzer 2.3.1 |

# 1. Propósito

Este documento establece las reglas de construcción, revisión y mantenimiento del código de Query
Analyzer. Su cumplimiento busca asegurar legibilidad, coherencia, seguridad, mantenibilidad y
compatibilidad entre los módulos Python, la extensión TypeScript, las pruebas y la documentación.

# 2. Alcance

Las reglas se aplican a:

- `query_analyzer/`;
- `tests/`;
- `integrations/vscode-query-analyzer/`;
- `integrations/skills/`;
- scripts de automatización;
- archivos de configuración;
- documentación técnica;
- workflows de GitHub Actions.

# 3. Entorno y herramientas

## 3.1. Python

- Versión mínima: Python 3.14.
- Gestor de dependencias obligatorio: `uv`.
- No se debe usar `pip` directamente para el flujo normal del repositorio.
- El entorno debe sincronizarse con:

```bash
uv sync
```

- Toda ejecución de desarrollo debe realizarse con `uv run`.

## 3.2. TypeScript

- La extensión se construye con TypeScript.
- Las dependencias deben instalarse de forma reproducible con `npm ci`.
- El código compilado se genera en `out/` y no se modifica manualmente.

# 4. Organización del código

| Paquete | Responsabilidad |
|---|---|
| `adapters` | Integración con motores, parsers, modelos y serialización |
| `config` | Configuración, perfiles y cifrado |
| `core` | Servicios transversales de diagnóstico e IA |
| `cli` | Interfaz de línea de comandos |
| `tui` | Interfaz interactiva |
| `api` | API REST y contratos HTTP |
| `integrations` | VS Code, MCP y skills |
| `tests/unit` | Pruebas sin infraestructura externa |
| `tests/integration` | Pruebas contra motores reales o emulados |

Reglas:

1. Cada módulo debe tener una responsabilidad clara.
2. No se deben importar módulos de presentación desde adaptadores.
3. Los modelos compartidos deben ubicarse en una capa inferior reutilizable.
4. Deben evitarse dependencias circulares; para tipos se utilizará `TYPE_CHECKING`.
5. La lógica específica de un motor debe permanecer en su adaptador o parser.

# 5. Estilo de Python

## 5.1. Formato

- Indentación: 4 espacios.
- Longitud máxima de línea: 100 caracteres.
- Formateador: Ruff Format.
- No se utilizan tabulaciones.
- Debe existir una línea en blanco entre bloques lógicos.
- Se prefiere una expresión clara antes que una expresión excesivamente compacta.

## 5.2. Importaciones

Orden obligatorio:

1. biblioteca estándar;
2. dependencias de terceros;
3. módulos locales.

Ejemplo:

```python
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

from query_analyzer.adapters.models import QueryAnalysisReport

if TYPE_CHECKING:
    from query_analyzer.config.models import ProfileConfig
```

No se permiten importaciones con `*`.

## 5.3. Nombres

| Elemento | Convención | Ejemplo |
|---|---|---|
| Clases | PascalCase | `PostgreSQLAdapter` |
| Funciones y métodos | snake_case | `execute_explain` |
| Variables | snake_case | `execution_time_ms` |
| Constantes | UPPER_SNAKE_CASE | `DEFAULT_PORT` |
| Módulos | snake_case | `connection_diagnostics.py` |
| Miembros privados | Prefijo `_` | `_connection` |
| Booleanos | `is_`, `has_`, `can_` | `is_connected()` |
| Excepciones | Sufijo `Error` | `QueryAnalysisError` |

Los nombres deben expresar intención. Se evitan abreviaturas ambiguas como `cfg`, `mgr`, `tmp` o
`res`, salvo en ámbitos pequeños y convencionales.

## 5.4. Tipado

- Toda función pública debe declarar tipos de parámetros y retorno.
- Se debe escribir `-> None` cuando no existe valor de retorno.
- Se utiliza la sintaxis moderna: `str | None`, `list[str]`, `dict[str, Any]`.
- Se evita `Any` salvo integración con datos realmente dinámicos.
- Los `# type: ignore` deben incluir justificación y código de error cuando sea posible.
- Las colecciones vacías deben tener tipos inferibles o explícitos.

Ejemplo:

```python
def execute_explain(self, query: str) -> QueryAnalysisReport:
    """Ejecuta el mecanismo de análisis del motor."""
```

## 5.5. Docstrings

- Estilo obligatorio: Google.
- Se documentan módulos, clases, funciones públicas y comportamientos no evidentes.
- Deben incluir `Args`, `Returns` y `Raises` cuando corresponda.
- La docstring explica el contrato; no repite literalmente el nombre del método.

```python
def get_profile(self, name: str) -> ProfileConfig:
    """Obtiene un perfil de conexión.

    Args:
        name: Nombre único del perfil.

    Returns:
        Configuración asociada al perfil.

    Raises:
        ProfileNotFoundError: Si el perfil no existe.
    """
```

## 5.6. Modelos

- Los contratos externos y modelos validados se implementan con Pydantic.
- Las estructuras internas simples pueden utilizar `dataclass`.
- Los valores mutables deben crearse con `default_factory`.
- Los campos sensibles de API deben usar `SecretStr`.
- Las fechas persistidas deben usar UTC e ISO 8601.
- Un dato ausente se modela con `None`; no se reemplaza por cero.

# 6. Patrón Adapter

Todo nuevo motor debe:

1. heredar de `BaseAdapter`;
2. registrarse con `@AdapterRegistry.register("motor")`;
3. implementar `connect`, `disconnect`, `test_connection`, `execute_explain`,
   `get_slow_queries`, `get_metrics` y `get_engine_info`;
4. devolver `QueryAnalysisReport`;
5. construir `PlanNode` cuando exista un plan jerárquico;
6. conservar el plan original en `raw_plan`;
7. agregar métricas específicas en `metrics`;
8. cerrar la conexión incluso cuando ocurra una excepción;
9. incluir pruebas unitarias;
10. incluir pruebas de integración cuando exista un servicio reproducible.

No se debe añadir lógica condicional por motor en CLI, TUI o API si puede resolverse dentro del
adaptador.

# 7. Manejo de errores

## 7.1. Jerarquías

Las excepciones personalizadas deben heredar de una excepción base del módulo:

```python
class AdapterError(Exception):
    """Base para errores de adaptadores."""


class ConnectionError(AdapterError):
    """No fue posible establecer la conexión."""
```

## 7.2. Encadenamiento

Al convertir una excepción se conserva la causa:

```python
try:
    adapter.connect()
except ConnectionError as exc:
    raise QueryAnalysisError(f"No se pudo analizar la consulta: {exc}") from exc
```

## 7.3. Mensajes

- El mensaje público debe ser comprensible y no incluir secretos.
- El detalle técnico puede registrarse después de ser sanitizado.
- No se utilizan `except Exception: pass` en flujos normales.
- Si un error se ignora deliberadamente, debe documentarse la razón.
- API, CLI y TUI deben traducir errores a respuestas apropiadas para su interfaz.

# 8. Seguridad

1. Nunca imprimir contraseñas, tokens o API keys.
2. No serializar objetos completos de conexión en logs.
3. Cifrar contraseñas antes de persistir perfiles.
4. Usar variables de entorno para secretos de despliegue.
5. Aplicar sanitización a URI, parámetros y cabeceras.
6. Mantener la API en `127.0.0.1` por defecto.
7. No persistir claves de IA recibidas por HTTP.
8. Validar rango de puertos y nombres de motor.
9. Evitar ejecutar consultas destructivas en pruebas o demostraciones.
10. No incluir credenciales reales en fixtures, README o commits.

# 9. Separación entre evidencia e IA

- `QueryAnalysisReport` contiene la evidencia factual.
- `AIAnalysisResult` contiene únicamente interpretación.
- La IA no debe modificar `execution_time_ms`, `plan_tree`, `raw_plan` ni `metrics`.
- Un fallo de IA no convierte un análisis factual exitoso en error.
- Toda salida que muestre IA debe incluir una advertencia visible.
- No se implementará un score universal sin una definición validada por motor y caso de uso.

# 10. Estándares de API REST

- Prefijo versionado: `/api/v1`.
- Rutas del recurso: `/analyzer/...`.
- Modelos de entrada y salida definidos con Pydantic.
- Contraseñas y claves con `SecretStr`.
- Respuestas de error sin trazas internas.
- Nombres JSON en `snake_case`.
- Fechas en ISO 8601 y UTC.
- Los endpoints deben reutilizar servicios y adaptadores; no duplicar lógica.
- Toda ruta nueva debe incluir pruebas.

# 11. Estándares de TypeScript y VS Code

- `strict` debe permanecer habilitado en `tsconfig.json`.
- Nombres de clases y tipos: PascalCase.
- Funciones y variables: camelCase.
- Constantes globales: UPPER_SNAKE_CASE cuando sean inmutables y compartidas.
- Se deben escapar datos antes de insertarlos en HTML.
- Las contraseñas deben almacenarse con `SecretStorage`.
- No se deben bloquear operaciones del editor con procesos síncronos largos.
- Los procesos del backend deben cerrarse al desactivar la extensión.
- Toda función exportada debe tener tipos explícitos.
- Se deben agregar pruebas para construcción de URL, payload, perfiles y manejo del servidor.

# 12. Pruebas

## 12.1. Unitarias

- No requieren Docker.
- Deben probar comportamiento, validaciones y errores.
- Se prefiere una prueba por escenario.
- Los nombres usan `test_<comportamiento>`.
- Se permite parametrización para casos equivalentes.
- Los mocks deben limitarse a límites externos.

## 12.2. Integración

- Deben ejecutarse contra servicios controlados.
- Los datos se preparan mediante scripts de semilla.
- Las pruebas deben ser repetibles.
- El teardown debe liberar conexiones y recursos.
- No deben depender de servicios personales ni datos reales.

## 12.3. Comandos obligatorios

```bash
uv run ruff check --fix
uv run ruff format
uv run mypy query_analyzer
uv run pytest tests/unit/
```

Para integración:

```bash
make up
make health
uv run pytest tests/integration/
make down
```

Para la extensión:

```bash
npm ci
npm test
```

# 13. Documentación

- Markdown en UTF-8.
- Encabezados jerárquicos sin saltar niveles.
- Tablas solo para información tabular.
- Código dentro de bloques con lenguaje declarado.
- Diagramas mediante Mermaid cuando mejoren la comprensión.
- Comandos probados y compatibles con el repositorio.
- Toda funcionalidad pública debe reflejarse en README o documentación específica.
- No se deben conservar cifras, nombres de módulos o capacidades obsoletas.

# 14. Git y control de cambios

- Ramas de trabajo enfocadas en una sola finalidad.
- No realizar `force push` sobre ramas compartidas.
- No utilizar operaciones destructivas sin coordinación.
- Mensajes de commit con Conventional Commits:

| Prefijo | Uso |
|---|---|
| `feat:` | Nueva funcionalidad |
| `fix:` | Corrección |
| `docs:` | Documentación |
| `test:` | Pruebas |
| `refactor:` | Reestructuración sin cambio funcional |
| `chore:` | Mantenimiento |
| `ci:` | Automatización |

Cada Pull Request debe incluir problema, solución, evidencia de pruebas y efectos sobre
compatibilidad o documentación.

# 15. Lista de verificación

Antes de integrar un cambio:

- [ ] El código tiene tipos y nombres claros.
- [ ] Las funciones públicas tienen docstring.
- [ ] Ruff no reporta errores.
- [ ] El formato está actualizado.
- [ ] mypy no reporta incidencias.
- [ ] Las pruebas relevantes pasan.
- [ ] No se exponen secretos.
- [ ] Las conexiones se cierran.
- [ ] La documentación pública está actualizada.
- [ ] Los cambios de contratos están versionados o documentados.
- [ ] No se mezclan hechos del motor con interpretación de IA.
