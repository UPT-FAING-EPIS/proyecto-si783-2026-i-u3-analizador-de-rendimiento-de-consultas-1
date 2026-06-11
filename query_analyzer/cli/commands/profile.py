"""Comandos CLI para gestionar perfiles."""

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt

from query_analyzer.adapters import (
    AdapterRegistry,
    BaseAdapter,
)
from query_analyzer.cli.utils import OutputFormatter
from query_analyzer.config import (
    ConfigManager,
    ConfigValidationError,
    ProfileConfig,
    ProfileNotFoundError,
)

app = typer.Typer(help="Gestionar perfiles de conexión")
console = Console()


def _get_adapter(engine: str) -> type[BaseAdapter]:
    """Obtiene la clase del adapter para un engine específico.

    Esta función es un helper privado que se usa internamente para
    instanciar adapters basados en el nombre del motor de base de datos.

    Args:
        engine: Nombre del motor ('postgresql', 'mysql', 'sqlite', 'cockroachdb', etc.)

    Returns:
        Clase del adapter correspondiente al engine.

    Raises:
        ValueError: Si el engine no está soportado o no registrado en el registry.

    """
    engine_key = engine.lower()
    if not AdapterRegistry.is_registered(engine_key):
        raise ValueError(f"Engine {engine} no soportado")
    return AdapterRegistry._registry[engine_key]


@app.command()
def add(
    name: str = typer.Argument(..., help="Nombre del nuevo perfil"),
    engine: str | None = typer.Option(
        None,
        "--engine",
        "-e",
        help="postgresql | mysql | sqlite | redis | cockroachdb | yugabytedb | mongodb | mssql",
    ),
    host: str | None = typer.Option(None, "--host", "-h", help="Host de la BD"),
    port: int | None = typer.Option(None, "--port", "-p", help="Puerto"),
    database: str | None = typer.Option(None, "--database", "-d", help="Nombre de DB"),
    username: str | None = typer.Option(None, "--username", "-u", help="Usuario"),
    password: str | None = typer.Option(
        None, "--password", "-pw", help="Password (interactivo si omitido)"
    ),
) -> None:
    r"""Agregar un nuevo perfil de conexión a la configuración.

    Crea un nuevo perfil de conexión interactivamente o mediante opciones CLI.
    Si se omiten parámetros, el comando entra en modo interactivo solicitando
    cada valor. Las credenciales se cifran y almacenan de forma segura.

    Args:
        name: Nombre único del nuevo perfil (ej: 'staging', 'local-postgres').
        engine: Motor de base de datos ('postgresql' o 'mysql'). Interactivo si omitido.
        host: Host del servidor. Interactivo si omitido.
        port: Puerto del servidor. Interactivo si omitido.
        database: Nombre de la base de datos. Interactivo si omitido.
        username: Usuario de conexión. Interactivo si omitido.
        password: Contraseña (siempre oculta en input). Interactivo si omitido.

    Raises:
        typer.Exit: Con código 1 si hay error de validación o I/O.

    Example:
        \b
        # Modo interactivo
        $ qa profile add staging
        Engine [postgresql]: mysql
        Host [localhost]: prod-db.example.com
        Port [3306]:
        Database: myapp
        Username: analyst
        Password (hidden): ****

        # Modo no-interactivo
        $ qa profile add local-dev -e postgresql -h localhost -p 5432 \
            -d dev_db -u postgres -pw secret
    """
    try:
        config_mgr = ConfigManager()

        # Modo interactivo: pedir datos faltantes
        if engine is None:
            engine = Prompt.ask(
                "Engine", choices=["postgresql", "mysql", "mssql"], default="postgresql"
            )

        if host is None:
            host = Prompt.ask("Host", default="localhost")

        if port is None:
            port = int(
                Prompt.ask(
                    "Port",
                    default={"postgresql": "5432", "mysql": "3306", "mssql": "1433"}.get(
                        engine, "1433"
                    ),
                )
            )

        if database is None:
            database = Prompt.ask("Database")

        if username is None:
            username = Prompt.ask(
                "Username",
                default={"postgresql": "postgres", "mysql": "root", "mssql": "sa"}.get(
                    engine, "sa"
                ),
            )

        if password is None:
            password = Prompt.ask("Password", password=True)

        # Crear perfil
        profile = ProfileConfig(
            engine=engine,
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
        )

        # Agregar a configuración
        config_mgr.add_profile(name, profile)

        OutputFormatter.print_success(f"Perfil '{name}' agregado exitosamente")

    except ConfigValidationError as e:
        OutputFormatter.print_error(f"Error de validación: {e}")
        raise typer.Exit(code=1) from None
    except Exception as e:
        OutputFormatter.print_error(f"Error: {e}")
        raise typer.Exit(code=1) from None


@app.command()
def list() -> None:
    r"""Listar todos los perfiles de conexión configurados.

    Muestra una tabla de todos los perfiles guardados con información de:
    - Nombre del perfil (marcado con [DEFAULT] si es el perfil por defecto)
    - Engine (postgresql, mysql, sqlite, cockroachdb, etc.)
    - Host y puerto
    - Nombre de la base de datos
    - Usuario de conexión

    Las contraseñas no se muestran por seguridad.

    Returns:
        Imprime tabla formateada en la consola.

    Example:
        \b
        $ qa profile list
        Perfiles de Conexion
        ┏━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━┳━━━━━┓
        ┃ Nombre ┃ Engine ┃ Host   ┃ DB ┃ User┃
        ┡━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━╇━━━━┩
        │ test * │ postgr │ localh │ qy │ pgr│
        └────────┴────────┴────────┴────┴────┘
    """
    try:
        config_mgr = ConfigManager()
        config = config_mgr.load_config()
        profiles = config_mgr.list_profiles()

        if not profiles:
            OutputFormatter.print_info("No hay perfiles configurados")
            return

        table = OutputFormatter.create_profiles_table(profiles, config.default_profile)
        console.print()
        console.print(table)
        console.print()

    except Exception as e:
        OutputFormatter.print_error(f"Error: {e}")
        raise typer.Exit(code=1) from None


@app.command()
def test(
    name: str = typer.Argument(..., help="Nombre del perfil a probar"),
) -> None:
    r"""Probar la conexión a un perfil de base de datos.

    Valida que el perfil especificado tenga una conexión activa y funcional
    al motor de base de datos correspondiente. Ejecuta:
    1. Validación del perfil (existencia y configuración)
    2. test_connection() del adapter
    3. Consultas diagnósticas según el engine

    Args:
        name: Nombre del perfil a probar (ej: 'local-postgres').

    Raises:
        typer.Exit: Con código 1 si el perfil no existe o la conexión falla.

    Example:
        \b
        $ qa profile test local-postgres
        Testing connection to 'local-postgres'...
        ✓ Connection successful
        ✓ PostgreSQL 14.2
        ✓ 1 active connection
    """
    try:
        config_mgr = ConfigManager()
        profile = config_mgr.get_profile(name)

        connection_config = config_mgr.get_connection_config(name)

        console.print(f"Testing connection to '[bold]{name}[/bold]'...")

        from query_analyzer.core.connection_diagnostics import ConnectionDiagnosticsService

        diagnostic = ConnectionDiagnosticsService.run_diagnostics(name, connection_config)

        for check in diagnostic.checks:
            if check.status == "success":
                status_char = "[green]✓[/green]"
            elif check.status == "failed":
                status_char = "[red]✗[/red]"
            else:
                status_char = "[yellow]-[/yellow]"

            duration_text = f" ({check.duration_ms:.1f}ms)" if check.status != "skipped" else ""
            console.print(f"  {status_char} {check.name}: {check.message}{duration_text}")

        console.print(f"  Fecha de diagnóstico: {diagnostic.checked_at.isoformat()}")
        console.print(f"  Duración total: {diagnostic.duration_ms:.1f}ms")

        if diagnostic.status == "connected":
            OutputFormatter.print_success(
                f"Connection successful: {profile.engine}@{diagnostic.endpoint}"
            )
        else:
            OutputFormatter.print_error(f"Error ({diagnostic.status}): {diagnostic.safe_message}")
            if diagnostic.technical_detail:
                console.print(f"  [dim]Technical detail: {diagnostic.technical_detail}[/dim]")
            raise typer.Exit(code=1)

    except ProfileNotFoundError:
        OutputFormatter.print_error(f"Perfil '{name}' no encontrado")
        raise typer.Exit(code=1) from None
    except typer.Exit:
        raise
    except Exception as e:
        OutputFormatter.print_error(f"Error: {e}")
        raise typer.Exit(code=1) from None


@app.command()
def set_default(
    name: str = typer.Argument(..., help="Nombre del perfil"),
) -> None:
    r"""Establecer un perfil como el perfil por defecto.

    Marca el perfil especificado como el perfil por defecto, que se usará
    automáticamente en comandos que no especifiquen explícitamente un perfil.

    Args:
        name: Nombre del perfil a establecer como default.

    Raises:
        typer.Exit: Con código 1 si el perfil no existe.

    Example:
        \b
        $ qa profile set-default production
        Perfil default establecido a 'production'
    """
    try:
        config_mgr = ConfigManager()
        config_mgr.set_default_profile(name)
        OutputFormatter.print_success(f"Perfil default establecido a '{name}'")

    except ProfileNotFoundError:
        OutputFormatter.print_error(f"Perfil '{name}' no encontrado")
        raise typer.Exit(code=1) from None
    except Exception as e:
        OutputFormatter.print_error(f"Error: {e}")
        raise typer.Exit(code=1) from None


@app.command()
def delete(
    name: str = typer.Argument(..., help="Nombre del perfil a eliminar"),
    force: bool = typer.Option(False, "--force", "-f", help="Sin confirmación"),
) -> None:
    r"""Eliminar un perfil de conexión.

    Elimina un perfil de la configuración. Solicita confirmación a menos
    que se use la opción --force.

    Args:
        name: Nombre del perfil a eliminar.
        force: Si True, elimina sin pedir confirmación.

    Raises:
        typer.Exit: Con código 1 si el perfil no existe o el usuario cancela.

    Example:
        \b
        $ qa profile delete staging
        ¿Eliminar perfil 'staging'? [y/N]: y
        Perfil 'staging' eliminado

        $ qa profile delete staging --force
        Perfil 'staging' eliminado
    """
    try:
        # Pedir confirmación si no hay --force
        if not force:
            if not Confirm.ask(f"¿Eliminar perfil '{name}'?"):
                OutputFormatter.print_info("Cancelado")
                return

        config_mgr = ConfigManager()
        config_mgr.delete_profile(name)
        OutputFormatter.print_success(f"Perfil '{name}' eliminado")

    except ProfileNotFoundError:
        OutputFormatter.print_error(f"Perfil '{name}' no encontrado")
        raise typer.Exit(code=1) from None
    except Exception as e:
        OutputFormatter.print_error(f"Error: {e}")
        raise typer.Exit(code=1) from None


@app.command()
def show(
    name: str = typer.Argument(..., help="Nombre del perfil"),
    show_password: bool = typer.Option(
        False, "--show-password", help="Mostrar password sin enmascarar"
    ),
) -> None:
    r"""Mostrar detalles completos de un perfil.

    Muestra la configuración completa de un perfil (host, puerto, usuario, etc.).
    Por defecto, la contraseña se enmascara por seguridad. Use --show-password
    para mostrar la contraseña en texto plano.

    Args:
        name: Nombre del perfil a mostrar.
        show_password: Si True, muestra la contraseña sin enmascarar.

    Raises:
        typer.Exit: Con código 1 si el perfil no existe.

    Example:
        \b
        $ qa profile show production
        Profile: production (DEFAULT)
        Engine: postgresql
        Host: prod-db.example.com
        Port: 5432
        Database: myapp_prod
        User: analyst
        Password: ****

        $ qa profile show production --show-password
        Password: super_secret_pwd
    """
    try:
        config_mgr = ConfigManager()
        config = config_mgr.load_config()
        profile = config_mgr.get_profile(name)

        is_default = name == config.default_profile
        console.print()
        console.print(
            OutputFormatter.format_profile(name, profile, is_default, mask_pwd=not show_password)
        )
        console.print()

    except ProfileNotFoundError:
        OutputFormatter.print_error(f"Perfil '{name}' no encontrado")
        raise typer.Exit(code=1) from None
    except Exception as e:
        OutputFormatter.print_error(f"Error: {e}")
        raise typer.Exit(code=1) from None
