"""Command-line interface for Time Visibility Tracker."""

import os
import platform
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import click
from rich.console import Console
from rich.prompt import Confirm, Prompt

from tvt import __version__
from tvt.config import (
    get_config_path,
    get_credentials_path,
    get_db_path,
    get_slack_token,
    load_config,
    load_credentials,
    save_config,
    save_credentials,
)
from tvt.process_manager import (
    cleanup_stale_pid_file,
    clear_pid_file,
    get_daemon_pid,
    read_pid_file,
    write_pid_file,
)
from tvt.storage.sqlite import SQLiteStorage
from tvt.summary import (
    export_summary_csv,
    generate_daily_summary,
    generate_weekly_summary,
)
from tvt.windows_service import (
    create_scheduled_task,
    delete_scheduled_task,
    is_task_scheduled,
)

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="tvt")
def main():
    """Time Visibility Tracker - Make invisible work time visible.

    Track your time across Slack huddles, Teams calls, and more to understand
    where your time actually goes beyond scheduled calendar events.
    """
    pass


@main.command()
def init():
    """Initialize TVT configuration interactively."""
    console.print("[bold]Time Visibility Tracker Setup[/bold]\n")

    config_path = get_config_path()
    creds_path = get_credentials_path()

    # Create config directory
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Check for existing config
    if config_path.exists():
        if not Confirm.ask("Configuration already exists. Overwrite?"):
            console.print("Setup cancelled.")
            return

    config = load_config()
    credentials = load_credentials()

    # Slack setup
    console.print("\n[bold cyan]Slack Integration[/bold cyan]")
    console.print(
        "To track Slack presence and huddles, you need a User OAuth Token.\n"
        "Create a Slack app at https://api.slack.com/apps with these scopes:\n"
        "  - users:read (for presence)\n"
        "  - users.profile:read (for huddle status)\n"
        "  - dnd:read (for DND status)\n"
    )

    if Confirm.ask("Configure Slack integration?"):
        token = Prompt.ask("Enter your Slack User OAuth Token (xoxp-...)")
        if token:
            credentials["slack"] = {"user_token": token}
            config["collectors"]["slack"]["enabled"] = True
            console.print("[green]Slack configured![/green]")
    else:
        config["collectors"]["slack"]["enabled"] = False

    # Database path
    console.print("\n[bold cyan]Database Location[/bold cyan]")
    default_db = "~/.tvt/data.db"
    db_path = Prompt.ask("Database path", default=default_db)
    config["database"]["path"] = db_path

    # Save configuration
    save_config(config)
    save_credentials(credentials)

    console.print(f"\n[green]Configuration saved to {config_path}[/green]")
    console.print(f"[green]Credentials saved to {creds_path}[/green]")
    console.print("\nRun [bold]tvt collect[/bold] to start tracking!")


@main.command()
@click.option(
    "--daemon", "-d", is_flag=True, help="Run continuously in the background"
)
@click.option(
    "--interval",
    "-i",
    default=30,
    help="Collection interval in seconds (default: 30)",
)
@click.option("--source", "-s", default="slack", help="Data source to collect from")
def collect(daemon: bool, interval: int, source: str):
    """Start collecting time visibility data.

    By default, runs a single collection cycle. Use --daemon to run continuously.
    """
    # Validate interval bounds to prevent API rate limiting issues
    if interval < 10:
        console.print(
            "[red]Error: Interval must be at least 10 seconds to avoid API rate limiting.[/red]"
        )
        sys.exit(1)
    if interval > 3600:
        console.print(
            "[red]Error: Interval cannot exceed 3600 seconds (1 hour).[/red]"
        )
        sys.exit(1)

    # Get storage
    storage = SQLiteStorage(get_db_path())

    if source == "slack":
        token = get_slack_token()
        if not token:
            console.print(
                "[red]Error: Slack token not configured.[/red]\n"
                "Run [bold]tvt init[/bold] or set SLACK_USER_TOKEN environment variable."
            )
            sys.exit(1)

        from tvt.collectors.slack import SlackCollector

        collector = SlackCollector(storage=storage, token=token)
    else:
        console.print(f"[red]Error: Unknown source '{source}'[/red]")
        sys.exit(1)

    if daemon:
        # Clean up stale PID file from previous crash
        cleanup_stale_pid_file()

        # Check if daemon is already running
        existing_pid = get_daemon_pid()
        if existing_pid:
            console.print(
                f"[yellow]Daemon already running with PID {existing_pid}.[/yellow]"
            )
            sys.exit(1)

        # Write PID file for this process
        try:
            write_pid_file(os.getpid())
        except OSError as e:
            console.print(f"[red]Error: Could not write PID file: {e}[/red]")
            sys.exit(1)

        try:
            console.print(
                f"[bold]Starting continuous collection from {source}[/bold]\n"
                f"Interval: {interval} seconds\n"
                "Press Ctrl+C to stop.\n"
            )
            collector.start(interval_seconds=interval)
            console.print("\n[yellow]Collection stopped.[/yellow]")
        finally:
            # Clean up PID file on exit
            clear_pid_file()
    else:
        console.print(f"[bold]Collecting from {source}...[/bold]")
        data = collector.run_once()
        if data:
            console.print(f"Current state: [cyan]{data.get('state', 'unknown')}[/cyan]")
            if data.get("in_huddle"):
                console.print("[blue]Currently in a huddle[/blue]")
        else:
            console.print("[yellow]No data collected.[/yellow]")


@main.command()
@click.option("--date", "-d", help="Date to summarize (YYYY-MM-DD). Default: today")
@click.option("--weekly", "-w", is_flag=True, help="Show weekly summary instead")
def summary(date: str | None, weekly: bool):
    """Display time visibility summary.

    Shows a breakdown of time spent in different states (active, away, DND,
    in huddles) for the specified day or week.
    """
    storage = SQLiteStorage(get_db_path())

    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            console.print("[red]Error: Invalid date format. Use YYYY-MM-DD.[/red]")
            sys.exit(1)
    else:
        target_date = datetime.now()

    if weekly:
        generate_weekly_summary(storage, target_date, console)
    else:
        generate_daily_summary(storage, target_date, console)


@main.command()
@click.option(
    "--start",
    "-s",
    required=True,
    help="Start date (YYYY-MM-DD)",
)
@click.option(
    "--end",
    "-e",
    help="End date (YYYY-MM-DD). Default: today",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path. Default: stdout",
)
def export(start: str, end: str | None, output: str | None):
    """Export time data to CSV format.

    Exports daily summaries for the specified date range.
    """
    storage = SQLiteStorage(get_db_path())

    try:
        start_date = datetime.strptime(start, "%Y-%m-%d")
    except ValueError:
        console.print("[red]Error: Invalid start date format. Use YYYY-MM-DD.[/red]")
        sys.exit(1)

    if end:
        try:
            end_date = datetime.strptime(end, "%Y-%m-%d")
        except ValueError:
            console.print("[red]Error: Invalid end date format. Use YYYY-MM-DD.[/red]")
            sys.exit(1)
    else:
        end_date = datetime.now()

    # Validate that end_date is not before start_date
    if end_date < start_date:
        console.print(
            "[red]Error: End date cannot be before start date.[/red]"
        )
        sys.exit(1)

    if output:
        with open(output, "w", newline="") as f:
            export_summary_csv(storage, start_date, end_date, f)
        console.print(f"[green]Data exported to {output}[/green]")
    else:
        export_summary_csv(storage, start_date, end_date, sys.stdout)


@main.command()
def status():
    """Show current TVT status and configuration."""
    config = load_config()
    db_path = get_db_path()

    console.print("[bold]Time Visibility Tracker Status[/bold]\n")

    # Database info
    console.print(f"[cyan]Database:[/cyan] {db_path}")
    if db_path.exists():
        size_kb = db_path.stat().st_size / 1024
        console.print(f"  Size: {size_kb:.1f} KB")

        storage = SQLiteStorage(db_path)
        today_summary = storage.get_daily_summary(datetime.now())
        console.print(
            f"  Today's tracked time: {today_summary['total_tracked_minutes']} minutes"
        )
    else:
        console.print("  [yellow]Database not yet created[/yellow]")

    # Configuration
    console.print(f"\n[cyan]Configuration:[/cyan] {get_config_path()}")

    # Collectors status
    console.print("\n[cyan]Collectors:[/cyan]")
    collectors = config.get("collectors", {})

    for name, settings in collectors.items():
        enabled = settings.get("enabled", False)
        status_str = "[green]enabled[/green]" if enabled else "[dim]disabled[/dim]"
        console.print(f"  {name}: {status_str}")

    # Check credentials
    if get_slack_token():
        console.print("\n[green]Slack credentials configured[/green]")
    else:
        console.print("\n[yellow]Slack credentials not configured[/yellow]")


@main.group()
def autostart():
    """Manage autostart configuration for TVT daemon."""
    pass


@autostart.command()
@click.option("--start-now", is_flag=True, help="Start daemon immediately after enabling")
def enable(start_now: bool):
    """Enable autostart via Windows Task Scheduler.

    Creates a task that runs at user login. Optionally starts the daemon now.
    """
    if platform.system() != "Windows":
        console.print("[red]Error: Autostart is only supported on Windows.[/red]")
        sys.exit(1)

    config = load_config()

    # Create the Task Scheduler task
    if not create_scheduled_task():
        console.print("[red]Error: Failed to create Task Scheduler task.[/red]")
        sys.exit(1)

    # Update config
    config["autostart"]["enabled"] = True
    config["autostart"]["last_enabled_at"] = datetime.now().isoformat()
    save_config(config)

    console.print("[green]Autostart enabled![/green]")
    console.print(
        "TVT daemon will start automatically at next login.\n"
    )

    # Start daemon now if requested
    if start_now:
        # Check if daemon is already running
        existing_pid = get_daemon_pid()
        if existing_pid:
            console.print(f"[yellow]Daemon already running with PID {existing_pid}.[/yellow]")
            return

        console.print("Starting daemon now...")
        try:
            # Start daemon in a detached process (no window)
            subprocess.Popen(
                [sys.executable, "-m", "tvt", "collect", "--daemon"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            console.print("[green]Daemon started.[/green]")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not start daemon: {e}[/yellow]")


@autostart.command()
@click.option("--stop-daemon", is_flag=True, help="Stop the daemon when disabling")
def disable(stop_daemon: bool):
    """Disable autostart and remove the Task Scheduler task.

    Optionally stops the daemon if it's running.
    """
    if platform.system() != "Windows":
        console.print("[red]Error: Autostart is only supported on Windows.[/red]")
        sys.exit(1)

    config = load_config()

    # Delete the Task Scheduler task
    if not delete_scheduled_task():
        console.print("[red]Error: Failed to delete Task Scheduler task.[/red]")
        sys.exit(1)

    # Update config
    config["autostart"]["enabled"] = False
    config["autostart"]["last_disabled_at"] = datetime.now().isoformat()
    save_config(config)

    console.print("[green]Autostart disabled.[/green]")

    # Stop daemon if requested
    if stop_daemon:
        daemon_pid = get_daemon_pid()
        if daemon_pid:
            try:
                os.kill(daemon_pid, 15)  # SIGTERM
                console.print("[green]Daemon stopped.[/green]")
            except (OSError, ProcessLookupError):
                console.print(
                    "[yellow]Warning: Could not stop daemon (may already be stopped).[/yellow]"
                )
                clear_pid_file()
        else:
            console.print("[dim]Daemon not running.[/dim]")


@autostart.command()
def status():
    """Show autostart and daemon status."""
    if platform.system() != "Windows":
        console.print("[red]Error: Autostart is only supported on Windows.[/red]")
        sys.exit(1)

    config = load_config()
    autostart_config = config.get("autostart", {})

    console.print("[bold]Autostart Status[/bold]\n")

    # Config state
    enabled = autostart_config.get("enabled", False)
    enabled_str = "[green]enabled[/green]" if enabled else "[dim]disabled[/dim]"
    console.print(f"Config state: {enabled_str}")

    last_enabled = autostart_config.get("last_enabled_at")
    if last_enabled:
        console.print(f"  Last enabled: {last_enabled}")

    last_disabled = autostart_config.get("last_disabled_at")
    if last_disabled:
        console.print(f"  Last disabled: {last_disabled}")

    # Task Scheduler state
    console.print()
    task_exists = is_task_scheduled()
    task_str = "[green]exists[/green]" if task_exists else "[dim]not scheduled[/dim]"
    console.print(f"Task Scheduler: {task_str}")

    # Daemon state
    console.print()
    daemon_pid = get_daemon_pid()
    if daemon_pid:
        console.print(f"[green]Daemon running[/green] (PID: {daemon_pid})")
    else:
        console.print("[dim]Daemon not running[/dim]")

    # Summary
    console.print()
    if enabled and task_exists and daemon_pid:
        console.print("[green]✓ Everything is configured and running[/green]")
    elif enabled and task_exists:
        console.print("[yellow]✓ Autostart configured (daemon will start at login)[/yellow]")
    elif enabled and not task_exists:
        console.print(
            "[yellow]⚠ Config says enabled but task not found[/yellow]\n"
            "Run [bold]tvt autostart enable[/bold] to recreate the task."
        )
    else:
        console.print("[dim]- Autostart is not configured[/dim]")


@main.command()
def dashboard():
    """Open the web dashboard (coming in Phase 1)."""
    console.print(
        "[yellow]Web dashboard coming in Phase 1![/yellow]\n\n"
        "For now, use these commands:\n"
        "  [bold]tvt summary[/bold]      - View today's summary\n"
        "  [bold]tvt summary -w[/bold]   - View weekly summary\n"
        "  [bold]tvt export -s DATE[/bold] - Export to CSV\n"
    )


if __name__ == "__main__":
    main()
