import http.client
import re
import json
import os
import stat
import subprocess
import threading
import time
import urllib.error

import pytest

from tutor import github, pdf_texto, ia
from tutor.ia import ErroIA, Gemini
from tutor.sudo import SudoNoNavegador
from tutor.web.servidor import SaidaWeb, WebUI, criar_servidor


# ---------------- servidor web
@pytest.fixture
def servidor():
    w = WebUI()
    h = criar_servidor(w, "tok123", 0)
    porta = h.server_address[1]
    t = threading.Thread(target=h.serve_forever, daemon=True)
    t.start()
    yield w, porta
    h.shutdown(); h.server_close()


def req(porta, metodo, caminho, corpo=None, headers=None):
    c = http.client.HTTPConnection("127.0.0.1", porta, timeout=5)
    h = {"Host": f"127.0.0.1:{porta}"}
    h.update(headers or {})
    c.request(metodo, caminho, body=corpo, headers=h)
    r = c.getresponse()
    return r.status, dict(r.getheaders()), r.read()


def test_sem_token_e_negado(servidor):
    _, p = servidor
    assert req(p, "GET", "/")[0] == 403
    assert req(p, "GET", "/?t=errado")[0] == 403


def test_token_valido_define_cookie_seguro_e_serve_pagina(servidor):
    _, p = servidor
    st, h, _ = req(p, "GET", "/?t=tok123")
    assert st == 302 and "HttpOnly" in h["Set-Cookie"] and "SameSite=Strict" in h["Set-Cookie"]
    st, h, corpo = req(p, "GET", "/", headers={"Cookie": "tutor_t=tok123"})
    assert st == 200 and b"Tutor Front" in corpo and "default-src" in h["Content-Security-Policy"]


def test_host_estranho_bloqueado_dns_rebinding(servidor):
    _, p = servidor
    assert req(p, "GET", "/", headers={"Host": "evil.com", "Cookie": "tutor_t=tok123"})[0] == 403


def test_post_exige_cookie_header_e_origin(servidor):
    w, p = servidor
    ck = {"Cookie": "tutor_t=tok123"}
    corpo = json.dumps({"id": 1, "valor": "x"})
    assert req(p, "POST", "/responder", corpo, ck)[0] == 403  # falta X-Tutor
    assert req(p, "POST", "/responder", corpo, {**ck, "X-Tutor": "1", "Origin": "http://evil.com"})[0] == 403
    assert req(p, "POST", "/responder", corpo, {"X-Tutor": "1"})[0] == 403  # sem cookie
    assert req(p, "POST", "/responder", corpo, {**ck, "X-Tutor": "1"})[0] == 200
    assert w.respostas[1] == "x"


def test_pergunta_e_resposta_ponta_a_ponta(servidor):
    w, p = servidor
    saida = {}
    t = threading.Thread(target=lambda: saida.update(r=w.perguntar("Nome?")))
    t.start()
    ev = []
    while not any(e["tipo"] == "pergunta" for e in ev):
        st, _, corpo = req(p, "GET", "/eventos?desde=0", headers={"Cookie": "tutor_t=tok123"})
        ev = json.loads(corpo)["eventos"]
    qid = [e for e in ev if e["tipo"] == "pergunta"][0]["id"]
    req(p, "POST", "/responder", json.dumps({"id": qid, "valor": "Ana"}), {"Cookie": "tutor_t=tok123", "X-Tutor": "1"})
    t.join(5)
    assert saida["r"] == "Ana"


def test_encerrar_libera_pergunta_pendente():
    w = WebUI()
    erro = []
    def f():
        try:
            w.perguntar("x")
        except SaidaWeb:
            erro.append(1)
    t = threading.Thread(target=f); t.start()
    w.encerrar(); t.join(5)
    assert erro


def test_frontend_nao_usa_innerhtml():
    from pathlib import Path
    js = (Path(__file__).parent.parent / "tutor" / "web" / "app.js").read_text(encoding="utf-8")
    assert not re.search(r"\.(innerHTML|outerHTML)\s*=|insertAdjacentHTML|document\.write", js) and "eval(" not in js


# ---------------- sudo
@pytest.mark.skipif(os.name == "nt", reason="unix")
def test_askpass_entrega_senha_sem_gravar_em_disco(monkeypatch, tmp_path):
    falso = tmp_path / "sudo"
    falso.write_text("#!/bin/sh\nexit 0\n"); falso.chmod(0o755)
    monkeypatch.setattr("shutil.which", lambda n: str(falso))
    with SudoNoNavegador(lambda: "segredo!") as s:
        assert stat.S_IMODE(os.stat(s.dir).st_mode) == 0o700
        r = subprocess.run([s.env()["SUDO_ASKPASS"]], capture_output=True, text=True)
        assert r.stdout.strip() == "segredo!"
        for f in s.dir.iterdir():
            if f.is_file():
                assert "segredo!" not in f.read_text()
        d = s.dir
    assert not d.exists()


# ---------------- IA
class Resp:
    def __init__(self, dados): self.d = dados
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def read(self): return json.dumps(self.d).encode()


def test_gemini_chave_permissao_e_resposta(tmp_path):
    arq = tmp_path / "k"
    vistos = {}
    def abrir(req, timeout=0):
        vistos["h"] = dict(req.header_items()); vistos["url"] = req.full_url
        return Resp({"candidates": [{"content": {"parts": [{"text": "olá "}, {"text": "aluno"}]}}]})
    g = Gemini(abrir, arq)
    assert not g.disponivel()
    with pytest.raises(ErroIA):
        g.perguntar("oi")
    g.salvar_chave("  ABC  ")
    assert stat.S_IMODE(os.stat(arq).st_mode) == 0o600 and g.chave() == "ABC"
    assert g.perguntar("oi", "ctx") == "olá aluno"
    assert vistos["h"]["X-goog-api-key"] == "ABC" and "ABC" not in vistos["url"]
    g.esquecer_chave(); assert not g.disponivel()


def test_gemini_erros(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    def http429(req, timeout=0):
        raise urllib.error.HTTPError("u", 429, "x", {}, None)
    with pytest.raises(ErroIA, match="limite"):
        Gemini(http429, tmp_path / "k").perguntar("a")
    def fora(req, timeout=0):
        raise urllib.error.URLError("sem rede")
    ok, msg = Gemini(fora, tmp_path / "k").testar()
    assert not ok and "conexão" in msg
    with pytest.raises(ErroIA, match="inesperada"):
        Gemini(lambda r, timeout=0: Resp({}), tmp_path / "k").perguntar("a")


# ---------------- github / pages / pdf
def test_github_url():
    assert github.interpretar("https://github.com/emmanuelvrm/rpg-simples") == ("emmanuelvrm", "rpg-simples")
    assert github.interpretar("https://github.com/a/b.git/") == ("a", "b")
    assert github.interpretar("http://evil.com/a/b") is None
    assert github.url_limpa("https://github.com/a/b.git") == "https://github.com/a/b"


def test_github_repo_existe_com_falsos():
    class R:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def read(self): return b"{}"
    assert github.repo_existe("https://github.com/a/b", lambda r, timeout=0: R())[0]
    def nao(r, timeout=0):
        raise urllib.error.HTTPError("u", 404, "nf", {}, None)
    assert not github.repo_existe("https://github.com/a/b", nao)[0]
    assert not github.repo_existe("lixo")[0]


def test_pages_url_e_no_ar_com_tentativas():
    from tutor.front import pages

    assert pages.url_do_site("https://github.com/Ana/meu-site") == "https://ana.github.io/meu-site/"
    assert pages.url_do_site("https://github.com/ana/ana.github.io") == "https://ana.github.io/"
    assert pages.prefixo_do_site("https://github.com/ana/meu-site") == "meu-site"
    assert pages.prefixo_do_site("https://github.com/ana/ana.github.io") == ""
    assert pages.url_do_site("lixo") == ""
    chamadas = []

    class R:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def read(self, n=0): return b"<html></html>"

    def abrir(req, timeout=0):
        chamadas.append(1)
        if len(chamadas) < 3:
            raise urllib.error.HTTPError("u", 404, "nf", {}, None)
        return R()
    ok, _ = pages.verificar_no_ar("https://x.github.io/a/", 4, 0, abrir, dormir=lambda s: None)
    assert ok and len(chamadas) == 3
    ok, msg = pages.verificar_no_ar("https://x.github.io/a/", 2, 0, lambda r, timeout=0: (_ for _ in ()).throw(urllib.error.URLError("x")),
                                    dormir=lambda s: None)
    assert not ok and msg


def test_pdf_texto_requisitos_e_pdf_de_referencia():
    from pathlib import Path
    txt = "Titulo\nRF01 O sistema deve cadastrar produtos\nblablá\nO usuário pode listar\n"
    assert pdf_texto.requisitos(txt) == ["RF01 O sistema deve cadastrar produtos", "O usuário pode listar"]
    pdf = Path(__file__).parent.parent / "materiais" / "Documentacao_Tecnica_RPG_Simples_Referencia.pdf"
    assert len(pdf_texto.extrair(pdf)) > 100


# ---------------- navegação livre (menu superior)
def test_navegar_exige_autenticacao_e_valida_alvo(servidor):
    w, p = servidor
    w.alvos_validos.add("E12")
    ck = {"Cookie": "tutor_t=tok123", "X-Tutor": "1"}
    assert req(p, "POST", "/navegar", json.dumps({"alvo": "E12"}), {"X-Tutor": "1"})[0] == 403
    st, _, corpo = req(p, "POST", "/navegar", json.dumps({"alvo": "../../etc"}), ck)
    assert st == 200 and json.loads(corpo)["ok"] is False and w.nav is None
    st, _, corpo = req(p, "POST", "/navegar", json.dumps({"alvo": "E12"}), ck)
    assert json.loads(corpo)["ok"] is True and w.nav == "E12"


def test_navegar_interrompe_pergunta_pendente():
    from tutor.motor_tipos import Navegar

    w = WebUI()
    resultado = {}

    def espera():
        try:
            w.pausa("x")
        except Navegar as n:
            resultado["alvo"] = n.alvo

    t = threading.Thread(target=espera, daemon=True)
    t.start()
    time.sleep(0.2)
    assert w.navegar("proxima")
    t.join(3)
    assert resultado == {"alvo": "proxima"}


def test_motor_navega_para_qualquer_etapa_e_nao_prende_no_fim(estado):
    from tutor.executor import Executor
    from tutor.motor import Contexto, Motor
    from tutor.motor_tipos import Check, Etapa, Navegar, Passo
    from tutor.ui import ScriptedUI

    ordem = []

    def mk(id_, aplica=None):
        return Etapa(id=id_, titulo=f"Etapa {id_}", objetivo="o", porque="p", aplica=aplica,
                     passos=[Passo("x", fazer=lambda c, m, id_=id_: ordem.append(id_), sempre=True)],
                     verificar=lambda c: [Check("ok", True)])

    class UI(ScriptedUI):
        def __init__(self):
            super().__init__()
            self.script = ["nav:T3", "F"]   # em T1 o aluno clica na etapa T3 (que 'não se aplica'); em T3 escolhe Fazer
            self.fim = 0

        def escolher_letra(self, pergunta, letras):
            self._reg("? " + pergunta)
            if "agora" in pergunta:          # menu do fim da lista: sai
                self.fim += 1
                return "S"
            item = self.script.pop(0)
            if item.startswith("nav:"):
                raise Navegar(item[4:])
            return item

    ctx = Contexto(ui=UI(), ex=Executor(), estado=estado)
    Motor([mk("T1"), mk("T2"), mk("T3", aplica=lambda c: False)], ctx).executar()
    assert ordem == ["T3"]                     # foi direto para T3, mesmo não se aplicando; T1 e T2 ficam pendentes
    assert ctx.estado.status("T3") == "ok" and ctx.estado.status("T1") is None
    assert ctx.ui.fim == 1                     # terminou a lista e perguntou o que fazer, em vez de encerrar sozinho


def test_motor_etapa_que_nao_se_aplica_nao_fica_marcada_como_pulada(estado):
    from tutor.executor import Executor
    from tutor.motor import Contexto, Motor
    from tutor.motor_tipos import Check, Etapa, Passo
    from tutor.ui import ScriptedUI

    class UI(ScriptedUI):
        def escolher_letra(self, pergunta, letras):
            return "S"

    e = Etapa(id="T9", titulo="t", objetivo="o", passos=[Passo("x")], verificar=lambda c: [Check("ok", True)], aplica=lambda c: False)
    ctx = Contexto(ui=UI(), ex=Executor(), estado=estado)
    Motor([e], ctx).executar()
    assert ctx.estado.status("T9") is None    # ao mudar de fase ela volta a aparecer
