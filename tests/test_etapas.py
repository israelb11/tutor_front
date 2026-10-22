"""Fluxo das etapas com UI simulada: o tutor guia, corrige com segurança e confere."""
from pathlib import Path

import pytest

from tests.conftest import FakeRunner
from tutor.etapas import catalogo, inicio, publicar, qualidade, repositorio
from tutor.front import docgen_front, pages
from tutor.front.auditoria import auditar_pasta
from tutor.logger import Log
from tutor.motor import Contexto, Motor
from tutor.ui import ScriptedUI


def novo_ctx(estado, pasta=None, respostas=None, ex=None, **info):
    ctx = Contexto(ui=ScriptedUI(respostas), ex=ex or FakeRunner(existentes={"git"}), estado=estado, log=Log())
    if pasta:
        ctx.estado.definir("pasta_projeto", str(pasta))
    ctx.estado.definir("fase", "Desenvolvimento")
    for k, v in info.items():
        ctx.estado.definir(k, v)
    return ctx


def ajuda(ctx, etapa):
    Motor([etapa], ctx)._modo_ajuda(etapa)
    return Motor([etapa], ctx).verificar(etapa)


def test_catalogo_completo_e_ordenado():
    ids = [e.id for e in catalogo()]
    assert len(ids) == len(set(ids)) == 39
    assert ids[:8] == ["E00", "E01", "E02", "A1", "E03", "Q1", "A2", "E04"]
    assert [i for i in ids if i.startswith("E")] == [f"E{n:02d}" for n in range(31)]
    assert [i for i in ids if i[0] in "AQ"] == ["A1", "Q1", "A2", "Q2", "A3", "Q3", "A4", "Q4"]
    assert ids[-10:] == ["Q3", "A4", "E24", "E25", "E26", "E27", "E28", "E29", "E30", "Q4"]
    assert catalogo()[0].titulo.startswith("IA opcional")  # a chave do Gemini vem antes de tudo


def test_e03_cria_site_inicial(estado, tmp_path):
    ctx = novo_ctx(estado, respostas=[1, str(tmp_path), "meu-site", "Loja da Ana", "Doces caseiros", "#c2410c"])
    e = inicio.e03()
    assert ajuda(ctx, e)
    assert (tmp_path / "meu-site" / "index.html").exists()
    assert "Loja da Ana" in (tmp_path / "meu-site" / "index.html").read_text(encoding="utf-8")
    assert ctx.estado.info("pasta_projeto") == str((tmp_path / "meu-site").resolve())
    assert auditar_pasta(tmp_path / "meu-site").geral == 100


def test_e03_pasta_inexistente_falha(estado, tmp_path):
    ctx = novo_ctx(estado, respostas=[0, str(tmp_path / "nada")])
    assert not ajuda(ctx, inicio.e03())


def test_e03_nao_sobrescreve_site_existente(estado, aluno):
    antes = (aluno / "index.html").read_text()
    ctx = novo_ctx(estado, respostas=[0, str(aluno)])
    ajuda(ctx, inicio.e03())
    assert (aluno / "index.html").read_text() == antes


def test_e02_planejamento_guarda_publico_e_paginas(estado):
    ctx = novo_ctx(estado, respostas=["Clientes da loja", "Início, Produtos , Contato"])
    inicio.e02().passos[1].fazer(ctx, "F")
    assert ctx.estado.info("publico") == "Clientes da loja"
    assert ctx.estado.info("paginas_planejadas") == ["Início", "Produtos", "Contato"]


def test_e05_registra_nota_inicial(estado, aluno):
    ctx = novo_ctx(estado, aluno)
    assert ajuda(ctx, qualidade.e05())
    assert "Raio-X" in ctx.ui.tudo()
    from tutor.etapas.util import primeira_nota
    assert primeira_nota(ctx)["geral"] < 70


def test_e06_cria_so_arquivos_novos(estado, aluno):
    ctx = novo_ctx(estado, aluno)
    antes = (aluno / "index.html").read_text()
    Motor([repositorio.e06()], ctx)._modo_ajuda(repositorio.e06())
    assert (aluno / "README.md").exists() and (aluno / ".gitignore").exists()
    assert (aluno / "index.html").read_text() == antes


def test_e12_corrige_cabecalho_e_mantem_backup(estado, aluno):
    ctx = novo_ctx(estado, aluno, respostas=["SIM", 1, 1, 0])
    e = qualidade.e12()
    ajuda(ctx, e)
    txt = (aluno / "index.html").read_text()
    assert txt.startswith("<!DOCTYPE html>") and 'lang="pt-BR"' in txt
    assert list((aluno / ".tutor_backup").rglob("index.html"))


def test_etapa_de_area_bloqueia_com_erro_e_libera_so_com_sugestoes(estado, aluno):
    ctx = novo_ctx(estado, aluno)
    checks = qualidade.e15().verificar(ctx)
    assert any(not c.ok for c in checks)               # contraste/foco: erro bloqueia
    ctx2 = novo_ctx(estado, aluno)
    (aluno / "css" / "style.css").write_text("body{color:#111;background:#fff}")
    c2 = qualidade.e13().verificar(ctx2)
    assert all(c.ok for c in c2)


def test_quiz_nao_bloqueia(estado, site_bom):
    ctx = novo_ctx(estado, site_bom, respostas=[2, 2, 2])  # respostas erradas
    assert ajuda(ctx, qualidade.e12())
    assert "Quase" in ctx.ui.tudo()


def test_e15_calculadora_de_contraste(estado, site_bom):
    ctx = novo_ctx(estado, site_bom, respostas=["#777777", "#ffffff", "#cccccc", "#ffffff", ""])
    qualidade.e15().passos[1].fazer(ctx, "F")
    t = ctx.ui.tudo()
    assert "passa" in t and "falha" in t


def test_e19_modo_pages_e_placar_final(estado, aluno, site_bom):
    ctx = novo_ctx(estado, site_bom, repo_url="https://github.com/ana/bom")
    ctx.estado.definir("pasta_projeto", str(site_bom))
    from tutor.etapas.util import registrar_nota, relatorio
    registrar_nota(ctx, "inicio", auditar_pasta(aluno))
    assert ajuda(ctx, qualidade.e19())
    t = ctx.ui.tudo()
    assert "/bom/" in t and "nota final: 100" in t
    assert (site_bom / "docs" / "QUALIDADE.md").exists()


def test_e19_falha_com_erros(estado, aluno):
    ctx = novo_ctx(estado, aluno, repo_url="https://github.com/ana/aluno")
    assert not ajuda(ctx, qualidade.e19())


def test_e17_arquivos_seo(estado, aluno):
    ctx = novo_ctx(estado, aluno, repo_url="https://github.com/ana/aluno")
    Motor([qualidade.e17()], ctx)._modo_ajuda(qualidade.e17())
    assert (aluno / "robots.txt").exists() and (aluno / "sitemap.xml").exists() and (aluno / "404.html").exists()


def test_e20_commit_com_git_real(estado, site_bom, tmp_path):
    import subprocess
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=site_bom, check=True)
    ctx = Contexto(ui=ScriptedUI(["Primeira versão"]), ex=__import__("tutor.executor", fromlist=["Executor"]).Executor(log=Log()), estado=estado)
    ctx.estado.definir("pasta_projeto", str(site_bom))
    ctx.estado.definir("repo_url", "https://github.com/ana/bom")
    subprocess.run(["git", "config", "user.email", "a@b.c"], cwd=site_bom, check=True)
    subprocess.run(["git", "config", "user.name", "A"], cwd=site_bom, check=True)
    publicar._e20_commit(ctx, "A")
    log = subprocess.run(["git", "log", "--oneline"], cwd=site_bom, capture_output=True, text=True).stdout
    assert "Primeira versão" in log
    assert all(c.ok for c in publicar._e20_verificar(ctx))


def test_e21_guia_e_verificacao(estado, site_bom, monkeypatch):
    ctx = novo_ctx(estado, site_bom, repo_url="https://github.com/ana/bom")
    monkeypatch.setattr(pages, "verificar_no_ar", lambda url, *a, **k: (True, "no ar"))
    assert ajuda(ctx, publicar.e21())
    assert "https://ana.github.io/bom/" in ctx.ui.tudo()
    assert ctx.estado.info("site_no_ar") is True


def test_e21_site_fora_do_ar_nao_passa(estado, site_bom, monkeypatch):
    ctx = novo_ctx(estado, site_bom, repo_url="https://github.com/ana/bom")
    monkeypatch.setattr(pages, "verificar_no_ar", lambda url, *a, **k: (False, "ainda não publicado (404)"))
    assert not ajuda(ctx, publicar.e21())


def test_e22_coloca_link_no_readme(estado, site_bom, monkeypatch):
    ctx = novo_ctx(estado, site_bom, repo_url="https://github.com/ana/bom", url_site="https://ana.github.io/bom/")
    publicar._e22_readme(ctx, "A")
    assert "https://ana.github.io/bom/" in (site_bom / "README.md").read_text(encoding="utf-8")
    publicar._e22_readme(ctx, "A")  # idempotente
    assert (site_bom / "README.md").read_text(encoding="utf-8").count("https://ana.github.io/bom/") >= 1


def test_e23_documentacao(estado, site_bom):
    ctx = novo_ctx(estado, site_bom, requisitos=["Mostrar portfólio"], publico="Recrutadores")
    assert ajuda(ctx, publicar.e23())
    doc = (site_bom / "docs" / "DOCUMENTACAO.md").read_text(encoding="utf-8")
    assert "Mostrar portfólio" in doc and "Recrutadores" in doc and "contato.html" in doc and "--cor-primaria" in doc


def test_e23_modo_planejamento_sem_pasta(estado, tmp_path):
    ctx = novo_ctx(estado, respostas=["SIM", str(tmp_path / "plano")], requisitos=["RF1"])
    ctx.estado.definir("so_planejamento", True)
    assert ajuda(ctx, publicar.e23())
    assert (tmp_path / "plano" / "docs" / "DOCUMENTACAO.md").exists()


def test_etapas_de_qualidade_nao_apagam_nada(estado, aluno):
    antes = sorted(p.relative_to(aluno).as_posix() for p in aluno.rglob("*") if p.is_file())
    ctx = novo_ctx(estado, aluno, repo_url="https://github.com/ana/aluno", respostas=[0] * 40)
    for e in (qualidade.e05(), repositorio.e06(), qualidade.e12(), qualidade.e13(), qualidade.e17()):
        Motor([e], ctx)._modo_ajuda(e)
    depois = sorted(p.relative_to(aluno).as_posix() for p in aluno.rglob("*") if p.is_file() and ".tutor_backup" not in p.parts)
    assert set(antes) <= set(depois)


def test_etapas_so_planejamento_ficam_ocultas(estado):
    ctx = novo_ctx(estado)
    ctx.estado.definir("so_planejamento", True)
    aplicaveis = [e.id for e in catalogo() if e.aplica is None or e.aplica(ctx)]
    assert "E12" not in aplicaveis and "E21" not in aplicaveis and "E23" in aplicaveis and "E03" in aplicaveis and "E00" in aplicaveis


def test_percurso_completo_em_modo_ajuda(estado, aluno, monkeypatch):
    """Passa por TODAS as etapas escolhendo [A]juda: o site ruim termina sem erros e com nota alta."""
    from tutor import github

    monkeypatch.setattr(github, "repo_existe", lambda url, abrir=None: (True, "ok"))
    monkeypatch.setattr(github, "arquivos_na_raiz", lambda url, abrir=None: ["index.html"])
    monkeypatch.setattr(pages, "verificar_no_ar", lambda url, *a, **k: (True, "no ar"))

    class UIA(ScriptedUI):
        def escolher_letra(self, pergunta, letras):
            self._reg("? " + pergunta)
            return "A" if "A" in letras and "fazer" in pergunta.lower() else ("A" if "Como seguir" in pergunta else "A")

        def perguntar(self, pergunta, padrao=""):
            if "repositório" in pergunta.lower() and "endereço" in pergunta.lower():
                return "https://github.com/ana/aluno"
            return super().perguntar(pergunta, padrao)

    ctx = Contexto(ui=UIA(), ex=FakeRunner(existentes={"git", "python3"}), estado=estado, log=Log())
    ctx.estado.definir("pasta_projeto", str(aluno))
    ctx.estado.definir("fase", "Desenvolvimento")
    ctx.estado.definir("repo_url", "https://github.com/ana/aluno")
    ctx.estado.definir("ambiente", "completo")
    ctx.cache["quiz_sem_embaralhar"] = True  # no teste, a opção 0 é sempre a certa
    ctx.cache["usar_python_atual"] = True
    for i in range(5):
        ctx.estado.marcar(f"E{i:02d}", "ok")
    # corrige à mão o que o tutor não corrige (como o aluno faria)
    (aluno / "index.html").write_text(
        "<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Aluno</title><meta name='description' content='Site do aluno com projetos e contato para quem quer conhecer o trabalho dele.'>"
        "<link rel='icon' href='favicon.svg'><link rel='stylesheet' href='css/style.css'><script src='js/app.js' defer></script></head>"
        "<body><main><h1>Meu Site</h1><nav><a href='index.html'>Início</a></nav></main></body></html>", encoding="utf-8")
    (aluno / "css" / "style.css").write_text(
        "*,*::before,*::after{box-sizing:border-box}body{color:#111;background:#fff;font-size:1rem;margin:0}"
        "a:focus-visible{outline:3px solid #036}@media (prefers-reduced-motion:reduce){*{animation:none}}", encoding="utf-8")
    (aluno / "js" / "app.js").write_text("const a = 1;\nif (a === 2) { document.title = String(a); }\n", encoding="utf-8")
    Motor(catalogo(), ctx).executar()
    final = auditar_pasta(aluno)
    assert final.contagem()["erro"] == 0, [a.texto() for a in final.achados if a.nivel == "erro"]
    assert (aluno / "docs" / "DOCUMENTACAO.md").exists() and (aluno / "docs" / "QUALIDADE.md").exists()
    assert ctx.estado.status("E23") == "ok" and ctx.estado.status("E21") == "ok"


def test_e00_ia_testa_chave_e_nao_bloqueia_sem_chave(estado, monkeypatch):
    from tutor import ia as ia_mod
    ctx = novo_ctx(estado, respostas=[""])
    ctx.ia = ia_mod.Gemini()
    e = inicio.e04_ia()
    assert e.id == "E00" and len(e.passos) == 4
    assert ajuda(ctx, e)                      # sem chave: etapa opcional passa
    t = ctx.ui.tudo()
    assert "aistudio.google.com/apikey" in t and "Create API key" in t and "Projects" in t
    # com chave válida (simulada)
    monkeypatch.setattr(ia_mod.Gemini, "salvar_chave", lambda self, c: setattr(self, "_k", c))
    monkeypatch.setattr(ia_mod.Gemini, "disponivel", lambda self: getattr(self, "_k", None) is not None)
    monkeypatch.setattr(ia_mod.Gemini, "testar", lambda self: (True, "ok"))
    ctx2 = novo_ctx(estado, respostas=["AIzaFAKE"])
    ctx2.ia = ia_mod.Gemini()
    assert ajuda(ctx2, e) and ctx2.estado.info("ia_testada") is True


def test_ia_explica_achados_sem_enviar_segredo(estado, aluno):
    class IAFalsa:
        enviado = ""
        def disponivel(self): return True
        def perguntar(self, p, c=""):
            IAFalsa.enviado = p
            return "explicação da IA"
    ctx = novo_ctx(estado, aluno, respostas=[True])
    ctx.ia = IAFalsa()
    from tutor.etapas.util import mostrar_achados
    mostrar_achados(ctx, ("JavaScript",), "JS")
    assert "explicação da IA" in ctx.ui.tudo()
    assert "abcdefghijklmnop12345678" not in IAFalsa.enviado
