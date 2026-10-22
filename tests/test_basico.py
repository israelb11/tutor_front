import json
import os
import stat
import subprocess
import sys

import pytest

from tutor import dependencias, sistema
from tutor.executor import Executor, montar_argv
from tutor.estado import Estado
from tutor.logger import Log
from tutor.seguranca import mascarar, nome_seguro, parece_segredo


def test_mascarar_segredos():
    assert "AIzaSyABCDEFGHIJKLMNOPQRSTUV" not in mascarar("chave AIzaSyABCDEFGHIJKLMNOPQRSTUV fim")
    assert "ghp_" not in mascarar("token ghp_abcdefghijklmnopqrstuvwxyz0123")
    assert mascarar("senha=abc123") == "senha=***"
    assert mascarar("texto normal") == "texto normal"


def test_parece_segredo_e_nome_seguro():
    assert parece_segredo('API_KEY = "abcdef123456"')
    assert not parece_segredo("x = 1")
    assert nome_seguro("Meu Produto!") == "meu_produto"
    assert nome_seguro("9abc").startswith("x_")


def test_montar_argv_nao_reinterpreta_valor_do_aluno():
    argv = montar_argv("git commit -m {msg}", msg="oi; rm -rf /")
    assert argv == ["git", "commit", "-m", "oi; rm -rf /"]


def test_executor_dry_run_nao_executa(tmp_path):
    ex = Executor(dry_run=True, log=Log(tmp_path / "l.log"))
    alvo = tmp_path / "criado.txt"
    r = ex.executar(["touch", str(alvo)])
    assert r.simulado and not alvo.exists()
    r2 = ex.executar([sys.executable, "-c", "print('ola')"], altera=False)
    assert "ola" in r2.saida  # leitura roda mesmo em dry-run


def test_executor_script_sh_usa_variaveis(tmp_path):
    ex = Executor(log=Log(tmp_path / "l.log"))
    r = ex.script_sh('echo "$TUTOR_NOME"', {"nome": "a; echo hacked"}, altera=False)
    assert r.saida.strip() == "a; echo hacked"


def test_executor_programa_inexistente(tmp_path):
    r = Executor(log=Log(tmp_path / "l.log")).executar(["programa_que_nao_existe_xyz"])
    assert r.codigo == 127


def test_log_mascara(tmp_path):
    l = Log(tmp_path / "x.log")
    l.escrever("token ghp_abcdefghijklmnopqrstuvwxyz0123")
    assert "ghp_" not in (tmp_path / "x.log").read_text()


def test_estado_persistencia_e_checklist(tmp_path):
    e = Estado(tmp_path / "e.json")
    e.definir("fase", "Desenvolvimento")
    e.marcar("E01", "ok")
    e2 = Estado(tmp_path / "e.json")
    assert e2.info("fase") == "Desenvolvimento" and e2.status("E01") == "ok"

    class E:
        id, titulo = "E01", "Teste"
    assert "[x] E01" in e2.checklist_md([E()])


def test_familia_mint_e_debian(tmp_path):
    assert sistema.familia({"ID": "linuxmint", "ID_LIKE": "ubuntu debian"}) == "ubuntu"
    assert sistema.familia({"ID": "debian"}) == "debian"
    assert sistema.familia({"ID": "fedora", "ID_LIKE": "rhel"}) == "outra"


def test_comando_instalar():
    assert sistema.comando_instalar("git", "linux", "ubuntu") == ["sudo", "apt-get", "install", "-y", "git"]
    assert sistema.comando_instalar("git", "windows", "outra")[0] == "winget"
    assert sistema.comando_instalar("geany", "windows", "outra") is None


def test_decidir_ambiente():
    d = dependencias.decidir_ambiente
    assert d([], {"pode": False}) == "completo"
    assert d(["git"], {"pode": True}) == "completo"
    assert d(["git"], {"pode": False}) == "somente_execucao"
    assert d(["python"], {"pode": False}) == "vm"
    assert d(["python", "git"], {"pode": False}) == "vm"


def test_catalogo_e_referencias():
    from tutor import referencias
    from tutor.etapas import catalogo

    etapas = catalogo()
    ids = [e.id for e in etapas]
    assert len(ids) == len(set(ids))
    base = referencias.todas()
    for e in etapas:
        assert e.objetivo and e.porque, e.id
        assert e.verificar is not None, e.id
        assert e.passos, e.id
        for k in e.refs:
            assert k in base, f"{e.id}: referência {k} não existe"
    for chave, itens in base.items():
        for r in itens:
            assert r["titulo"] and r["link"], chave


def test_passos_que_executam_comando_sao_marcados_como_alteracao():
    from tutor.etapas import catalogo

    somente_leitura = ("git status",)
    for e in catalogo():
        for p in e.passos:
            if p.comando and p.fazer and not p.comando.startswith(somente_leitura):
                assert p.altera, f"{e.id}: '{p.texto}' deve ter altera=True"


def test_nenhuma_etapa_apaga_arquivos_do_aluno():
    from pathlib import Path

    for f in Path(__file__).resolve().parent.parent.glob("tutor/**/*.py"):
        if f.name == "sudo.py":
            continue
        t = f.read_text(encoding="utf-8")
        assert "rmtree" not in t and "os.remove" not in t and ".unlink(" not in t or f.name == "ia.py", f.name


def test_codigo_compila_no_python_minimo():
    """Python 3.10 não aceita barra invertida/aspas repetidas dentro de f-strings: garante a sintaxe mínima."""
    import ast
    from pathlib import Path

    raiz = Path(__file__).resolve().parent.parent
    for f in list(raiz.glob("tutor/**/*.py")) + [raiz / "tutor_front.py"]:
        ast.parse(f.read_text(encoding="utf-8"), filename=str(f), feature_version=(3, 10))
