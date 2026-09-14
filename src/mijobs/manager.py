"""Containerized, project-scoped operations console."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, quote_plus

from dotenv import dotenv_values
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

ACTIONS = {
    '1': ('start', 'Start / apply configuration'),
    '2': ('stop', 'Stop service'),
    '3': ('restart', 'Restart service'),
    '4': ('logs', 'Recent service logs'),
    '5': ('init-db', 'Initialize database'),
    '6': ('audit-ledger', 'Audit evidence and hash chain'),
    '7': ('sources', 'Browse official source registry'),
    '8': ('ci', 'Run strict quality checks'),
    '9': ('config', 'Configuration overview'),
    'r': ('status', 'Refresh status'),
    'e': ('exchange-start', 'Start / apply confidential exchange'),
    'x': ('exchange-stop', 'Stop confidential exchange'),
    's': ('exchange-status', 'Confidential exchange status'),
}
CREDENTIALS = ('BLS_API_KEY', 'CENSUS_API_KEY', 'ONET_USERNAME', 'ONET_PASSWORD', 'EXCHANGE_OPERATOR_TOKEN', 'EXCHANGE_ENCRYPTION_KEY')


@dataclass(frozen=True)
class Result:
    code: int
    output: str


class Manager:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        self.env_path = self.workspace / '.env'

    def redact(self, text: str) -> str:
        values = dotenv_values(self.env_path, interpolate=False) if self.env_path.is_file() else {}
        for key in (*CREDENTIALS, 'MIJOBS_DATABASE_URL'):
            for value in (values.get(key), os.getenv(key)):
                if value:
                    variants = {value, quote(value, safe=''), quote_plus(value), json.dumps(value)[1:-1]}
                    for variant in sorted(variants, key=len, reverse=True):
                        text = text.replace(variant, '[redacted]')
        # Also hide userinfo if a driver prints a URL from an unexpected source.
        text = re.sub(r'(\w+://)[^\s/@]+:[^\s/@]+@', r'\1[redacted]@', text)
        # Do not replay terminal control sequences from subprocess logs.
        return re.sub(r'\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))', '', text)

    def _run(self, args: list[str], timeout: int = 120) -> Result:
        command = ['docker', 'compose', '--project-directory', str(self.workspace),
                   '-f', str(self.workspace / 'compose.yaml'), '--env-file', str(self.env_path), *args]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
            output = '\n'.join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
            return Result(result.returncode, self.redact(output))
        except FileNotFoundError:
            return Result(127, 'Docker CLI unavailable. Launch this manager with docker compose run --rm tui.')
        except subprocess.TimeoutExpired:
            return Result(124, 'Operation timed out. Check Status and Logs; Docker may still be finishing the action.')
        except KeyboardInterrupt:
            return Result(130, 'Interrupted. Check Status before retrying.')
        except OSError:
            return Result(1, 'Could not run Docker. Check Docker Desktop and the manager socket mount.')

    def execute(self, action: str) -> Result:
        if not self.env_path.is_file():
            return Result(2, 'Missing .env. Copy .env.example to .env in the project folder, then reopen the manager.')
        if action == 'config':
            values = dotenv_values(self.env_path, interpolate=False)
            lines = ['Runtime settings: edit .env, reopen the manager, then choose Start / apply configuration.',
                     'Persistence: project data volume; stopping or quitting does not remove evidence.']
            for key in CREDENTIALS:
                lines.append(f'{key}: {"configured" if values.get(key) or os.getenv(key) else "not set"}')
            lines.append('Database URL and credential values are hidden.')
            return Result(0, '\n'.join(lines))
        routes = {
            'exchange-start': ['up', '-d', '--build', '--wait', '--wait-timeout', '60', 'exchange'],
            'exchange-stop': ['stop', 'exchange'],
            'exchange-status': ['ps', '--all', '--format', 'json', 'exchange'],
            'status': ['ps', '--all', '--format', 'json', 'app'],
            'start': ['up', '-d', '--build', '--wait', '--wait-timeout', '60', 'app'],
            'stop': ['stop', 'app'],
            'logs': ['logs', '--no-color', '--tail', '100', 'app'],
            'ci': ['run', '--build', '--rm', '--no-deps', '-T', 'ci'],
        }
        if action == 'restart':
            started = self.execute('start')
            if started.code:
                return started
            return self._run(['restart', '--no-deps', 'app'])
        if action in ('init-db', 'audit-ledger', 'sources'):
            return self._run(['run', '--build', '--rm', '--no-deps', '-T', 'cli', action])
        if action not in routes:
            return Result(2, f'Unknown action: {action}')
        return self._run(routes[action], timeout=900 if action in ('ci', 'start', 'exchange-start') else 120)


def render_status(console: Console, result: Result) -> None:
    if result.code:
        console.print(Panel(Text(result.output), title='Docker unavailable', border_style='red'))
        return
    table = Table(expand=True, border_style='cyan', title='SERVICE STATUS')
    for label in ('Service', 'State', 'Health'):
        table.add_column(label)
    try:
        raw = result.output.strip()
        rows = json.loads(raw) if raw.startswith('[') else [json.loads(line) for line in raw.splitlines() if line]
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError('unexpected status')
        for row in rows:
            table.add_row(Text(str(row.get('Service', 'app'))), Text(str(row.get('State', 'unknown'))),
                          Text(str(row.get('Health') or '—')))
        if not rows:
            table.add_row('app', 'not created', 'Choose Start')
        console.print(table)
    except (ValueError, TypeError):
        console.print(Panel(Text(result.output), title='Docker status', border_style='yellow'))


def menu(manager: Manager, console: Console) -> None:
    while True:
        console.print(Panel('[bold white]MICHIGAN[/bold white]  [cyan]WORKFORCE INTELLIGENCE[/cyan]\n'
                            '[dim]Local operations · Evidence first · Docker workspace[/dim]', border_style='cyan'))
        render_status(console, manager.execute('status'))
        options = Table.grid(padding=(0, 3))
        options.add_column(style='bold cyan')
        options.add_column()
        for key, (_, label) in ACTIONS.items():
            options.add_row(key, label)
        options.add_row('q', 'Quit manager (service keeps running)')
        console.print(Panel(options, title='OPERATIONS', border_style='blue'))
        try:
            choice = Prompt.ask('Action', choices=[*ACTIONS, 'q'], default='r', console=console)
            if choice == 'q':
                return
            action, label = ACTIONS[choice]
            with console.status(f'{label}…', spinner='dots'):
                result = manager.execute(action)
            console.print(Panel(Text(result.output or 'Completed.'), title=f'{label} · exit {result.code}',
                                border_style='green' if result.code == 0 else 'red'))
        except (EOFError, KeyboardInterrupt):
            console.print('\nManager closed; service state unchanged.')
            return


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Michigan workforce Docker operations')
    parser.add_argument('action', nargs='?', choices=[item[0] for item in ACTIONS.values()])
    args = parser.parse_args(argv)
    manager = Manager(Path(os.getenv('MIJOBS_WORKSPACE', '/workspace')))
    console = Console()
    if args.action:
        result = manager.execute(args.action)
        if args.action == 'status':
            render_status(console, result)
        else:
            console.print(Text(result.output))
        return result.code
    menu(manager, console)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
