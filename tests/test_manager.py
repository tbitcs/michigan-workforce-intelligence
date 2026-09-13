from __future__ import annotations

import io
import subprocess

import pytest
from rich.console import Console

from mijobs.manager import Manager, Result, main, menu, render_status


def manager(tmp_path, monkeypatch):
    (tmp_path / '.env').write_text("COMPOSE_PROJECT_NAME=test-mwi\nBLS_API_KEY='abc$secret'\n")
    return Manager(tmp_path)


def test_routes_are_project_scoped(tmp_path, monkeypatch):
    controller = manager(tmp_path, monkeypatch)
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        assert kwargs.get('shell', False) is False
        return subprocess.CompletedProcess(args, 0, 'ok', '')
    monkeypatch.setattr(subprocess, 'run', run)
    for action in ('start', 'stop', 'restart', 'logs', 'init-db', 'audit-ledger', 'sources', 'ci', 'status'):
        assert controller.execute(action).code == 0
    assert all(args[:2] == ['docker', 'compose'] for args in calls)
    assert all(str(tmp_path / 'compose.yaml') in args for args in calls)
    flat = ' '.join(' '.join(args) for args in calls)
    assert '--wait' in flat and '--build' in flat
    assert '--tail' in flat and '100' in flat
    assert 'prune' not in flat and 'down' not in flat
    assert any('ci' in args and 'run' in args for args in calls)


def test_failures_and_secrets(tmp_path, monkeypatch):
    controller = manager(tmp_path, monkeypatch)
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: subprocess.CompletedProcess(a, 7, 'abc$secret', 'failed abc$secret'))
    result = controller.execute('logs')
    assert result.code == 7 and 'abc$secret' not in result.output
    assert '[redacted]' in result.output
    assert 'abc$secret' not in controller.execute('config').output


@pytest.mark.parametrize('error', [FileNotFoundError(), subprocess.TimeoutExpired('docker', 1), KeyboardInterrupt()])
def test_execution_errors(tmp_path, monkeypatch, error):
    controller = manager(tmp_path, monkeypatch)
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(subprocess, 'run', fail)
    assert controller.execute('start').code != 0


def test_missing_env_and_unknown_action(tmp_path):
    controller = Manager(tmp_path)
    assert controller.execute('start').code != 0
    assert 'copy' in controller.execute('start').output.lower()
    assert controller.execute('delete-evidence').code != 0


def test_status_rendering():
    output = io.StringIO()
    console = Console(file=output, width=90, color_system=None)
    render_status(console, Result(0, '[{"Service":"app","State":"running","Health":"healthy"}]'))
    assert 'healthy' in output.getvalue()
    render_status(console, Result(0, ''))
    render_status(console, Result(0, 'not json'))
    render_status(console, Result(1, 'daemon unavailable'))
    assert 'daemon unavailable' in output.getvalue()


def test_menu_action_and_quit(tmp_path, monkeypatch):
    controller = manager(tmp_path, monkeypatch)
    output = io.StringIO()
    calls = []
    monkeypatch.setattr(controller, 'execute', lambda action: calls.append(action) or Result(0, '[]'))
    choices = iter(['1', 'q'])
    monkeypatch.setattr('mijobs.manager.Prompt.ask', lambda *a, **k: next(choices))
    menu(controller, Console(file=output, width=90))
    assert 'start' in calls
    assert 'MICHIGAN' in output.getvalue()


def test_menu_eof(tmp_path, monkeypatch):
    controller = manager(tmp_path, monkeypatch)
    monkeypatch.setattr(controller, 'execute', lambda _: Result(0, '[]'))
    def eof(*args, **kwargs):
        raise EOFError
    monkeypatch.setattr('mijobs.manager.Prompt.ask', eof)
    menu(controller, Console(file=io.StringIO()))


def test_main_noninteractive(tmp_path, monkeypatch):
    monkeypatch.setenv('MIJOBS_WORKSPACE', str(tmp_path))
    monkeypatch.setattr(Manager, 'execute', lambda self, action: Result(8, 'failed'))
    assert main(['status']) == 8
