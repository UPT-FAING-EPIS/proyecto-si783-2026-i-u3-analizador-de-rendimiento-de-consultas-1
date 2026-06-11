"""Servicio y modelos de diagnóstico de conexiones a bases de datos."""

from __future__ import annotations

import re
import socket
import time
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from query_analyzer.adapters import AdapterRegistry
from query_analyzer.adapters.models import ConnectionConfig


class DiagnosticCheck(BaseModel):
    """Representa el resultado de una comprobación individual de diagnóstico.

    Attributes:
        name: Nombre de la comprobación (ej. 'TCP Ping').
        status: Resultado ('success', 'failed', 'skipped').
        message: Mensaje descriptivo con el resultado o detalle.
        duration_ms: Tiempo tomado por la comprobación en milisegundos.
    """

    name: str
    status: str  # 'success', 'failed', 'skipped'
    message: str
    duration_ms: float


class ConnectionDiagnostic(BaseModel):
    """Diagnóstico de conexión completo para un perfil.

    Attributes:
        profile_name: Nombre del perfil.
        engine: Nombre del motor de base de datos.
        endpoint: Endpoint de conexión (ej. host:port o ruta de archivo).
        status: Estado agregado ('connected', 'service_unreachable', etc.).
        checks: Lista ordenada de comprobaciones individuales.
        duration_ms: Duración total de las pruebas.
        checked_at: Fecha y hora del diagnóstico en UTC.
        safe_message: Mensaje de error seguro (sin contraseñas).
        technical_detail: Detalle técnico completo del error (sanitizado).
    """

    profile_name: str
    engine: str
    endpoint: str
    status: str  # 'connected', 'service_unreachable', 'authentication_failed',
    # 'database_missing', 'timeout', 'configuration_error', 'unknown_error'
    checks: list[DiagnosticCheck]
    duration_ms: float
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    safe_message: str
    technical_detail: str | None = None


class ConnectionDiagnosticsService:
    """Servicio para ejecutar diagnósticos progresivos sobre perfiles de conexión."""

    @staticmethod
    def sanitize_secrets(text: str, config: ConnectionConfig) -> str:
        """Sanitiza secretos (contraseñas y tokens) en un texto.

        Args:
            text: El texto original que puede contener secretos.
            config: Configuración de conexión que contiene las credenciales.

        Returns:
            El texto sanitizado con los secretos enmascarados.
        """
        if not text:
            return text

        sanitized = text

        # 1. Ocultar secretos en URIs (scheme://user:password@host)
        sanitized = re.sub(
            r"([a-zA-Z0-9+.-]+://[^/@\s:]*):([^/@\s]+)(@[^/\s]+)", r"\1:********\3", sanitized
        )

        # 2. Ocultar parámetros password=, token=, api_key=, secret=, pwd=
        sanitized = re.sub(
            r"(?i)(password|token|api_key|secret|pwd)\s*=\s*([^\s,;\'\"]+)",
            r"\1=********",
            sanitized,
        )

        # 3. Ocultar cabeceras Bearer
        sanitized = re.sub(r"(?i)(bearer\s+)([^\s,;\'\"]+)", r"\1********", sanitized)

        # 4. Obtener todos los secretos exactos a reemplazar
        secrets: list[str] = []
        if config.password:
            secrets.append(config.password)

        # Buscar en configuraciones extra
        for key, value in config.extra.items():
            if any(k in key.lower() for k in ["token", "password", "key", "secret", "pwd"]):
                if isinstance(value, str) and value:
                    secrets.append(value)

        # 5. Reemplazar secretos exactos (incluyendo longitudes de 1 o 2 caracteres)
        for secret in secrets:
            if not secret:
                continue
            if len(secret) > 2:
                sanitized = sanitized.replace(secret, "********")
            else:
                escaped = re.escape(secret)
                pattern = (
                    r"""(?P<prefix>^|[\s"':/=\(\)\[\]\{\},;])("""
                    + escaped
                    + r""")(?P<suffix>$|[\s"':/=\(\)\[\]\{\},;\.])"""
                )
                prev = ""
                while prev != sanitized:
                    prev = sanitized
                    sanitized = re.sub(pattern, r"\g<prefix>********\g<suffix>", sanitized)

        return sanitized

    @classmethod
    def _classify_error(cls, engine: str, exc: Exception) -> tuple[str, str]:
        """Clasifica una excepción de conexión en un estado diagnóstico y un mensaje seguro.

        Args:
            engine: Nombre del motor de base de datos.
            exc: La excepción capturada.

        Returns:
            Tupla de (status, safe_message)
        """
        exc_message = str(exc)
        exc_class_name = exc.__class__.__name__
        message_lower = exc_message.lower()

        # R04. Clasificar TimeoutError, socket.timeout y mensajes timed out/timeout como timeout
        if (
            isinstance(exc, (TimeoutError, socket.timeout))
            or "timed out" in message_lower
            or "timeout" in message_lower
        ):
            return (
                "timeout",
                "Tiempo de espera agotado al conectar al servidor de base de datos.",
            )

        # PostgreSQL (psycopg2)
        if engine == "postgresql":
            pgcode = getattr(exc, "pgcode", None)
            if pgcode:
                if pgcode in ("28000", "28P01"):
                    return (
                        "authentication_failed",
                        "Error de autenticación. Verifique el usuario y la contraseña de PostgreSQL.",
                    )
                elif pgcode == "3D000":
                    return (
                        "database_missing",
                        "La base de datos especificada no existe en el servidor PostgreSQL.",
                    )
                elif pgcode in ("08001", "08004", "08006"):
                    return (
                        "service_unreachable",
                        "El servidor PostgreSQL rechazó la conexión o el puerto está inaccesible.",
                    )
            # Detección por mensajes alternativos si pgcode no está presente
            if "password authentication failed" in message_lower:
                return (
                    "authentication_failed",
                    "Error de autenticación. Verifique el usuario y la contraseña de PostgreSQL.",
                )
            if "does not exist" in message_lower:
                return (
                    "database_missing",
                    "La base de datos especificada no existe en el servidor PostgreSQL.",
                )

        # MySQL (pymysql)
        elif engine == "mysql":
            args = getattr(exc, "args", None)
            if args and isinstance(args, tuple) and len(args) > 0:
                err_code = args[0]
                if err_code == 1045:
                    return (
                        "authentication_failed",
                        "Error de autenticación (Access denied). Verifique el usuario y la contraseña de MySQL.",
                    )
                elif err_code in (1049, 1044):
                    return (
                        "database_missing",
                        "La base de datos especificada no existe en el servidor MySQL.",
                    )
                elif err_code in (2002, 2003, 2006):
                    return (
                        "service_unreachable",
                        "No se pudo conectar al servidor MySQL. Verifique que el servicio esté corriendo.",
                    )
                elif err_code == 2013:
                    return (
                        "timeout",
                        "Tiempo de espera agotado al conectar con el servidor MySQL.",
                    )
            if "access denied for user" in message_lower:
                if "to database" in message_lower:
                    return (
                        "database_missing",
                        "La base de datos especificada no existe en el servidor MySQL.",
                    )
                return (
                    "authentication_failed",
                    "Error de autenticación. Verifique el usuario y la contraseña de MySQL.",
                )
            if "unknown database" in message_lower:
                return (
                    "database_missing",
                    "La base de datos especificada no existe en el servidor MySQL.",
                )

        # SQLite
        elif engine == "sqlite":
            if "unable to open database file" in message_lower:
                return (
                    "configuration_error",
                    "No se pudo abrir el archivo de base de datos SQLite. Verifique la ruta y permisos.",
                )

        # Fallback genérico para otros motores basados en texto
        if (
            any(
                x in message_lower
                for x in [
                    "access denied",
                    "auth failed",
                    "login failed",
                    "unauthorized",
                    "invalid password",
                    "invalid user",
                    "authentication failed",
                ]
            )
            or "auth" in exc_class_name.lower()
        ):
            return (
                "authentication_failed",
                f"Error de autenticación al conectar al motor {engine}.",
            )

        if any(
            x in message_lower
            for x in ["database not found", "does not exist", "unknown database", "keyspace"]
        ):
            return (
                "database_missing",
                f"La base de datos o espacio de nombres especificado no existe en {engine}.",
            )

        if any(x in message_lower for x in ["connection refused", "unreachable", "cannot connect"]):
            return (
                "service_unreachable",
                f"No se pudo establecer comunicación de red con el servicio {engine}.",
            )

        return "unknown_error", "Error de conexión inesperado."

    @classmethod
    def create_connected_diagnostic(
        cls, profile_name: str, config: ConnectionConfig, duration_ms: float = 0.0
    ) -> ConnectionDiagnostic:
        """Crea un ConnectionDiagnostic exitoso de manera centralizada.

        Args:
            profile_name: Nombre del perfil.
            config: Configuración de conexión.
            duration_ms: Duración total del diagnóstico.

        Returns:
            Objeto ConnectionDiagnostic configurado como exitoso.
        """
        if config.engine == "sqlite":
            endpoint = config.database
        else:
            endpoint = f"{config.host or 'localhost'}:{config.port or '-'}"

        return ConnectionDiagnostic(
            profile_name=profile_name,
            engine=config.engine,
            endpoint=endpoint,
            status="connected",
            checks=[
                DiagnosticCheck(
                    name="Validación de Configuración",
                    status="success",
                    message="Configuración válida",
                    duration_ms=0.0,
                ),
                DiagnosticCheck(
                    name="Conectividad de Red (TCP)",
                    status="success" if config.engine != "sqlite" else "skipped",
                    message="Omitido/Exitoso"
                    if config.engine == "sqlite"
                    else f"Puerto {config.port} accesible en {config.host}",
                    duration_ms=0.0,
                ),
                DiagnosticCheck(
                    name="Autenticación y Driver",
                    status="success",
                    message="Conexión establecida exitosamente",
                    duration_ms=0.0,
                ),
                DiagnosticCheck(
                    name="Consulta de Operatividad",
                    status="success",
                    message="Consulta de verificación exitosa (SELECT 1/Ping)",
                    duration_ms=0.0,
                ),
            ],
            duration_ms=duration_ms,
            checked_at=datetime.now(UTC),
            safe_message="Conexión exitosa",
        )

    @classmethod
    def run_diagnostics(cls, profile_name: str, config: ConnectionConfig) -> ConnectionDiagnostic:
        """Ejecuta un diagnóstico completo y progresivo sobre la configuración de conexión.

        Args:
            profile_name: Nombre del perfil de conexión.
            config: Configuración de conexión.

        Returns:
            Objeto ConnectionDiagnostic con el resultado de las pruebas.
        """
        start_total = time.perf_counter()
        checks: list[DiagnosticCheck] = []
        status = "connected"
        safe_message = "Conexión exitosa"
        technical_detail: str | None = None

        # Obtener endpoint seguro para mostrar
        if config.engine == "sqlite":
            endpoint = config.database
        else:
            endpoint = f"{config.host or 'localhost'}:{config.port or '-'}"

        # 1. Comprobación de Configuración
        start_check = time.perf_counter()
        config_valid = True
        config_msg = "Configuración válida"

        if not config.engine:
            config_valid = False
            config_msg = "Motor de base de datos no especificado"
        elif config.engine != "sqlite" and not config.host:
            config_valid = False
            config_msg = f"El motor {config.engine} requiere un host especificado"

        duration = (time.perf_counter() - start_check) * 1000
        checks.append(
            DiagnosticCheck(
                name="Validación de Configuración",
                status="success" if config_valid else "failed",
                message=config_msg,
                duration_ms=duration,
            )
        )

        if not config_valid:
            status = "configuration_error"
            safe_message = config_msg
            # Agregar los checks restantes como skipped para que siempre existan los 4 checks
            checks.append(
                DiagnosticCheck(
                    name="Conectividad de Red (TCP)",
                    status="skipped",
                    message="Omitido debido a fallo de configuración",
                    duration_ms=0.0,
                )
            )
            checks.append(
                DiagnosticCheck(
                    name="Autenticación y Driver",
                    status="skipped",
                    message="Omitido debido a fallo de configuración",
                    duration_ms=0.0,
                )
            )
            checks.append(
                DiagnosticCheck(
                    name="Consulta de Operatividad",
                    status="skipped",
                    message="Omitido debido a fallo de configuración",
                    duration_ms=0.0,
                )
            )
            total_duration = (time.perf_counter() - start_total) * 1000
            return ConnectionDiagnostic(
                profile_name=profile_name,
                engine=config.engine,
                endpoint=endpoint,
                status=status,
                checks=checks,
                duration_ms=total_duration,
                checked_at=datetime.now(UTC),
                safe_message=safe_message,
            )

        # 2. Comprobación de Red TCP (si aplica)
        is_network_engine = config.engine != "sqlite"
        if is_network_engine and config.host and config.port:
            start_check = time.perf_counter()
            tcp_ok = False
            tcp_msg = ""
            try:
                # Intento de resolución DNS y conexión por socket
                addr_info = socket.getaddrinfo(
                    config.host, config.port, socket.AF_UNSPEC, socket.SOCK_STREAM
                )
                for res in addr_info:
                    af, socktype, proto, canonname, sa = res
                    s = None
                    try:
                        s = socket.socket(af, socktype, proto)
                        s.settimeout(2.0)  # Timeout corto para diagnosticar rápido
                        s.connect(sa)
                        tcp_ok = True
                        tcp_msg = f"Puerto {config.port} accesible en {config.host}"
                        break
                    except Exception as e:
                        tcp_msg = f"Puerto {config.port} cerrado o inaccesible: {e}"
                    finally:
                        if s:
                            s.close()
            except socket.gaierror as e:
                tcp_msg = f"No se pudo resolver el host '{config.host}': {e}"
            except Exception as e:
                tcp_msg = f"Error de socket TCP: {e}"

            duration = (time.perf_counter() - start_check) * 1000
            checks.append(
                DiagnosticCheck(
                    name="Conectividad de Red (TCP)",
                    status="success" if tcp_ok else "failed",
                    message=tcp_msg,
                    duration_ms=duration,
                )
            )

            if not tcp_ok:
                status, safe_message = cls._classify_error(config.engine, Exception(tcp_msg))
                # Si _classify_error no clasifica el error de socket TCP como timeout/service_unreachable
                if status not in ("timeout", "service_unreachable"):
                    status = "service_unreachable"
                safe_message = (
                    f"No se pudo conectar al puerto {config.port} en el host {config.host}."
                )
                technical_detail = tcp_msg
                # Omitir comprobaciones posteriores
                checks.append(
                    DiagnosticCheck(
                        name="Autenticación y Driver",
                        status="skipped",
                        message="Omitido debido a fallo de red",
                        duration_ms=0.0,
                    )
                )
                checks.append(
                    DiagnosticCheck(
                        name="Consulta de Operatividad",
                        status="skipped",
                        message="Omitido debido a fallo de red",
                        duration_ms=0.0,
                    )
                )
                total_duration = (time.perf_counter() - start_total) * 1000
                return ConnectionDiagnostic(
                    profile_name=profile_name,
                    engine=config.engine,
                    endpoint=endpoint,
                    status=status,
                    checks=checks,
                    duration_ms=total_duration,
                    checked_at=datetime.now(UTC),
                    safe_message=safe_message,
                    technical_detail=cls.sanitize_secrets(technical_detail, config),
                )
        else:
            checks.append(
                DiagnosticCheck(
                    name="Conectividad de Red (TCP)",
                    status="skipped",
                    message="Omitido (Conexión local/archivo)",
                    duration_ms=0.0,
                )
            )

        # 3. Autenticación y Driver Connect
        start_check = time.perf_counter()
        connected_ok = False
        connect_msg = "Conexión establecida exitosamente"
        adapter = None

        try:
            if not AdapterRegistry.is_registered(config.engine):
                raise ValueError(f"Motor '{config.engine}' no soportado o registrado")

            adapter = AdapterRegistry.create(config.engine, config)
            adapter.connect()
            connected_ok = True
        except Exception as e:
            connect_msg = str(e)
            status, safe_message = cls._classify_error(config.engine, e)
            technical_detail = connect_msg
            if adapter:
                try:
                    adapter.disconnect()
                except Exception:
                    pass
        finally:
            duration = (time.perf_counter() - start_check) * 1000

        checks.append(
            DiagnosticCheck(
                name="Autenticación y Driver",
                status="success" if connected_ok else "failed",
                message=cls.sanitize_secrets(connect_msg, config),
                duration_ms=duration,
            )
        )

        if not connected_ok:
            checks.append(
                DiagnosticCheck(
                    name="Consulta de Operatividad",
                    status="skipped",
                    message="Omitido debido a fallo de conexión",
                    duration_ms=0.0,
                )
            )
            total_duration = (time.perf_counter() - start_total) * 1000
            return ConnectionDiagnostic(
                profile_name=profile_name,
                engine=config.engine,
                endpoint=endpoint,
                status=status,
                checks=checks,
                duration_ms=total_duration,
                checked_at=datetime.now(UTC),
                safe_message=safe_message,
                technical_detail=cls.sanitize_secrets(technical_detail or "", config),
            )

        # 4. Consulta de Operatividad
        start_check = time.perf_counter()
        test_ok = False
        test_msg = ""
        try:
            if adapter and adapter.test_connection():
                test_ok = True
                test_msg = "Consulta de verificación exitosa (SELECT 1/Ping)"
            else:
                test_msg = "Fallo la consulta de verificación básica"
        except Exception as e:
            test_msg = f"Error al ejecutar consulta de prueba: {e}"
            status = "unknown_error"
            safe_message = "Fallo en la prueba de operatividad de la conexión."
            technical_detail = test_msg
        finally:
            if adapter:
                try:
                    adapter.disconnect()
                except Exception:
                    pass
            duration = (time.perf_counter() - start_check) * 1000

        checks.append(
            DiagnosticCheck(
                name="Consulta de Operatividad",
                status="success" if test_ok else "failed",
                message=cls.sanitize_secrets(test_msg, config),
                duration_ms=duration,
            )
        )

        if not test_ok and status == "connected":
            status = "unknown_error"
            safe_message = "Fallo en la prueba de operatividad de la conexión."
            technical_detail = test_msg

        total_duration = (time.perf_counter() - start_total) * 1000
        return ConnectionDiagnostic(
            profile_name=profile_name,
            engine=config.engine,
            endpoint=endpoint,
            status=status,
            checks=checks,
            duration_ms=total_duration,
            checked_at=datetime.now(UTC),
            safe_message=safe_message,
            technical_detail=cls.sanitize_secrets(technical_detail or "", config)
            if technical_detail
            else None,
        )
