"""CLI argument parsing and command dispatch."""

import argparse
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from . import __version__
from .config import MacSrvConfig
from .constants import (
    APP_DISPLAY_NAME,
    LOGFILE,
    CONFIG_FILE,
    EXIT_SUCCESS,
    EXIT_ERROR,
    STATE_DIR,
)
from .logger import setup_logging, get_logger
from .server import start, stop, restart, is_running
from .status import display_status
from .doctor import run as doctor_run
from .utils import parse_duration


def _make_parser() -> argparse.ArgumentParser:
    """Build the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="macsrv",
        description="Prevent macOS sleep until a target time.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  macsrv start              Start until 02:00 (config default)\n"
            "  macsrv start --until 04:00  Start until 04:00\n"
            "  macsrv start --for 8h       Start for 8 hours\n"
            "  macsrv stop               Stop the server\n"
            "  macsrv status             Show status\n"
            "  macsrv logs --tail 20     Show last 20 log lines\n"
        ),
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"{APP_DISPLAY_NAME} v{__version__}",
    )

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # ── start ──────────────────────────────────────────────────────────────
    p_start = sub.add_parser("start", help="Start the server")
    p_start.add_argument(
        "--until",
        type=str,
        metavar="HH:MM",
        help="Stop time in 24h format (overrides config)",
    )
    p_start.add_argument(
        "--for",
        type=str,
        dest="duration",
        metavar="DURATION",
        help="Duration (e.g. 8h, 30m, 2h30m)",
    )

    # ── stop ───────────────────────────────────────────────────────────────
    sub.add_parser("stop", help="Stop the server")

    # ── restart ────────────────────────────────────────────────────────────
    p_restart = sub.add_parser("restart", help="Restart the server")
    p_restart.add_argument(
        "--until",
        type=str,
        metavar="HH:MM",
        help="Stop time in 24h format (overrides config)",
    )
    p_restart.add_argument(
        "--for",
        type=str,
        dest="duration",
        metavar="DURATION",
        help="Duration (e.g. 8h, 30m, 2h30m)",
    )

    # ── status ─────────────────────────────────────────────────────────────
    sub.add_parser("status", help="Show server status")

    # ── doctor ─────────────────────────────────────────────────────────────
    sub.add_parser("doctor", help="Run system diagnostics")

    # ── logs ───────────────────────────────────────────────────────────────
    p_logs = sub.add_parser("logs", help="Show server logs")
    p_logs.add_argument(
        "--tail",
        type=int,
        metavar="N",
        help="Show only the last N lines",
    )

    # ── config ─────────────────────────────────────────────────────────────
    p_config = sub.add_parser("config", help="View or modify configuration")
    p_config.add_argument(
        "action",
        nargs="?",
        choices=["set"],
        help="'set' to modify a config value",
    )
    p_config.add_argument(
        "key",
        nargs="?",
        help="Config key to set",
    )
    p_config.add_argument(
        "value",
        nargs="?",
        help="Value to set",
    )

    # ── help ───────────────────────────────────────────────────────────────
    sub.add_parser("help", help="Show this help message")

    # ── version ────────────────────────────────────────────────────────────
    sub.add_parser("version", help="Show version information")

    # ── completion ─────────────────────────────────────────────────────────
    p_completion = sub.add_parser(
        "completion",
        help="Generate shell completion script",
    )
    p_completion.add_argument(
        "shell",
        nargs="?",
        choices=["bash", "zsh"],
        default="zsh",
        help="Target shell (default: zsh)",
    )

    return parser


def _cmd_completion(args: argparse.Namespace) -> int:
    """Print shell completion script."""
    shell = args.shell
    script = _completion_script(shell)
    print(script)
    return EXIT_SUCCESS


def _completion_script(shell: str) -> str:
    """Generate shell completion script."""
    if shell == "bash":
        return """_macsrv_complete() {
    local cur prev words cword
    _init_completion || return
    COMPREPLY=( $(compgen -W "start stop restart status doctor logs config help version completion" -- "$cur") )
}
complete -F _macsrv_complete macsrv
"""
    # zsh
    return """#compdef macsrv
_macsrv() {
    local -a commands
    commands=(
        'start:Start the server'
        'stop:Stop the server'
        'restart:Restart the server'
        'status:Show server status'
        'doctor:Run system diagnostics'
        'logs:Show server logs'
        'config:View or modify configuration'
        'help:Show help'
        'version:Show version'
        'completion:Generate completion script'
    )
    _describe 'command' commands
}
_macsrv "$@"
"""


def _cmd_config(args: argparse.Namespace) -> int:
    """Handle config subcommand."""
    cfg = MacSrvConfig.load()

    if args.action == "set":
        if not args.key or not args.value:
            print("Usage: macsrv config set <key> <value>")
            print()
            print("Keys: auto_stop_time, display_sleep, logging")
            return EXIT_ERROR
        success, err = cfg.set(args.key, args.value)
        if success:
            print(f"✅  {args.key} set to {args.value}")
            return EXIT_SUCCESS
        print(f"❌  {err}")
        return EXIT_ERROR

    # Display config
    vals = cfg.display()
    print()
    print("  macsrv Configuration")
    print("  ────────────────────────")
    print(f"  Config file: {CONFIG_FILE}")
    print()
    print(f"  Auto Stop Time : {vals['auto_stop_time']}")
    print(f"  Display Sleep  : {vals['display_sleep']} min")
    print(f"  Logging        : {vals['logging']}")
    print()
    print("  To change:")
    print("    macsrv config set auto-stop 03:00")
    print("    macsrv config set logging false")
    print()
    return EXIT_SUCCESS


def _cmd_logs(args: argparse.Namespace) -> int:
    """Display log file contents."""
    logfile = LOGFILE
    if not logfile.exists():
        print("📝  No log file found. Start the server to create logs.")
        return EXIT_SUCCESS

    lines = logfile.read_text().splitlines()
    if args.tail:
        lines = lines[-args.tail:]

    print()
    print("  macsrv Logs")
    print("  ────────────────────────")
    if not lines:
        print("  (empty)")
    for line in lines:
        print(f"  {line}")
    print()
    return EXIT_SUCCESS


def _cmd_help() -> int:
    """Print beautiful help page."""
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║         Mac Server CLI  v1.0.0          ║")
    print("  ╚══════════════════════════════════════════╝")
    print()
    print("  Usage:  macsrv <command> [options]")
    print()
    print("  Commands:")
    print()
    print("    start     Start the server")
    print("              --until HH:MM    Stop at given time")
    print("              --for DURATION   Run for duration (8h, 30m)")
    print()
    print("    stop      Stop the server")
    print("    restart   Restart the server")
    print("    status    Show server status")
    print("    doctor    Run system diagnostics")
    print("    logs      Show server logs")
    print("              --tail N   Show last N lines")
    print()
    print("    config    View or modify configuration")
    print("              config set <key> <value>")
    print()
    print("    version   Show version")
    print("    help      Show this help")
    print("    completion [bash|zsh]  Generate shell completion")
    print()
    print("  Examples:")
    print()
    print("    macsrv start              Start until 02:00")
    print("    macsrv start --until 04:00  Start until 04:00")
    print("    macsrv start --for 8h       Start for 8 hours")
    print("    macsrv stop               Stop server")
    print("    macsrv status             Check status")
    print("    macsrv logs --tail 20     Last 20 log lines")
    print()
    return EXIT_SUCCESS


def _cmd_version() -> int:
    """Print version banner."""
    print(f"{APP_DISPLAY_NAME}")
    print(f"Version {__version__}")
    return EXIT_SUCCESS


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main entry point: parse args and dispatch to the right handler.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code.
    """
    parser = _make_parser()
    args = parser.parse_args(argv)

    # Load config for logging setup
    cfg = MacSrvConfig.load()
    setup_logging(logging_enabled=cfg.logging)

    # No command or help
    if args.command is None:
        return _cmd_help()

    # Dispatch
    dispatch = {
        "start": lambda: start(cfg, until=args.until, duration=args.duration) if hasattr(args, 'until') else start(cfg),
        "stop": stop,
        "restart": lambda: restart(cfg),
        "status": display_status,
        "doctor": doctor_run,
        "logs": lambda: _cmd_logs(args),
        "config": lambda: _cmd_config(args),
        "help": _cmd_help,
        "version": _cmd_version,
        "completion": lambda: _cmd_completion(args),
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return EXIT_ERROR

    try:
        return handler()
    except Exception as e:
        logger = get_logger()
        logger.exception("Command failed: %s", args.command)
        print(f"❌  Error: {e}")
        return EXIT_ERROR