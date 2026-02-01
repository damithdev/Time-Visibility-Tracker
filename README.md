# Time Visibility Tracker (TVT)

An open-source tool that makes invisible work time visible—helping developers, engineering managers, and IT workers understand where their time actually goes beyond calendar events.

## The Problem

Calendar apps only show scheduled meetings. The real time drain—Slack huddles, Teams calls, ad-hoc DMs, context-switching—remains invisible and untrackable.

## Features

- **Automatic Tracking**: Detects Slack presence, huddles, and DND status
- **Privacy-First**: All data stays local in SQLite
- **Simple CLI**: Easy-to-use command line interface
- **Daily/Weekly Summaries**: Understand your time patterns
- **CSV Export**: Get your data out for further analysis

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/damithdev/Time-Visibility-Tracker-.git
cd Time-Visibility-Tracker-

# Install with pip (in a virtual environment recommended)
pip install -e .
```

### Setup

```bash
# Interactive configuration
tvt init
```

This will guide you through:
1. Setting up Slack integration (optional)
2. Configuring database location

### Usage

```bash
# Run a single collection
tvt collect

# Run continuously (daemon mode)
tvt collect --daemon

# View today's summary
tvt summary

# View weekly summary
tvt summary --weekly

# Export data to CSV
tvt export --start 2025-01-01 --output report.csv

# Check status
tvt status
```

## Slack Integration Setup

To track Slack presence and huddles, you need to create a Slack app:

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Add these **User Token Scopes** under OAuth & Permissions:
   - `users:read`
   - `users:read.presence` (for presence tracking)
   - `dnd:read` (for DND status)
4. Install the app to your workspace
5. Copy the **User OAuth Token** (starts with `xoxp-`)
6. Run `tvt init` and paste the token when prompted

Alternatively, set the `SLACK_USER_TOKEN` environment variable:

```bash
export SLACK_USER_TOKEN=xoxp-your-token-here
```

## Configuration

Configuration is stored in `~/.tvt/config.yaml`:

```yaml
database:
  path: ~/.tvt/data.db

collectors:
  slack:
    enabled: true
    interval_seconds: 30
  teams:
    enabled: false
    interval_seconds: 30
```

Credentials are stored separately in `~/.tvt/credentials.yaml` with restricted permissions.

## Data Storage

TVT uses SQLite for local data storage. The database contains:

- **events**: Tracked time events (huddles, calls, focus time)
- **presence_states**: Raw presence data snapshots

Database location: `~/.tvt/data.db` (configurable)

## Commands Reference

| Command | Description |
|---------|-------------|
| `tvt init` | Interactive setup wizard |
| `tvt collect` | Run single collection cycle |
| `tvt collect --daemon` | Run continuously |
| `tvt summary` | Show today's time breakdown |
| `tvt summary --weekly` | Show weekly overview |
| `tvt summary --date 2025-01-15` | Show specific day |
| `tvt export --start DATE` | Export data to CSV |
| `tvt status` | Show current status |
| `tvt dashboard` | Open web dashboard (Phase 1) |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black tvt/
ruff check tvt/
```

## Project Structure

```
time-visibility-tracker/
├── tvt/
│   ├── __init__.py
│   ├── cli.py              # Command line interface
│   ├── config.py           # Configuration management
│   ├── summary.py          # Summary generation
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── base.py         # Base collector class
│   │   └── slack.py        # Slack integration
│   └── storage/
│       ├── __init__.py
│       ├── models.py       # Data models
│       └── sqlite.py       # SQLite backend
├── tests/
├── pyproject.toml
├── LICENSE
└── README.md
```

## Roadmap

- **Phase 0** (Current): Slack presence tracking, daily summaries
- **Phase 1**: Microsoft Teams integration, web dashboard
- **Phase 2**: Insights engine, pattern detection
- **Phase 3**: Team features (opt-in, privacy-focused)
- **Phase 4**: Full open-source release with docs

## Privacy

- All data is stored locally on your machine
- No data is sent to external servers
- Credentials are stored with restricted file permissions
- You own your data—export it anytime

## License

MIT License - see [LICENSE](LICENSE) file.

## Contributing

Contributions welcome! Please read our contributing guidelines (coming in Phase 4).

## Support

- Issues: [GitHub Issues](https://github.com/damithdev/Time-Visibility-Tracker-/issues)
