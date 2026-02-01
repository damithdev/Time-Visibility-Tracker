# Time Visibility Tracker

An open-source tool that makes invisible work time visible—helping developers, engineering managers, and IT workers understand where their time actually goes beyond calendar events.

## 🎯 Problem

Calendar apps only show scheduled meetings. The real time drain—Slack huddles, Teams calls, ad-hoc DMs, context-switching—remains invisible and untrackable. **Time Visibility Tracker** solves this by automatically monitoring and categorizing your actual computer activity.

## ✨ Features

- **Automatic Activity Tracking**: Monitors active applications every minute
- **Smart Categorization**: Automatically categorizes time into:
  - Communication (Slack, Teams, Discord, etc.)
  - Development (VS Code, IntelliJ, Terminal, etc.)
  - Email (Outlook, Gmail, etc.)
  - Browser (Chrome, Firefox, Safari, etc.)
  - Documentation (Word, Notion, Confluence, etc.)
  - Meetings (Zoom, Teams, Meet, etc.)
  - Other
- **Detailed Reports**: Generate reports for today, this week, this month, or all time
- **Data Export**: Export your time data as JSON or CSV for further analysis
- **Privacy-First**: All data stored locally on your machine
- **Cross-Platform**: Works on macOS, Linux, and Windows

## 📦 Installation

### Prerequisites

- Node.js 14.0.0 or higher

### Install from source

```bash
# Clone the repository
git clone https://github.com/damithdev/Time-Visibility-Tracker-.git
cd Time-Visibility-Tracker-

# Install globally
npm install -g .
```

## 🚀 Usage

### Start Tracking

Begin tracking your time:

```bash
tvt start
```

### Check Status

See if tracking is active and current session details:

```bash
tvt status
```

### Stop Tracking

Stop the current tracking session:

```bash
tvt stop
```

### Generate Reports

View reports for different time periods:

```bash
# Today's activity
tvt report today

# Past week
tvt report week

# This month
tvt report month

# All time
tvt report all
```

Example output:
```
📊 Time Visibility Report - WEEK
══════════════════════════════════════════════════
Total tracked time: 25h 30m
Sessions: 12

⏱️  Time by Category:
  Development          12h 15m    ████████████████████████ 48.0%
  Communication        6h 30m     ████████████ 25.5%
  Browser              4h 20m     ████████ 17.0%
  Documentation        2h 25m     ████ 9.5%

🔝 Top Applications:
   1. Visual Studio Code              8h 45m
   2. Slack                            5h 20m
   3. Chrome                           4h 20m
   4. Terminal                         3h 30m
   5. Microsoft Teams                  1h 10m
```

### Export Data

Export your tracked data for external analysis:

```bash
# Export as JSON
tvt export json

# Export as CSV
tvt export csv
```

### Clear Data

Remove all tracked data:

```bash
tvt clear
```

### Help

Display help information:

```bash
tvt help
```

## 📊 What Gets Tracked

The tracker monitors:
- **Active application names**: The application you're currently using
- **Timestamps**: When each activity occurs
- **Categories**: Automatically assigned based on the application

**What is NOT tracked:**
- Content of your work (no screenshots or keystroke logging)
- Websites you visit
- File names or code you write
- Any personal or sensitive data

## 🔒 Privacy & Data

- All data is stored locally in the `data/` directory
- No data is sent to external servers
- You have full control over your data
- You can export or delete your data at any time

## 🛠️ Development

### Run Tests

```bash
npm test
```

### Project Structure

```
Time-Visibility-Tracker-/
├── src/
│   ├── tracker.js    # Core tracking engine
│   ├── cli.js        # Command-line interface
│   └── index.js      # Main entry point
├── test/
│   └── tracker.test.js  # Test suite
├── data/             # Local data storage (created automatically)
├── package.json      # Project configuration
└── README.md         # This file
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details

## 🙏 Acknowledgments

Built to solve the real problem of invisible work time that impacts developers and IT professionals everywhere.

## 📞 Support

If you encounter any issues or have questions, please open an issue on GitHub.
