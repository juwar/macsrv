# macsrv

**macsrv** — Prevent your Mac from sleeping until a target time.

Uses `caffeinate` under the hood. No external dependencies.

## Install

```bash
pip install -e .
```

Or install from the project root:

```bash
cd macsrv
pip install -e .
```

## Usage

```bash
macsrv start              # Start until 02:00 (configurable)
macsrv start --until 04:00  # Start until 04:00
macsrv start --for 8h       # Start for 8 hours
macsrv stop               # Stop the server
macsrv restart            # Restart
macsrv status             # Show status
macsrv doctor             # Run diagnostics
macsrv logs               # Show logs
macsrv logs --tail 20     # Last 20 lines
macsrv config             # Show config
macsrv config set auto-stop 03:00  # Change stop time
macsrv config set logging false     # Disable logging
macsrv version            # Show version
```

## Configuration

Config file: `~/.config/macsrv/config.ini`

| Key | Default | Description |
|-----|---------|-------------|
| `auto_stop_time` | `02:00` | Time to stop in HH:MM |
| `display_sleep` | `10` | Display sleep timeout (minutes) |
| `logging` | `true` | Enable file logging |

## State

Stored in `~/.local/state/macsrv/`:

- `pid` — Process ID of the running caffeinate
- `started_at` — Unix timestamp when started
- `expires_at` — Unix timestamp when it expires
- `logfile` — Application log

## Diagnostics

```bash
macsrv doctor
```

Checks:

- caffeinate exists
- SSH enabled (`systemsetup -getremotelogin`)
- Tailscale installed and connected
- Config file exists
- State directory exists
- Current caffeinate process

## System Requirements

- macOS Sonoma or later
- Python 3.12+
- No external dependencies