# Query Analyzer

[![Python 3.14+](https://img.shields.io/badge/Python-3.14%2B-blue)](https://www.python.org/)
[![uv](https://img.shields.io/badge/Package%20Manager-uv-orange)](https://github.com/astral-sh/uv)

Analizador de rendimiento de consultas para SQL, NoSQL y TimeSeries con interfaz TUI en terminal.

## Que puedes hacer

- Analizar planes de ejecucion y detectar anti-patrones de rendimiento.
- Trabajar con multiples motores desde una sola herramienta CLI/TUI.
- Obtener recomendaciones de optimizacion orientadas al motor.

## Motores soportados

### SQL

- PostgreSQL
- MySQL
- SQLite
- CockroachDB
- YugabyteDB

### NoSQL

- MongoDB
- DynamoDB

### TimeSeries y grafos

- InfluxDB
- Neo4j

Para detalles de DynamoDB, revisa `docs/adapters/DYNAMODB.md`.

## Instalacion

La forma recomendada es instalar por package manager (Homebrew, Scoop o Snap). Como alternativa, puedes
instalar con binarios de GitHub Releases o ejecutar desde codigo fuente.

### Opcion A (recomendada): Instalacion por package manager

Cada release `v*` publica automaticamente el paquete `qa` via JReleaser.

#### Homebrew (macOS/Linux)

```bash
brew tap andre-carbajal/tap
brew install qa
qa --help
```

#### Scoop (Windows)

```powershell
scoop bucket add andre https://github.com/andre-carbajal/scoop-bucket.git
scoop install qa
qa --help
```

#### Snap (Linux)

```bash
sudo snap install qa
qa --help
```

### Opcion B: Instalar binario desde GitHub Releases

En cada tag `v*` se publican estos artefactos:

- `qa-linux-amd64.tar.gz`
- `qa-macos-arm64.zip`
- `qa-windows-amd64.zip`

#### Linux (amd64)

```bash
tar -xzf qa-linux-amd64.tar.gz
chmod +x qa
sudo mv qa /usr/local/bin/qa
qa --help
```

#### macOS (arm64)

```bash
unzip qa-macos-arm64.zip
chmod +x qa
sudo mv qa /usr/local/bin/qa
qa --help
```

#### Windows (amd64)

1. Descomprime `qa-windows-amd64.zip`.
2. Ubica `qa.exe` dentro de `qa-<version>/bin/`.
3. Agrega esa carpeta al `PATH` o ejecuta el binario directamente.

PowerShell (ejecucion directa):

```powershell
.\qa-0.1.0\bin\qa.exe --help
```

### Opcion C: Ejecutar desde codigo fuente

Requisitos:

- Python 3.14+
- uv

```bash
git clone https://github.com/UPT-FAING-EPIS/proyecto-si783-2026-i-u1-analizador-de-rendimiento-de-consultas.git
cd proyecto-si783-2026-i-u1-analizador-de-rendimiento-de-consultas
uv sync
uv run query_analyzer
```

Tambien puedes usar:

```bash
python -m query_analyzer
```

## Canales de distribucion

El pipeline de release publica automaticamente en estos canales:

- Homebrew Tap: `andre-carbajal/tap`
- Scoop Bucket: `andre` (`https://github.com/andre-carbajal/scoop-bucket`)
- Snapcraft: paquete `qa`

## Uso rapido

```bash
qa --help
```

Si lo ejecutas desde fuente:

```bash
uv run query_analyzer --help
```

## AI Integration (v2.0.0+)

Query Analyzer now supports **optional AI-powered analysis** via pluggable LLM providers.

### Configure Your LLM Provider

To enable AI insights, set these environment variables:

```bash
# Required: All three must be set
export QA_AI_BASE_URL="https://api.openai.com/v1"     # LLM provider URL
export QA_AI_API_KEY="sk-..."                         # API key
export QA_AI_MODEL="gpt-4o-mini"                      # Model identifier

# Optional: Timeout in seconds (default: 30)
export QA_AI_TIMEOUT_SECONDS="30"
```

### Supported LLM Providers

| Provider | Base URL | Model Examples | Cost |
|----------|----------|-----------------|------|
| **OpenAI** | `https://api.openai.com/v1` | `gpt-4o-mini`, `gpt-4` | Paid |
| **DeepSeek** | `https://api.deepseek.com/v1` | `deepseek-chat` | Paid (cheap) |
| **Groq** | `https://api.groq.com/openai/v1` | `mixtral-8x7b-32768` | Free |
| **Ollama (Local)** | `http://localhost:11434/v1` | `mistral`, `llama2` | Free (local) |

### Example: Using OpenAI

```bash
export QA_AI_BASE_URL="https://api.openai.com/v1"
export QA_AI_API_KEY="sk-proj-..."
export QA_AI_MODEL="gpt-4o-mini"

uv run query_analyzer analyze \
  --engine postgresql \
  --host localhost \
  < query.sql
```

Output includes:
- **Plan Summary**: Brief description of execution plan
- **Metrics**: Execution time, rows examined, etc.
- **AI Analysis** (if configured):
  - Summary of query performance
  - Observations (potential issues detected)
  - Recommendations for optimization

### Example: Using Local Ollama

```bash
# Start Ollama with Mistral model
ollama run mistral

# In another terminal
export QA_AI_BASE_URL="http://localhost:11434/v1"
export QA_AI_API_KEY="ollama"
export QA_AI_MODEL="mistral"

uv run query_analyzer analyze --engine sqlite < query.sql
```

### What Happens If AI Is Not Configured?

The tool gracefully falls back to raw EXPLAIN analysis:
- ✅ Plan tree visualization
- ✅ Execution metrics
- ✅ Performance stats
- ❌ AI-powered recommendations (skipped)

### Programmatic Usage

```python
from query_analyzer.adapters import AdapterRegistry
from query_analyzer.core import AIAnalyzer

# Execute EXPLAIN
config = ConnectionConfig(
    engine="postgresql",
    host="localhost",
    database="mydb",
    username="user",
    password="pass"
)
adapter = AdapterRegistry.create("postgresql", config)
report = adapter.execute_explain("SELECT * FROM users")

# Get AI insights (if configured)
analyzer = AIAnalyzer()
if analyzer.is_configured():
    ai_result = analyzer.analyze(report)
    print(f"Summary: {ai_result.summary}")
    print(f"Observations: {ai_result.observations}")
    print(f"Recommendations: {ai_result.recommendations}")
else:
    print("AI not configured")
```

---

## Entorno opcional con Docker

Si quieres levantar servicios de base de datos locales para pruebas:

```bash
cp .env.example .env
make up
make health
```

Servicios incluidos: PostgreSQL, MySQL, MongoDB, Redis, InfluxDB, Neo4j y CockroachDB.

Para apagar:

```bash
make down
```

## Releases

El workflow `.github/workflows/release.yml` se ejecuta automaticamente cuando haces push de un tag `v*`.

- Construye binarios por plataforma con PyInstaller.
- Publica artefactos de release.
- Publica y actualiza package managers via JReleaser.

Comandos de instalacion por canal:

```bash
# Homebrew
brew tap andre-carbajal/tap
brew install qa
```

```bash
# Snap
sudo snap install qa
```

```powershell
# Scoop
scoop bucket add andre https://github.com/andre-carbajal/scoop-bucket.git
scoop install qa
```

## Para desarrolladores

Si quieres contribuir, revisa `CONTRIBUTING.md` para setup, pruebas, estilo de codigo y flujo de PRs.
