import pytest

from tutor import cli
from tutor.ui import ScriptedUI


def test_versao(capsys):
    assert cli.main(["--versao"]) == 0
    assert "tutor-front" in capsys.readouterr().out


def test_root_recusado(monkeypatch, capsys):
    monkeypatch.setattr(cli, "eh_root", lambda: True)
    assert cli.main(["--lista"]) == 2
    assert "root" in capsys.readouterr().out


def test_lista(monkeypatch):
    monkeypatch.setattr(cli, "eh_root", lambda: False)
    ui = ScriptedUI()
    assert cli.main(["--lista"], ui=ui) == 0
    assert "E00" in ui.tudo() and "E23" in ui.tudo()


def test_sair_na_primeira_etapa_salva_progresso(monkeypatch):
    monkeypatch.setattr(cli, "eh_root", lambda: False)
    ui = ScriptedUI(["S"])
    assert cli.main(["--dry-run"], ui=ui) == 0
    assert "progresso foi salvo" in ui.tudo()
