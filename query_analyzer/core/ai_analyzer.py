"""AI Analyzer - Cliente genérico para análisis de queries con IA.

Soporta cualquier proveedor compatible con OpenAI API:
- OpenAI (https://api.openai.com/v1)
- DeepSeek (https://api.deepseek.com/v1)
- Groq (https://api.groq.com/openai/v1)
- Ollama local (http://localhost:11434/v1)
- Anthropic (vía DeepSeek: https://api.deepseek.com/anthropic)
- etc.

Variables de entorno requeridas:
- QA_AI_BASE_URL: URL base del proveedor (ej: https://api.openai.com/v1)
- QA_AI_API_KEY: Token de autenticación
- QA_AI_MODEL: Modelo a usar (opcional, default: gpt-4o)
"""

import json
import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AIAnalysisResult:
    """Resultado del análisis con IA."""

    summary: str
    """Resumen del EXPLAIN en lenguaje natural."""

    observations: list[str] = field(default_factory=list)
    """Observaciones puntuales del plan."""

    recommendations: list[str] = field(default_factory=list)
    """Recomendaciones accionables."""

    raw_response: str | None = None
    """Respuesta completa de la IA (para debugging)."""


class AIAnalyzer:
    """Cliente genérico de IA para análisis de queries.

    Compatible con cualquier proveedor que siga OpenAI API.
    Detecta automáticamente si la IA está configurada.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        """Inicializa con parámetros explícitos o variables de entorno como fallback.

        Variables de entorno:
        - QA_AI_BASE_URL: URL base del proveedor (requerida si no se pasa por parámetro)
        - QA_AI_API_KEY: Token de autenticación (requerida si no se pasa por parámetro)
        - QA_AI_MODEL: Modelo a usar (default: gpt-4o)
        """
        self.base_url = (base_url or os.environ.get("QA_AI_BASE_URL", "")).strip()
        self.api_key = (api_key or os.environ.get("QA_AI_API_KEY", "")).strip()
        self.model = (model or os.environ.get("QA_AI_MODEL", "gpt-4o")).strip()

        # Disponibilidad de IA
        self.available = bool(self.base_url and self.api_key)

        if self.available:
            logger.info(
                f"AI Analyzer initialized with provider: {self._extract_provider()} "
                f"(model: {self.model})"
            )
        else:
            logger.debug("AI Analyzer disabled (QA_AI_BASE_URL or QA_AI_API_KEY not set)")

    def is_configured(self) -> bool:
        """Retorna si el analizador de IA está configurado."""
        return self.available

    def _extract_provider(self) -> str:
        """Extrae el nombre del proveedor desde la URL.

        Returns:
            Nombre del proveedor (ej: 'OpenAI', 'DeepSeek', 'Ollama')
        """
        if not self.base_url:
            return "Unknown"

        url_lower = self.base_url.lower()
        if "openai" in url_lower:
            return "OpenAI"
        elif "deepseek" in url_lower:
            return "DeepSeek"
        elif "groq" in url_lower:
            return "Groq"
        elif "localhost" in url_lower or "127.0.0.1" in url_lower:
            return "Ollama (local)"
        else:
            return "Custom Provider"

    def analyze(
        self,
        plan_json: str | dict,
        query: str,
        engine: str,
    ) -> AIAnalysisResult | None:
        """Analiza un EXPLAIN con IA.

        Args:
            plan_json: Plan de ejecución como JSON string o dict
            query: Consulta SQL original
            engine: Motor de base de datos (postgresql, mysql, etc.)

        Returns:
            AIAnalysisResult con análisis, o None si no está configurada IA

        Raises:
            Exception: Si hay error al comunicarse con la IA
        """
        if not self.available:
            return None

        try:
            # Convertir plan a string si es dict
            if isinstance(plan_json, dict):
                plan_str = json.dumps(plan_json, indent=2)
            else:
                plan_str = plan_json

            # Construir prompt
            prompt = self._build_prompt(plan_str, query, engine)

            # Llamar a la IA
            response = self._call_ai(prompt)

            if not response:
                logger.warning("Empty response from AI provider")
                return None

            # Parsear respuesta
            result = self._parse_response(response)

            logger.info(f"AI analysis complete for {engine} query")
            return result

        except Exception as e:
            logger.error(f"Error during AI analysis: {e}")
            raise

    def _build_prompt(self, plan_json: str, query: str, engine: str) -> str:
        """Construye el prompt para enviar a la IA.

        Args:
            plan_json: Plan de ejecución en JSON
            query: Consulta SQL
            engine: Motor de base de datos

        Returns:
            Prompt formateado para la IA
        """
        return f"""You are an expert database query performance analyst.

Analyze the following EXPLAIN plan and provide insights in a clear, concise format.

DATABASE ENGINE: {engine}

QUERY:
{query}

EXPLAIN PLAN (JSON):
{plan_json}

Please provide your analysis in this exact format:

SUMMARY:
[One paragraph explaining the overall plan efficiency]

OBSERVATIONS:
- [Observation 1]
- [Observation 2]
- [Observation 3 if applicable]

RECOMMENDATIONS:
- [Recommendation 1 if applicable]
- [Recommendation 2 if applicable]
- [Recommendation 3 if applicable]

Be specific, mention table names and operation types. Focus on what the query actually does, not hypothetical optimizations."""

    def _call_ai(self, prompt: str) -> str | None:
        """Llama al proveedor de IA.

        Args:
            prompt: Prompt a enviar

        Returns:
            Respuesta de la IA como string

        Raises:
            ImportError: Si falta la librería requests
            Exception: Si hay error en la API
        """
        try:
            import requests
        except ImportError as error:
            raise ImportError(
                "requests library required for AI analysis. Install with: pip install requests"
            ) from error

        # Construir headers
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Construir payload (formato OpenAI API)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert database performance analyst. Provide concise, actionable insights.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.3,  # Bajo para respuestas consistentes
            "max_tokens": 1000,
        }

        try:
            # Llamar API
            response = requests.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()

            # Parsear respuesta
            data = response.json()
            if "choices" not in data or not data["choices"]:
                logger.warning("Unexpected response format from AI provider")
                return None

            content = data["choices"][0].get("message", {}).get("content", "")
            return content if content else None

        except requests.exceptions.Timeout as error:
            raise TimeoutError("AI provider timeout after 30s") from error
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(
                f"AI provider error: {e.response.status_code} - {e.response.text}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Failed to call AI provider: {e}") from e

    def _parse_response(self, response: str) -> AIAnalysisResult:
        """Parsea la respuesta de la IA.

        Args:
            response: Respuesta de la IA

        Returns:
            AIAnalysisResult con campos parseados
        """
        result = AIAnalysisResult(
            summary="",
            observations=[],
            recommendations=[],
            raw_response=response,
        )

        # Parsear secciones
        sections = response.split("\n\n")

        for section in sections:
            section = section.strip()
            if not section:
                continue

            if section.startswith("SUMMARY:"):
                result.summary = section.replace("SUMMARY:", "").strip()

            elif section.startswith("OBSERVATIONS:"):
                obs_text = section.replace("OBSERVATIONS:", "").strip()
                for line in obs_text.split("\n"):
                    line = line.strip()
                    if line and line.startswith("- "):
                        result.observations.append(line[2:].strip())

            elif section.startswith("RECOMMENDATIONS:"):
                rec_text = section.replace("RECOMMENDATIONS:", "").strip()
                for line in rec_text.split("\n"):
                    line = line.strip()
                    if line and line.startswith("- "):
                        result.recommendations.append(line[2:].strip())

        return result
