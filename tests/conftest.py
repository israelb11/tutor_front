import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from tutor.estado import Estado  # noqa: E402
from tutor.executor import Executor, Resultado  # noqa: E402
from tutor.logger import Log  # noqa: E402
from tutor.motor import Contexto  # noqa: E402
from tutor.ui import ScriptedUI  # noqa: E402


def pytest_addoption(parser):
    parser.addoption("--vm", action="store_true", default=False, help="roda testes que exigem VM real")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--vm"):
        return
    skip = pytest.mark.skip(reason="precisa de VM real: use --vm")
    for item in items:
        if "vm" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def ambiente_isolado(tmp_path, monkeypatch):
    home = tmp_path / "tutor_home"
    home.mkdir()
    monkeypatch.setenv("TUTOR_HOME", str(home))
    gitcfg = tmp_path / "gitconfig"
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(gitcfg))
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", os.devnull)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    return home


class FakeRunner(Executor):
    """Executor falso: registra comandos e devolve respostas programadas por prefixo."""

    def __init__(self, respostas=None, existentes=None):
        super().__init__(dry_run=False, log=Log())
        self.respostas = respostas or {}
        self.existentes = existentes
        self.chamadas = []

    def existe(self, programa):
        if self.existentes is None:
            return super().existe(programa)
        return programa in self.existentes

    def executar(self, argv, cwd=None, altera=True, timeout=600, env=None):
        self.chamadas.append(list(argv))
        for prefixo, r in self.respostas.items():
            if " ".join(argv).startswith(prefixo):
                return Resultado(argv, r[0], r[1], r[2] if len(r) > 2 else "")
        return Resultado(argv, 0, "")


@pytest.fixture
def estado(tmp_path):
    return Estado(tmp_path / "estado.json")


@pytest.fixture
def ctx(estado):
    ui = ScriptedUI()
    return Contexto(ui=ui, ex=Executor(log=Log()), estado=estado)


@pytest.fixture
def aluno(tmp_path):
    """Site de aluno com problemas típicos de iniciante."""
    p = tmp_path / "aluno"
    (p / "css").mkdir(parents=True)
    (p / "js").mkdir()
    (p / "index.html").write_text(
        "<html>\n<head>\n<script src=\"js/App.js\"></script>\n<link rel=\"stylesheet\" href=\"/css/style.css\">\n</head>\n<body>\n"
        "<div onclick=\"x()\"><b>Meu Site</b></div>\n<img src=\"img/foto.png\">\n<a href=\"sobre\">Sobre</a>\n</body>\n</html>\n",
        encoding="utf-8")
    (p / "css" / "style.css").write_text("body{color:#ccc;background:#fff;font-size:12px} *{outline:none}\n", encoding="utf-8")
    (p / "js" / "app.js").write_text(
        "var a = 1;\nif (a == 2) { document.getElementById('x').innerHTML = '<b>' + a; }\nconst api_key = 'abcdefghijklmnop12345678';\n",
        encoding="utf-8")
    return p


@pytest.fixture
def site_bom(tmp_path):
    from tutor.front import starter

    p = tmp_path / "bom"
    starter.gerar(p, "Meu Portfólio", "Portfólio de projetos web.", url_base="https://ana.github.io/bom")
    return p


@pytest.fixture
def ctx_aluno(ctx, aluno):
    ctx.estado.definir("pasta_projeto", str(aluno))
    ctx.estado.definir("fase", "Desenvolvimento")
    return ctx
