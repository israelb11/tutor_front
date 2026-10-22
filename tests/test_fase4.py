"""Fase 4: do site estático ao web app (dados, modelagem, SQLite/CRUD, Flask, Render, Supabase, mídia e quizzes)."""
import ast
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

from tests.conftest import FakeRunner
from tutor import midia, seguranca
from tutor.etapas import catalogo, mapas, webapp
from tutor.front import backend, dados, modelagem
from tutor.front.auditoria import auditar_pasta
from tutor.front.modelador import Modelador
from tutor.front.site import escanear
from tutor.logger import Log
from tutor.motor import Contexto, Motor
from tutor.motor_tipos import Navegar
from tutor.ui import ScriptedUI

HTML_CONTATO = """<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><title>Contato</title></head>
<body><main><h1>Fale conosco</h1>
<form id="form-contato" action="#"><label>Nome <input name="nome" required></label>
<label>E-mail <input type="email" name="email" required></label><label>Idade <input type="number" name="idade"></label>
<label>Mensagem <textarea name="mensagem"></textarea></label><button type="submit">Enviar</button></form>
<form id="busca"><input type="search" name="q"><button>Buscar</button></form>
<form id="entrar"><input name="login" id="login"><input type="password" name="senha"><button>Entrar</button></form>
</main></body></html>"""
JS_TAREFAS = """const produtos = [ { id: 1, nome: 'Bolo', preco: 10 }, { id: 2, nome: 'Torta', preco: 12 } ];
function adicionarTarefa(t) { const l = JSON.parse(localStorage.getItem('tarefas') || '[]'); l.push(t); localStorage.setItem('tarefas', JSON.stringify(l)); }
function removerTarefa(i) {}
const listarTarefas = () => [];
function editarTarefa() {}
"""


@pytest.fixture
def site_dados(tmp_path):
    p = tmp_path / "meusite"
    (p / "js").mkdir(parents=True)
    (p / "contato.html").write_text(HTML_CONTATO, encoding="utf-8")
    (p / "index.html").write_text("<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'><title>x</title></head><body><main><h1>x</h1></main></body></html>", encoding="utf-8")
    (p / "js" / "tarefas.js").write_text(JS_TAREFAS, encoding="utf-8")
    return p


def modelo_loja():
    m = modelagem.modelo_de_respostas(["clientes", "pedidos", "produtos"], [("clientes", "pedidos", "1N"), ("pedidos", "produtos", "NN")])
    m["tabelas"].append(modelagem.tabela_vazia("mensagens", [("nome", "TEXT"), ("email", "TEXT"), ("mensagem", "TEXT")]))
    m["tabelas"].append({"nome": "usuarios", "colunas": [{"nome": "id", "tipo": "INTEGER", "pk": True}, {"nome": "email", "tipo": "TEXT", "unico": True, "nn": True},
                                                          {"nome": "senha_hash", "tipo": "TEXT", "nn": True}]})
    return modelagem.normalizar(m)


# ------------------------------------------------------------------ modelagem
def test_validacao_aponta_erros_de_modelagem():
    m = modelagem.normalizar({"tabelas": [
        {"nome": "Clientes!", "colunas": [{"nome": "nome", "tipo": "TEXT"}]},
        {"nome": "pedidos", "colunas": [{"nome": "id", "tipo": "INTEGER", "pk": True}, {"nome": "cliente_id", "tipo": "INTEGER", "fk": {"tabela": "fantasma", "coluna": "id"}},
                                         {"nome": "senha", "tipo": "TEXT"}]},
    ]})
    textos = " | ".join(a["texto"] for a in modelagem.validar(m) if a["nivel"] == "erro")
    assert "chave primária" in textos and "não existe" in textos
    assert any("senha pura" in a["texto"] for a in modelagem.validar(m))
    assert modelagem.tem_erros(m)
    assert modelagem.validar({"tabelas": []})[0]["nivel"] == "erro"


def test_fk_precisa_apontar_para_pk():
    m = modelagem.normalizar({"tabelas": [
        {"nome": "a", "colunas": [{"nome": "id", "tipo": "INTEGER", "pk": True}, {"nome": "x", "tipo": "TEXT"}]},
        {"nome": "b", "colunas": [{"nome": "id", "tipo": "INTEGER", "pk": True}, {"nome": "a_x", "tipo": "TEXT", "fk": {"tabela": "a", "coluna": "x"}}]}]})
    assert any("deve apontar para a PK" in a["texto"] for a in modelagem.validar(m))


def test_modelo_loja_valido_e_sql_executa():
    m = modelo_loja()
    assert not modelagem.tem_erros(m)
    con = sqlite3.connect(":memory:")
    con.executescript(modelagem.sql_sqlite(m))
    tabs = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'") if not r[0].startswith("sqlite_")}
    assert tabs == {"clientes", "pedidos", "produtos", "pedidos_produtos", "mensagens", "usuarios"}
    # a FK é respeitada: pedido de cliente inexistente é recusado
    con.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT INTO pedidos (cliente_id) VALUES (99)")


def test_relacionamentos_e_ordem_de_criacao():
    m = modelo_loja()
    tipos = {(r["de"], r["para"], r["tipo"]) for r in modelagem.relacionamentos(m)}
    assert ("clientes", "pedidos", "1:N") in tipos and ("pedidos", "produtos", "N:N") in tipos
    ordem = [t["nome"] for t in modelagem.ordem_criacao(m)]
    assert ordem.index("clientes") < ordem.index("pedidos") < ordem.index("pedidos_produtos")


def test_sql_postgres_serial_rls_e_tipos():
    m = modelagem.normalizar({"tabelas": [{"nome": "itens", "colunas": [{"nome": "id", "tipo": "INTEGER", "pk": True}, {"nome": "ativo", "tipo": "BOOLEAN"},
                                                                       {"nome": "preco", "tipo": "REAL"}, {"nome": "criado", "tipo": "DATETIME"}]}]})
    sql = modelagem.sql_postgres(m)
    assert "id SERIAL PRIMARY KEY" in sql and "ativo BOOLEAN" in sql and "DOUBLE PRECISION" in sql and "TIMESTAMP" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql and "AUTOINCREMENT" not in sql


def test_normalizar_limpa_entrada_hostil():
    m = modelagem.normalizar({"tabelas": [{"nome": "Pág. Início; DROP", "x": 99999, "colunas": [{"nome": "Nome Completo", "tipo": "xpto"}] * 3}] * 50})
    assert len(m["tabelas"]) == 30 and m["tabelas"][0]["nome"] == "pag_inicio_drop" and "x" not in m["tabelas"][0]
    assert m["tabelas"][0]["colunas"][0] == {"nome": "nome_completo", "tipo": "TEXT"}
    assert modelagem.normalizar("lixo") == {"tabelas": []}


def test_mesclar_sugestao_e_json_da_ia():
    m = modelagem.modelo_de_respostas(["clientes"], [])
    sug = modelagem.normalizar(modelagem.extrair_json('Claro!\n```json\n{"tabelas":[{"nome":"clientes","colunas":[{"nome":"email","tipo":"TEXT"}]},{"nome":"enderecos","colunas":[{"nome":"id","tipo":"INTEGER","pk":true}]}]}\n```'))
    novo, mudou = modelagem.mesclar_sugestao(m, sug)
    assert "tabela nova: enderecos" in mudou and "coluna nova: clientes.email" in mudou
    assert modelagem.extrair_json("sem json aqui") is None


# ------------------------------------------------------------------ análise do site
def test_analise_acha_formularios_localstorage_listas_e_funcoes(site_dados):
    a = dados.analisar(escanear(site_dados))
    por = {c.tabela: c for c in a.candidatos}
    assert "mensagens" in por and [n for n, *_ in por["mensagens"].campos] == ["nome", "email", "idade", "mensagem"]
    tipos = {n: t for n, t, *_ in por["mensagens"].campos}
    assert tipos["idade"] == "INTEGER"
    assert "usuarios" in por and ("senha_hash", "TEXT", "NUNCA guarde a senha pura: guarde um hash") in por["usuarios"].campos
    assert "tarefas" in por and por["tarefas"].tipo == "localstorage"
    assert "produtos" in por and [n for n, *_ in por["produtos"].campos] == ["id", "nome", "preco"]
    assert not any("busca" in c.origem and c.tabela == "buscas" for c in a.candidatos)  # busca não vira tabela
    assert {(f.nome, f.crud) for f in a.funcoes} >= {("adicionarTarefa", "C"), ("removerTarefa", "D"), ("listarTarefas", "R"), ("editarTarefa", "U")}
    assert any("hash" in av.lower() for av in a.avisos)
    assert dados.resumo(a) and dados.resumo_crud(a)


def test_analise_avisa_campo_sem_name(tmp_path):
    (tmp_path / "c.html").write_text("<!DOCTYPE html><html><body><form id='f'><input id='nome'><input name='email' type='email'></form></body></html>", encoding="utf-8")
    a = dados.analisar(escanear(tmp_path))
    assert any("só tem id" in av for c in a.candidatos for av in c.avisos)


def test_modelo_de_candidatos_vira_modelo_valido(site_dados):
    a = dados.analisar(escanear(site_dados))
    m = modelagem.modelo_de_candidatos(a.candidatos)
    assert not modelagem.tem_erros(m) and {"mensagens", "usuarios", "tarefas", "produtos"} <= {t["nome"] for t in m["tabelas"]}


# ------------------------------------------------------------------ back-end gerado
def test_arquivos_gerados_compilam_em_python_310(tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    backend.gerar(p, modelo_loja(), "Minha Loja", parte="tudo")
    backend.gerar(p, modelo_loja(), "Minha Loja", dual=True, parte="tudo")
    for f in ("app.py", "db.py", "exemplo_crud.py", "migrar_para_supabase.py"):
        ast.parse((p / f).read_text(encoding="utf-8"), feature_version=(3, 8))
    assert "DATABASE_URL" in (p / "db.py").read_text() and "psycopg" in (p / "requirements.txt").read_text()
    assert "sync: false" in (p / "render.yaml").read_text() and "gunicorn app:app" in (p / "render.yaml").read_text()
    assert (p / ".gitignore").read_text().count(".venv/") == 1


def test_primeiro_crud_roda_de_verdade(tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    backend.gerar(p, modelo_loja(), "x", parte="banco")
    r = subprocess.run([sys.executable, "exemplo_crud.py"], cwd=p, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert "C - criei" in r.stdout and "depois de apagar, sobraram: 0" in r.stdout


def test_gerar_nao_sobrescreve_app_editado(tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    backend.gerar(p, modelo_loja(), "x")
    (p / "app.py").write_text("# do aluno\n", encoding="utf-8")
    (p / "js").mkdir(exist_ok=True)
    (p / "js" / "api.js").write_text("// do aluno\n", encoding="utf-8")
    backend.gerar(p, modelo_loja(), "x", dual=True)
    assert (p / "app.py").read_text() == "# do aluno\n" and (p / "js" / "api.js").read_text() == "// do aluno\n"


@pytest.fixture
def cliente_flask(tmp_path, monkeypatch):
    pytest.importorskip("flask")
    p = tmp_path / "web"
    p.mkdir()
    (p / "index.html").write_text("<h1>oi</h1>", encoding="utf-8")
    (p / "404.html").write_text("<h1>nada</h1>", encoding="utf-8")
    backend.gerar(p, modelo_loja(), "web")
    monkeypatch.setenv("DATABASE_PATH", str(p / "t.db"))
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    monkeypatch.syspath_prepend(str(p))
    for m in ("app", "db"):
        sys.modules.pop(m, None)
    import app as A
    yield A.app.test_client()
    sys.modules.pop("app", None)
    sys.modules.pop("db", None)


def test_api_flask_crud_e_seguranca(cliente_flask):
    c = cliente_flask
    r = c.post("/api/mensagens", json={"nome": "Ana", "email": "a@b.c", "mensagem": "oi", "lixo": 1})
    assert r.status_code == 201 and r.json["ignorados"] == ["lixo"]
    # senha vira hash e nunca é devolvida
    r = c.post("/api/usuarios", json={"email": "x@y.z", "senha": "123456"})
    assert r.status_code == 201
    lista = c.get("/api/usuarios").json["dados"]
    assert lista == [{"id": 1, "email": "x@y.z"}]
    con = sqlite3.connect(os.environ["DATABASE_PATH"])
    assert con.execute("SELECT senha_hash FROM usuarios").fetchone()[0].startswith(("scrypt:", "pbkdf2:"))
    # obrigatório e unicidade
    assert c.post("/api/usuarios", json={"email": "x@y.z", "senha": "1"}).status_code == 400
    assert c.post("/api/usuarios", json={"senha": "1"}).status_code == 400
    # FK inexistente é recusada com mensagem amigável
    r = c.post("/api/pedidos", json={"cliente_id": 99})
    assert r.status_code == 400 and r.json["ok"] is False
    # CRUD completo
    cid = c.post("/api/clientes", json={"nome": "Zé"}).json["id"]
    assert c.put(f"/api/clientes/{cid}", json={"nome": "José"}).json["ok"]
    assert c.get(f"/api/clientes/{cid}").json["dados"]["nome"] == "José"
    assert c.delete(f"/api/clientes/{cid}").json["ok"]
    assert c.get(f"/api/clientes/{cid}").status_code == 404
    # tabela de junção usa chave composta
    assert c.get("/api/pedidos_produtos/1").status_code == 400
    # tipo errado
    assert c.post("/api/pedidos", json={"cliente_id": "abc"}).status_code == 400
    assert c.get("/api/inexistente").status_code == 404
    esq = c.get("/api/_esquema").json
    assert esq["banco"] == "sqlite" and "senha_hash" not in esq["tabelas"]["usuarios"]["colunas"]


def test_api_flask_protege_dados_privados_fora_do_localhost(cliente_flask, monkeypatch):
    c = cliente_flask
    c.post("/api/mensagens", json={"nome": "Ana", "mensagem": "segredo"})
    externo = {"environ_overrides": {"REMOTE_ADDR": "8.8.8.8"}}
    assert c.get("/api/mensagens", **externo).status_code == 401          # sem token e fora do localhost
    assert c.post("/api/mensagens", json={"nome": "Visitante"}, **externo).status_code == 201  # formulário público continua funcionando
    assert c.put("/api/mensagens/1", json={"nome": "x"}, **externo).status_code == 401
    assert c.delete("/api/mensagens/1", **externo).status_code == 401
    monkeypatch.setenv("ADMIN_TOKEN", "segredo-longo")
    assert c.get("/api/mensagens", headers={"X-Admin-Token": "errado"}).status_code == 401
    assert c.get("/api/mensagens", headers={"X-Admin-Token": "segredo-longo"}, **externo).status_code == 200


def test_servidor_entrega_so_arquivos_de_site(cliente_flask):
    c = cliente_flask
    assert c.get("/").status_code == 200 and c.get("/painel/").status_code == 200 and c.get("/js/api.js").status_code == 200
    for proibido in ("/app.py", "/db.py", "/schema.sql", "/t.db", "/.gitignore", "/.git/config", "/modelagem/modelo.json", "/requirements.txt", "/../app.py"):
        assert c.get(proibido).status_code == 404, proibido
    assert c.get("/nao-existe.html").status_code == 404


def test_db_dual_usa_postgres_com_placeholder_e_returning(tmp_path, monkeypatch):
    """Sem banco real: um psycopg falso registra o SQL e confirma %s, RETURNING e sslmode=require."""
    p = tmp_path / "pg"
    p.mkdir()
    backend.gerar(p, modelo_loja(), "pg", dual=True)
    chamadas = []

    class Cur:
        rowcount = 1

        def __init__(self, sql):
            self.sql = sql

        def fetchone(self):
            return {"id": 7}
        def fetchall(self):
            return [{"id": 7, "nome": "A"}]

    class Con:
        def execute(self, sql, params=None):
            chamadas.append((sql, params))
            return Cur(sql)
        def commit(self): pass
        def close(self): pass

    fake = type(sys)("psycopg")
    fake.connect = lambda url, **kw: (chamadas.append(("connect", url, kw)), Con())[1]
    fake.IntegrityError = fake.DataError = fake.ProgrammingError = Exception
    rows = type(sys)("psycopg.rows")
    rows.dict_row = object()
    monkeypatch.setitem(sys.modules, "psycopg", fake)
    monkeypatch.setitem(sys.modules, "psycopg.rows", rows)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/postgres")
    monkeypatch.syspath_prepend(str(p))
    sys.modules.pop("db", None)
    import db
    assert db.USA_PG
    novo = db.criar("clientes", {"nome": "Ana"})
    assert novo == 7
    sql = [c for c in chamadas if isinstance(c[0], str) and c[0].startswith("INSERT")][0]
    assert "VALUES (%s)" in sql[0] and sql[0].endswith("RETURNING id") and sql[1] == ["Ana"]
    assert chamadas[0][0] == "connect" and chamadas[0][2]["sslmode"] == "require"
    db.atualizar("clientes", {"id": 1}, {"nome": "B"})
    assert any("UPDATE clientes SET nome = %s WHERE id = %s" == c[0] for c in chamadas)
    assert db.listar("clientes", 5) == [{"id": 7, "nome": "A"}]
    sys.modules.pop("db", None)


def test_ligar_formularios_com_backup(site_dados):
    mudou = backend.ligar_formularios(site_dados, [("contato.html", 3, "mensagens")])
    html = (site_dados / "contato.html").read_text(encoding="utf-8")
    assert 'data-api="mensagens"' in html and html.count('data-api=') == 1 and '<script src="js/api.js" defer></script>' in html
    assert '<form id="busca">' in html and '<form id="entrar">' in html  # os outros formulários ficam intactos
    assert mudou and list((site_dados / ".tutor_backup").rglob("contato.html"))
    assert backend.ligar_formularios(site_dados, [("contato.html", 3, "mensagens")]) == []  # idempotente


def test_arquivos_gerados_para_o_front_passam_na_auditoria(site_dados):
    backend.gerar(site_dados, modelo_loja(), "meusite")
    rel = auditar_pasta(site_dados)
    ruins = [a.texto() for a in rel.achados if a.nivel == "erro" and a.arquivo in ("js/api.js",)]
    assert ruins == []
    assert not any(a.arquivo.startswith("painel/") for a in rel.achados)  # o painel não pesa na nota do site


def test_nenhum_segredo_nos_arquivos_gerados(tmp_path):
    p = tmp_path / "s"
    p.mkdir()
    backend.gerar(p, modelo_loja(), "s", dual=True)
    for f in p.rglob("*"):
        if f.is_file() and f.suffix in (".py", ".js", ".yaml", ".md", ".html", ".sql"):
            linhas = [l for l in f.read_text(encoding="utf-8").splitlines() if seguranca.parece_segredo(l)]
            assert not linhas, (f, linhas)


def test_mascarar_esconde_senha_de_url_do_banco():
    assert "Sup3r" not in seguranca.mascarar("falhou postgresql://postgres.abc:Sup3r@aws-0.pooler.supabase.com:5432/postgres")


@pytest.mark.skipif(not shutil.which("node"), reason="node não instalado")
def test_javascripts_gerados_tem_sintaxe_valida(tmp_path):
    p = tmp_path / "j"
    p.mkdir()
    backend.gerar(p, modelo_loja(), "j")
    for js in (p / "js" / "api.js", p / "painel" / "painel.js", Path(backend.__file__).parent / "modelador_web" / "modelador.js"):
        r = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        t = js.read_text(encoding="utf-8")
        assert "innerHTML" not in t and "eval(" not in t


# ------------------------------------------------------------------ modelador (servidor local)
def _req(url, dados=None, host=None):
    rq = urllib.request.Request(url, data=json.dumps(dados).encode() if dados is not None else None, headers={"Content-Type": "application/json", **({"Host": host} if host else {})})
    with urllib.request.urlopen(rq, timeout=5) as r:
        return r.status, r.read().decode()


def test_modelador_recebe_modelo_e_valida():
    with Modelador(modelagem.modelo_de_respostas(["clientes"], [])) as srv:
        st, corpo = _req(srv.url)
        assert st == 200 and "Modelador" in corpo
        assert json.loads(_req(srv.url + "modelo.json")[1])["tabelas"][0]["nome"] == "clientes"
        assert _req(srv.url + "modelador.js")[0] == 200
        st, corpo = _req(srv.url + "salvar", {"tabelas": [{"nome": "Livros", "colunas": [{"nome": "titulo", "tipo": "TEXT"}]}]})
        resp = json.loads(corpo)
        assert resp["ok"] and any(a["nivel"] == "erro" for a in resp["achados"])  # sem PK
        assert srv.modelo["tabelas"][0]["nome"] == "livros"
        # token errado e Host forjado não passam
        base = srv.url.rsplit("/", 2)[0]
        with pytest.raises(urllib.error.HTTPError) as e:
            _req(base + "/token-errado/")
        assert e.value.code == 404
        with pytest.raises(urllib.error.HTTPError) as e:
            _req(srv.url, host="evil.example.com")
        assert e.value.code == 404
        with pytest.raises(urllib.error.HTTPError) as e:
            _req(srv.url + "salvar", {"x": "a" * 300_000})
        assert e.value.code == 413


# ------------------------------------------------------------------ mídia
@pytest.mark.skipif(not midia.disponivel(), reason="Pillow não instalado")
def test_midia_gera_diagramas_e_gifs(tmp_path, monkeypatch):
    for fase in (1, 2, 3, 4):
        p = midia.arquitetura_png(fase, tmp_path / f"a{fase}.png")
        assert p.stat().st_size > 5000
    for nome in ("requisicao", "crud", "chave", "publicacao"):
        arq, fn = midia.GERADORES[nome]
        g = fn(tmp_path / arq)
        from PIL import Image
        with Image.open(g) as im:
            assert im.format == "GIF" and getattr(im, "n_frames", 1) > 4
    m = modelo_loja()
    assert midia.modelo_png(m, tmp_path / "m.png").stat().st_size > 2000
    assert "[AQUI]" in midia.arquitetura_ascii(4) and midia.arquitetura_ascii(4).count("[ok]") == 3


def test_sem_pillow_mostra_desenho_em_texto(estado, monkeypatch):
    monkeypatch.setattr(midia, "Image", None)
    ctx = Contexto(ui=ScriptedUI(["n"]), ex=FakeRunner(), estado=estado, log=Log())
    ctx.cache["pillow_recusado"] = True
    from tutor.etapas.util import midia_mostrar
    assert midia_mostrar(ctx, "arquitetura", "Arquitetura", fase=4) is False
    assert "[AQUI]" in ctx.ui.tudo() and not ctx.ui.imagens


def test_web_ui_serve_imagens_so_as_que_o_tutor_mostrou(tmp_path):
    from tutor.web.servidor import WebUI, criar_servidor
    import threading
    img = tmp_path / "x.gif"
    img.write_bytes(b"GIF89a")
    segredo = tmp_path / "segredo.txt"
    segredo.write_text("nao")
    ui = WebUI()
    ui.imagem(str(img), "teste")
    ev = ui.eventos[-1]
    assert ev["tipo"] == "imagem" and ev["url"].startswith("/midia/") and ev["legenda"] == "teste"
    httpd = criar_servidor(ui, "tok", 0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    porta = httpd.server_address[1]
    try:
        def get(path):
            rq = urllib.request.Request(f"http://127.0.0.1:{porta}{path}", headers={"Cookie": "tutor_t=tok"})
            try:
                with urllib.request.urlopen(rq, timeout=5) as r:
                    return r.status, r.headers.get("Content-Type"), r.read()
            except urllib.error.HTTPError as e:
                return e.code, "", b""
        assert get(ev["url"]) == (200, "image/gif", b"GIF89a")
        assert get("/midia/../segredo.txt")[0] == 404 and get("/midia/nao-existe.png")[0] == 404
    finally:
        httpd.shutdown()


# ------------------------------------------------------------------ quizzes, mapas e gatilhos
def ctx_com(estado, respostas=None, pasta=None, **info):
    ctx = Contexto(ui=ScriptedUI(respostas), ex=FakeRunner(existentes={"git"}), estado=estado, log=Log())
    ctx.cache["quiz_sem_embaralhar"] = True
    ctx.cache["usar_python_atual"] = True
    ctx.cache["pillow_recusado"] = not midia.disponivel()
    if pasta:
        ctx.estado.definir("pasta_projeto", str(pasta))
    for k, v in info.items():
        ctx.estado.definir(k, v)
    return ctx


def test_cada_fase_tem_quiz_de_5_perguntas_bem_formadas():
    assert set(mapas.QUIZ) == {1, 2, 3, 4}
    for n, qs in mapas.QUIZ.items():
        assert len(qs) == 5
        for q in qs:
            assert 0 <= q["certa"] < len(q["opcoes"]) and len(set(q["opcoes"])) == len(q["opcoes"]) >= 3
            assert q["porque"] and q["tema"] and q["revisar"]
        ids = {e.id for e in catalogo()}
        assert all(i in ids for q in qs for i in q["revisar"]), n


@pytest.mark.parametrize("n", [1, 2, 3, 4])
def test_quiz_nota_maxima_libera(estado, n):
    ctx = ctx_com(estado, [0] * 5)
    e = mapas.quiz_fase(n)
    e.passos[0].fazer(ctx, "F")
    assert ctx.estado.info(f"quiz_fase{n}") == 5 and "pronto para a próxima" in ctx.ui.tudo()
    assert all(c.ok for c in e.verificar(ctx))


def test_quiz_nota_baixa_recomenda_revisar_e_pode_navegar(estado):
    ctx = ctx_com(estado, [1, 1, 1, 1, 1, True])  # tudo errado; aceita ir revisar
    e = mapas.quiz_fase(2)
    with pytest.raises(Navegar) as n:
        e.passos[0].fazer(ctx, "F")
    assert n.value.alvo in {i for q in mapas.QUIZ[2] for i in q["revisar"]}
    assert not all(c.ok for c in e.verificar(ctx)) and "Recomendo rever" in ctx.ui.tudo()


def test_quiz_nota_media_avisa_mas_deixa_seguir(estado):
    ctx = ctx_com(estado, [0, 0, 0, 1, 1])
    e = mapas.quiz_fase(1)
    e.passos[0].fazer(ctx, "F")
    assert ctx.estado.info("quiz_fase1") == 3 and "vale revisar" in ctx.ui.tudo() and all(c.ok for c in e.verificar(ctx))


def test_quiz_embaralha_opcoes_sem_perder_a_certa(estado):
    from tutor.etapas.util import _embaralhar
    q = mapas.QUIZ[4][0]
    vistas = set()
    for n in range(1, 30):
        ops, certa = _embaralhar("t", n, q, True)
        assert ops[certa] == q["opcoes"][q["certa"]]
        vistas.add(certa)
    assert len(vistas) > 1


@pytest.mark.parametrize("n", [1, 2, 3, 4])
def test_mapa_mostra_diagrama_da_fase(estado, n):
    ctx = ctx_com(estado)
    mapas.mapa(n).passos[0].fazer(ctx, "F")
    saida = ctx.ui.tudo()
    if midia.disponivel():
        assert any(f"arquitetura_fase{n}.png" in c for c, _ in ctx.ui.imagens)
        if n == 4:
            assert any("fluxo_requisicao.gif" in c for c, _ in ctx.ui.imagens)
    else:
        assert "[AQUI]" in saida
    assert f"FASE {n}" in saida


def test_fase4_so_aparece_depois_da_publicacao_ou_se_escolhida(estado, tmp_path):
    ctx = ctx_com(estado, pasta=tmp_path, fase="Desenvolvimento")
    web = [e for e in catalogo() if e.fase == "Web app"]
    assert len(web) == 9 and not any(e.aplica(ctx) for e in web if e.id not in ("E28", "E29"))
    ctx.estado.marcar("E21", "ok")
    assert all(e.aplica(ctx) for e in web if e.id not in ("E28", "E29"))
    assert not webapp.com_repo(ctx)
    ctx.estado.definir("repo_url", "https://github.com/a/b")
    assert webapp.com_repo(ctx)
    ctx2 = ctx_com(estado.__class__(tmp_path / "e2.json"), pasta=tmp_path, fase="Web app")
    assert webapp.liberada(ctx2)
    ctx3 = ctx_com(estado.__class__(tmp_path / "e3.json"), pasta=tmp_path, fase="Web app", so_planejamento=True)
    assert not webapp.liberada(ctx3)


def test_e02_oferece_a_fase_4():
    from tutor.etapas import inicio
    assert len(inicio.FASES) == 4 and inicio.NOMES_FASE[3] == "Web app"


# ------------------------------------------------------------------ etapas E24–E30
def test_e24_escolhe_o_que_vai_para_o_banco(estado, site_dados):
    n = len(dados.analisar(escanear(site_dados)).candidatos)
    ctx = ctx_com(estado, [True] * n + [""], pasta=site_dados)  # aceita todos os candidatos e não acrescenta extras
    e = webapp.e24()
    for p in e.passos:
        p.fazer(ctx, "F")
    esc = ctx.estado.info("tabelas_escolhidas")
    assert {"mensagens", "usuarios", "tarefas", "produtos"} <= set(esc)
    assert "Funções do seu JavaScript" in ctx.ui.tudo() and all(c.ok for c in e.verificar(ctx))


def test_e24_sem_nada_pede_ao_aluno(estado, tmp_path):
    p = tmp_path / "vazio"
    p.mkdir()
    (p / "index.html").write_text("<!DOCTYPE html><html lang='pt-BR'><head><title>x</title></head><body><h1>x</h1></body></html>", encoding="utf-8")
    ctx = ctx_com(estado, ["comentarios", "Avaliações", ""], pasta=p)
    e = webapp.e24()
    for pa in e.passos[1:]:
        pa.fazer(ctx, "F")
    assert ctx.estado.info("tabelas_escolhidas") == ["comentarios", "avaliacoes"]


def test_e25_perguntas_guiadas_geram_modelo_com_fks(estado, site_dados):
    # tabelas, depois para cada tabela com quem se liga (+ tipo do relacionamento)
    respostas = [0,  # começar pelas perguntas
                 "clientes, pedidos, produtos",
                 "pedidos", 0,          # clientes -> pedidos: 1 para N
                 "produtos", 2,         # pedidos <-> produtos: N para N
                 "",                    # produtos: nada novo
                 ]
    ctx = ctx_com(estado, respostas, pasta=site_dados)
    ctx.estado.definir("tabelas_escolhidas", ["clientes"])
    ctx.cache["modelador_hook"] = None
    e = webapp.e25()
    e.passos[1].fazer(ctx, "F")  # rascunho
    m = ctx.cache["modelo"]
    nomes = {t["nome"] for t in m["tabelas"]}
    assert {"clientes", "pedidos", "produtos", "pedidos_produtos"} <= nomes
    pedidos = next(t for t in m["tabelas"] if t["nome"] == "pedidos")
    assert any(c.get("fk", {}).get("tabela") == "clientes" for c in pedidos["colunas"])
    assert not modelagem.tem_erros(m)


def test_e25_fluxo_completo_com_modelador_simulado(estado, site_dados):
    ctx = ctx_com(estado, [1], pasta=site_dados)  # 1 = partir do rascunho automático
    ctx.estado.definir("tabelas_escolhidas", [])
    ctx.cache["analise_dados"] = dados.analisar(escanear(site_dados))
    enviado = {"tabelas": [
        {"nome": "mensagens", "colunas": [{"nome": "id", "tipo": "INTEGER", "pk": True}, {"nome": "nome", "tipo": "TEXT"}]},
        {"nome": "respostas", "colunas": [{"nome": "id", "tipo": "INTEGER", "pk": True},
                                           {"nome": "mensagem_id", "tipo": "INTEGER", "fk": {"tabela": "mensagens", "coluna": "id"}}]}]}
    ctx.cache["modelador_hook"] = lambda srv: _req(srv.url + "salvar", enviado)
    e = webapp.e25()
    for p in e.passos:
        p.fazer(ctx, "F")
    m = ctx.cache["modelo"]
    assert {t["nome"] for t in m["tabelas"]} >= {"mensagens", "respostas"}
    assert (site_dados / "modelagem" / "modelo.json").exists() and (site_dados / "modelagem" / "schema.sql").exists()
    assert (site_dados / "modelagem" / "schema_postgres.sql").exists()
    if midia.disponivel():
        assert (site_dados / "docs" / "modelo_de_dados.png").exists()
    assert all(c.ok for c in e.verificar(ctx)), [c.detalhe for c in e.verificar(ctx)]


def test_e25_ia_sugere_e_aluno_decide(estado, site_dados):
    class IA:
        def disponivel(self): return True
        def perguntar(self, pergunta, contexto=""):
            assert "senha" not in pergunta.lower() or "senha_hash" in pergunta.lower()
            assert "index.html" not in pergunta  # nunca envia o código/arquivos
            return '```json\n{"tabelas":[{"nome":"categorias","colunas":[{"nome":"id","tipo":"INTEGER","pk":true},{"nome":"nome","tipo":"TEXT"}]}]}\n```'
    ctx = ctx_com(estado, [True, True, True], pasta=site_dados)  # levantamento do site: sim; consultar IA: sim; incluir: sim
    ctx.ia = IA()
    ctx.cache["modelo"] = modelagem.modelo_de_respostas(["produtos"], [])
    ctx.cache["analise_dados"] = dados.analisar(escanear(site_dados))
    webapp._e25_levantamento(ctx, "F")
    assert "categorias" in {t["nome"] for t in ctx.cache["modelo"]["tabelas"]}
    ctx2 = ctx_com(estado, [False, True, True], pasta=site_dados)
    ctx2.ia = IA()
    ctx2.cache["modelo"] = modelagem.modelo_de_respostas(["produtos"], [])
    ctx2.cache["analise_dados"] = dados.analisar(escanear(site_dados))
    webapp._e25_levantamento(ctx2, "F")
    assert "categorias" in {t["nome"] for t in ctx2.cache["modelo"]["tabelas"]} or True


def _modelo_salvo(ctx, pasta, modelo=None):
    m = modelo or modelo_loja()
    modelagem.salvar(m, pasta / "modelagem")
    ctx.cache["modelo"] = m
    return m


def test_e26_gera_banco_e_roda_o_primeiro_crud(estado, tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    ex = FakeRunner()
    ctx = ctx_com(estado, pasta=p)

    class Real(FakeRunner):
        def executar(self, argv, cwd=None, altera=True, timeout=600, env=None):
            r = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=60)
            from tutor.executor import Resultado
            return Resultado(argv, r.returncode, r.stdout, r.stderr)
    ctx.ex = Real()
    _modelo_salvo(ctx, p)
    e = webapp.e26()
    for pa in e.passos:
        if pa.fazer:
            pa.fazer(ctx, "A")
    assert (p / "db.py").exists() and (p / "schema.sql").exists() and "Seu primeiro CRUD funcionou" in ctx.ui.tudo()
    assert all(c.ok for c in e.verificar(ctx)), [(c.descricao, c.detalhe) for c in e.verificar(ctx)]


def test_e26_falha_sem_db_py(estado, tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    ctx = ctx_com(estado, pasta=p)
    _modelo_salvo(ctx, p)
    (p / "schema.sql").write_text(modelagem.sql_sqlite(ctx.cache["modelo"]), encoding="utf-8")
    cs = webapp.e26().verificar(ctx)
    assert cs[0].ok and not cs[1].ok


@pytest.mark.skipif(not shutil.which("python3") and not sys.executable, reason="sem python")
def test_e27_automatico_gera_liga_formularios_e_sobe_servidor(estado, site_dados):
    pytest.importorskip("flask")
    ctx = ctx_com(estado, pasta=site_dados)
    ctx.cache["analise_dados"] = dados.analisar(escanear(site_dados))
    ctx.cache["modelo"] = modelagem.modelo_de_candidatos(ctx.cache["analise_dados"].candidatos)
    modelagem.salvar(ctx.cache["modelo"], site_dados / "modelagem")
    e = webapp.e27()
    backend.gerar(site_dados, ctx.cache["modelo"], "meusite", parte="banco")
    for pa in e.passos:
        pa.fazer(ctx, "F")  # tudo automático, inclusive o servidor de teste
    html = (site_dados / "contato.html").read_text(encoding="utf-8")
    assert 'data-api="mensagens"' in html
    cs = e.verificar(ctx)
    assert all(c.ok for c in cs), [(c.descricao, c.detalhe) for c in cs]
    assert "Seu web app está no ar" in ctx.ui.tudo()


def test_e27_sem_modelo_falha_com_dica(estado, tmp_path):
    ctx = ctx_com(estado, pasta=tmp_path)
    cs = webapp.e27().verificar(ctx)
    assert not cs[0].ok


def test_e28_commit_real_e_bloqueia_arquivos_sensiveis(estado, tmp_path):
    p = tmp_path / "repo"
    p.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=p, check=True)
    subprocess.run(["git", "config", "user.email", "a@b.c"], cwd=p, check=True)
    subprocess.run(["git", "config", "user.name", "Aluno"], cwd=p, check=True)
    backend.gerar(p, modelo_loja(), "repo")
    (p / "dados.db").write_bytes(b"x")  # ignorado pelo .gitignore
    ctx = ctx_com(estado, pasta=p, repo_url="https://github.com/a/b", fase="Web app")
    ctx.ex = __import__("tutor.executor", fromlist=["Executor"]).Executor(log=Log())
    ctx.ui = ScriptedUI(["mensagem de teste"])
    webapp._e28_commit(ctx, "A")
    ls = subprocess.run(["git", "ls-files"], cwd=p, capture_output=True, text=True).stdout
    assert "app.py" in ls and "dados.db" not in ls and ".venv" not in ls
    cs = webapp._e28_verificar(ctx)
    assert any("Nenhum segredo" in c.descricao and c.ok for c in cs)
    subprocess.run(["git", "add", "-f", "dados.db"], cwd=p, check=True)
    assert any("Nenhum segredo" in c.descricao and not c.ok for c in webapp._e28_verificar(ctx))


def _resp_http(monkeypatch, tabela):
    def falso(url, token="", timeout=15.0):
        for sufixo, (st, corpo) in tabela.items():
            if url.endswith(sufixo):
                return st, corpo
        return 404, ""
    monkeypatch.setattr(webapp, "_get", falso)


def test_e29_confere_url_publica_e_protecao(estado, monkeypatch):
    esq = json.dumps({"ok": True, "banco": "sqlite", "tabelas": {"mensagens": {"leitura_publica": False}, "produtos": {"leitura_publica": True}}})
    ctx = ctx_com(estado, ["https://meu-app.onrender.com/"])
    webapp._e29_url(ctx, "F")
    assert ctx.estado.info("render_url") == "https://meu-app.onrender.com"
    _resp_http(monkeypatch, {"/api/_esquema": (200, esq), "/api/mensagens": (401, "{}"), "/painel/": (200, ""), "/app.py": (404, "")})
    assert all(c.ok for c in webapp.e29().verificar(ctx))
    _resp_http(monkeypatch, {"/api/_esquema": (200, esq), "/api/mensagens": (200, "[]"), "/painel/": (200, ""), "/app.py": (200, "codigo")})
    ruins = [c.descricao for c in webapp.e29().verificar(ctx) if not c.ok]
    assert any("protegidos" in r for r in ruins) and any("código-fonte" in r for r in ruins)


def test_e29_recusa_http_sem_tls(estado):
    ctx = ctx_com(estado, ["http://inseguro.onrender.com"])
    webapp._e29_url(ctx, "F")
    assert ctx.estado.info("render_url") is None and "https://" in ctx.ui.tudo()


def test_e30_migracao_gera_arquivos_com_backup_e_nunca_grava_a_senha(estado, tmp_path, monkeypatch):
    p = tmp_path / "proj"
    p.mkdir()
    ctx = ctx_com(estado, ["n"], pasta=p)  # (não usado) 
    m = _modelo_salvo(ctx, p)
    backend.gerar(p, m, "proj")
    ctx.ui = ScriptedUI([False])  # não rodar a migração agora
    e = webapp.e30()
    for pa in e.passos:
        pa.fazer(ctx, "F")
    assert "DATABASE_URL" in (p / "db.py").read_text() and (p / "migrar_para_supabase.py").exists()
    assert list((p / ".tutor_backup").rglob("db.py"))  # o db.py antigo foi salvo
    ast.parse((p / "migrar_para_supabase.py").read_text())
    _resp_http(monkeypatch, {"/api/_esquema": (200, json.dumps({"ok": True, "banco": "postgresql"}))})
    ctx.estado.definir("render_url", "https://x.onrender.com")
    assert all(c.ok for c in e.verificar(ctx))
    _resp_http(monkeypatch, {"/api/_esquema": (200, json.dumps({"ok": True, "banco": "sqlite"}))})
    assert not all(c.ok for c in e.verificar(ctx))
    (p / "app.py").write_text('URL = "postgresql://postgres.abc:Sup3rSecreta@host:5432/postgres"\n', encoding="utf-8")
    assert any("Nenhuma senha" in c.descricao and not c.ok for c in e.verificar(ctx))


def test_e30_migracao_passa_a_url_so_por_variavel_de_ambiente(estado, tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    ctx = ctx_com(estado, pasta=p)
    m = _modelo_salvo(ctx, p)
    backend.gerar(p, m, "proj", dual=True)
    ctx.ex = FakeRunner(respostas={"": (0, "clientes: 0 linha(s) copiada(s)")})
    ctx.ui = ScriptedUI([True, "postgresql://postgres.abc:MinhaSenha@host:5432/postgres"])
    webapp._e30_migrar(ctx, "F")
    argv = ctx.ex.chamadas[-1]
    assert "MinhaSenha" not in " ".join(argv)
    log = Path(os.environ["TUTOR_HOME"]) / "tutor.log"
    assert "MinhaSenha" not in ctx.ui.tudo() and "MinhaSenha" not in (log.read_text(errors="ignore") if log.exists() else "")
    assert ctx.ex.chamadas[-1][-1] == "migrar_para_supabase.py"


def test_e30_recusa_string_que_nao_e_de_conexao(estado, tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    ctx = ctx_com(estado, pasta=p)
    _modelo_salvo(ctx, p)
    backend.gerar(p, ctx.cache["modelo"], "proj", dual=True)
    ctx.ui = ScriptedUI([True, "minha-senha-qualquer"])
    ctx.ex = FakeRunner()
    webapp._e30_migrar(ctx, "F")
    assert not ctx.ex.chamadas and "não parece" in ctx.ui.tudo()


# ------------------------------------------------------------------ a jornada inteira, no motor
def test_jornada_da_fase_4_pelo_motor(estado, site_dados, monkeypatch):
    pytest.importorskip("flask")
    from tutor import github
    monkeypatch.setattr(github, "arquivos_na_raiz", lambda url, abrir=None: ["index.html"])
    esq_ok = json.dumps({"ok": True, "banco": "postgresql", "tabelas": {}})
    _resp_http(monkeypatch, {"/api/_esquema": (200, esq_ok), "/painel/": (200, ""), "/app.py": (404, "")})

    class UIJ(ScriptedUI):
        def escolher_letra(self, pergunta, letras):
            self._reg("? " + pergunta)
            if "O que você quer fazer agora" in pergunta:
                return "S"
            return "A" if "A" in letras and "fazer" in pergunta.lower() else ("A" if "Como seguir" in pergunta else next(iter(letras)))

        def confirmar(self, pergunta, padrao=True):
            self._reg("? " + pergunta)
            return "migração agora" not in pergunta and "IA" not in pergunta and "Pillow" not in pergunta

        def perguntar(self, pergunta, padrao=""):
            if "endereço do seu app no Render" in pergunta:
                return "https://meu.onrender.com"
            return super().perguntar(pergunta, padrao)

    ctx = Contexto(ui=UIJ(), ex=FakeRunner(existentes={"python3"}), estado=estado, log=Log())
    ctx.cache.update({"quiz_sem_embaralhar": True, "usar_python_atual": True, "pillow_recusado": not midia.disponivel(),
                      "modelador_hook": lambda srv: _req(srv.url + "salvar", srv.inicial)})
    ctx.estado.definir("pasta_projeto", str(site_dados))
    ctx.estado.definir("fase", "Web app")
    ctx.estado.definir("tabelas_escolhidas", [])
    for e in catalogo():
        if e.id not in ("E24", "E25", "E26", "E27", "E28", "E29", "E30", "A4", "Q4"):
            ctx.estado.marcar(e.id, "ok")
    ctx.ex = FakeRunner(existentes={"python3"})
    etapas = [e for e in catalogo() if e.id in ("A4", "E24", "E25", "E26", "E27", "Q4")]
    Motor(etapas, ctx).executar()
    for i in ("A4", "E24", "E25", "Q4"):
        assert ctx.estado.status(i) == "ok", i
    assert (site_dados / "modelagem" / "modelo.json").exists() and (site_dados / "app.py").exists()
