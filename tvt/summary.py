"""Summary generation for Time Visibility Tracker."""

from datetime import datetime, timedelta
from typing import TextIO

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from tvt.storage.sqlite import SQLiteStorage


def format_duration(minutes: int) -> str:
    """Format minutes as human-readable duration.

    Args:
        minutes: Duration in minutes.

    Returns:
        Formatted string like "2h 30m" or "45m".
    """
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    remaining_minutes = minutes % 60
    if remaining_minutes == 0:
        return f"{hours}h"
    return f"{hours}h {remaining_minutes}m"


def get_state_emoji(state: str) -> str:
    """Get emoji for a presence state.

    Args:
        state: Presence state name.

    Returns:
        Emoji character for the state.
    """
    emojis = {
        "active": "[green]●[/green]",
        "away": "[yellow]○[/yellow]",
        "dnd": "[red]⊘[/red]",
        "huddle": "[blue]♪[/blue]",
    }
    return emojis.get(state.lower(), "•")


def generate_daily_summary(
    storage: SQLiteStorage,
    date: datetime | None = None,
    console: Console | None = None,
) -> dict:
    """Generate and display a daily summary.

    Args:
        storage: SQLiteStorage instance.
        date: Date to summarize. Defaults to today.
        console: Rich console for output. Creates new one if not provided.

    Returns:
        Summary data dictionary.
    """
    if date is None:
        date = datetime.now()
    if console is None:
        console = Console()

    summary = storage.get_daily_summary(date)

    # Create header
    date_str = date.strftime("%A, %B %d, %Y")
    console.print(Panel(f"[bold]Time Visibility Summary[/bold]\n{date_str}"))

    # Presence time breakdown
    if summary["presence"]:
        presence_table = Table(title="Time by State", show_header=True)
        presence_table.add_column("State", style="cyan")
        presence_table.add_column("Duration", justify="right")
        presence_table.add_column("Percentage", justify="right")

        total = summary["total_tracked_minutes"]
        for state, minutes in sorted(
            summary["presence"].items(), key=lambda x: x[1], reverse=True
        ):
            emoji = get_state_emoji(state)
            pct = (minutes / total * 100) if total > 0 else 0
            bar_width = int(pct / 5)  # Scale to max 20 chars
            bar = "█" * bar_width + "░" * (20 - bar_width)
            presence_table.add_row(
                f"{emoji} {state.title()}",
                format_duration(minutes),
                f"{pct:.1f}% {bar}",
            )

        console.print(presence_table)
        console.print(f"\n[dim]Total tracked time: {format_duration(total)}[/dim]\n")
    else:
        console.print("[yellow]No presence data recorded for this day.[/yellow]\n")

    # Events breakdown (if any completed events)
    if summary["events"]:
        events_table = Table(title="Completed Events", show_header=True)
        events_table.add_column("Type", style="magenta")
        events_table.add_column("Source", style="blue")
        events_table.add_column("Total Time", justify="right")

        for event in summary["events"]:
            if event["total_minutes"]:
                events_table.add_row(
                    event["event_type"].title(),
                    event["source"].title(),
                    format_duration(event["total_minutes"]),
                )

        console.print(events_table)

    return summary


def generate_weekly_summary(
    storage: SQLiteStorage,
    end_date: datetime | None = None,
    console: Console | None = None,
) -> list[dict]:
    """Generate and display a weekly summary.

    Args:
        storage: SQLiteStorage instance.
        end_date: Last day of the week. Defaults to today.
        console: Rich console for output.

    Returns:
        List of daily summary dictionaries.
    """
    if end_date is None:
        end_date = datetime.now()
    if console is None:
        console = Console()

    # Get summaries for last 7 days
    summaries = []
    for i in range(6, -1, -1):
        day = end_date - timedelta(days=i)
        summaries.append(storage.get_daily_summary(day))

    console.print(Panel("[bold]Weekly Overview[/bold]"))

    # Create weekly table
    table = Table(show_header=True)
    table.add_column("Day", style="cyan")
    table.add_column("Active", justify="right")
    table.add_column("Away", justify="right")
    table.add_column("DND", justify="right")
    table.add_column("Huddles", justify="right")
    table.add_column("Total", justify="right")

    week_totals = {"active": 0, "away": 0, "dnd": 0, "huddle": 0, "total": 0}

    for summary in summaries:
        date = datetime.fromisoformat(summary["date"])
        day_name = date.strftime("%a %m/%d")

        presence = summary["presence"]
        active = presence.get("active", 0)
        away = presence.get("away", 0)
        dnd = presence.get("dnd", 0)
        huddle = presence.get("huddle", 0)
        total = summary["total_tracked_minutes"]

        week_totals["active"] += active
        week_totals["away"] += away
        week_totals["dnd"] += dnd
        week_totals["huddle"] += huddle
        week_totals["total"] += total

        table.add_row(
            day_name,
            format_duration(active) if active else "-",
            format_duration(away) if away else "-",
            format_duration(dnd) if dnd else "-",
            format_duration(huddle) if huddle else "-",
            format_duration(total) if total else "-",
        )

    # Add totals row
    table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{format_duration(week_totals['active'])}[/bold]",
        f"[bold]{format_duration(week_totals['away'])}[/bold]",
        f"[bold]{format_duration(week_totals['dnd'])}[/bold]",
        f"[bold]{format_duration(week_totals['huddle'])}[/bold]",
        f"[bold]{format_duration(week_totals['total'])}[/bold]",
    )

    console.print(table)

    # Calculate and display insights
    if week_totals["total"] > 0:
        huddle_pct = week_totals["huddle"] / week_totals["total"] * 100
        active_pct = week_totals["active"] / week_totals["total"] * 100

        console.print("\n[bold]Weekly Insights:[/bold]")
        console.print(f"  • Huddle time: {huddle_pct:.1f}% of tracked time")
        console.print(f"  • Active time: {active_pct:.1f}% of tracked time")

        if huddle_pct > 30:
            console.print(
                "  [yellow]⚠ High huddle time this week. "
                "Consider if some could be async.[/yellow]"
            )

    return summaries


def export_summary_csv(
    storage: SQLiteStorage,
    start_date: datetime,
    end_date: datetime,
    output: TextIO,
) -> None:
    """Export summary data to CSV format.

    Args:
        storage: SQLiteStorage instance.
        start_date: Start of date range.
        end_date: End of date range.
        output: File-like object to write CSV to.
    """
    import csv

    writer = csv.writer(output)
    writer.writerow(["Date", "State", "Minutes", "Source"])

    current = start_date
    while current <= end_date:
        summary = storage.get_daily_summary(current)
        for state, minutes in summary["presence"].items():
            writer.writerow([summary["date"], state, minutes, "presence"])
        for event in summary["events"]:
            if event["total_minutes"]:
                writer.writerow([
                    summary["date"],
                    event["event_type"],
                    event["total_minutes"],
                    event["source"],
                ])
        current += timedelta(days=1)
