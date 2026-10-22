"""Auditores de HTML, CSS, JS e publicação: site bom (starter) e site ruim (iniciante)."""
import urllib.error
import urllib.request

import pytest

from tutor.front import audit_js, cores, fixes, tokens
from tutor.front.auditoria import auditar_pasta, nota_categoria
from tutor.front.regras import REGRAS, achar
from tutor.front.servidor_local import ServidorPages
from tutor.front.site import escanear


def ids(pasta):
    return auditar_pasta(pasta).ids()


def test_regras_bem_formadas():
    assert len(REGRAS) >= 90
    for r in REGRAS.values():
        assert r.titulo and r.porque and r.como, r.id
        assert r.nivel in ("erro", "aviso", "dica")


def test_starter_tem_nota_maxima(site_bom):
    r = auditar_pasta(site_bom)
    assert r.geral == 100, [a.texto() for a in r.achados]
    assert r.contagem() == {"erro": 0, "aviso": 0, "dica": 0}
    assert all(n == 100 for n in r.notas.values())


def test_site_ruim_detecta_problemas_tipicos(aluno):
    achados = ids(aluno)
    esperados = {"H01", "H02", "H03", "H04", "H05", "H20", "H21", "C06", "C14", "J01", "J02", "J03", "J12",
                 "S02", "S03", "S04", "S08", "S09"}
    assert esperados <= achados, esperados - achados
    r = auditar_pasta(aluno)
    assert r.geral < 70 and r.contagem()["erro"] >= 8


def test_s03_maiusculas_diferentes(aluno):
    a = [x for x in auditar_pasta(aluno).achados if x.id == "S03"]
    assert a and "app.js" in a[0].detalhe


def test_s04_caminho_absoluto(aluno):
    a = [x for x in auditar_pasta(aluno).achados if x.id == "S04"]
    assert a and a[0].detalhe.startswith("/css/")


def test_sem_index_limita_nota(tmp_path):
    (tmp_path / "home.html").write_text("<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>x</title></head><body><main><h1>a</h1></main></body></html>")
    r = auditar_pasta(tmp_path)
    assert "S01" in r.ids() and r.geral <= 60


def test_categorias_sem_js_ficam_nao_aplicaveis(tmp_path):
    (tmp_path / "index.html").write_text("<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'><title>x</title></head><body><h1>a</h1></body></html>")
    r = auditar_pasta(tmp_path)
    assert r.notas["JavaScript"] is None


def test_pasta_vazia_nao_quebra(tmp_path):
    r = auditar_pasta(tmp_path)
    assert "S01" in r.ids() and 0 <= r.geral <= 60


def test_repeticao_do_mesmo_erro_pesa_pouco():
    um = [achar("H07", "a.html", 1)]
    trinta = [achar("H07", "a.html", i) for i in range(30)]
    assert nota_categoria(trinta) - nota_categoria(um) >= -10
    assert nota_categoria([]) == 100


def test_link_externo_e_ancora_ok(tmp_path):
    (tmp_path / "index.html").write_text(
        "<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>x</title></head>"
        "<body><main id='topo'><h1>a</h1><a href='https://exemplo.com' target='_blank' rel='noopener'>externo aqui</a> <a href='#topo'>ir ao topo</a>"
        "<a href='#nao'>quebrada</a></main></body></html>")
    a = [x.id for x in auditar_pasta(tmp_path).achados]
    assert "S05" in a and a.count("S02") == 0


# ------------------------------------------------------------------ JS
def test_js_limpar_ignora_strings_comentarios_e_regex():
    js = 'const t = "var x = 1; eval(1)"; // var y\n/* var z */ const r = /var \\d/; let s = `var ${1}`;'
    assert audit_js.auditar_arquivo("a.js", js) == []


def test_js_detecta_basicos():
    js = "var a = 1;\nif (a == 2) {}\neval('1');\nel.innerHTML = '<b>' + a;\n"
    i = {x.id for x in audit_js.auditar_arquivo("a.js", js)}
    assert {"J01", "J02", "J03", "J04"} <= i


def test_js_innerhtml_literal_e_seguro():
    i = {x.id for x in audit_js.auditar_arquivo("a.js", "el.innerHTML = '<b>fixo</b>';\n")}
    assert "J03" not in i


def test_js_parenteses_desbalanceados():
    i = {x.id for x in audit_js.auditar_arquivo("a.js", "function f( {\n  return 1;\n")}
    assert "J13" in i


def test_js_fetch_sem_tratamento_e_json_parse():
    js = "fetch('/api').then(r => r.json()).then(d => console.log(d));\nconst x = JSON.parse(localStorage.getItem('a'));\n"
    i = {x.id for x in audit_js.auditar_arquivo("a.js", js)}
    assert "J10" in i and "J11" in i
    seguro = "try { const x = JSON.parse(a); } catch { }\nfetch('/a').then(r => { if (!r.ok) throw 1; return r; }).catch(() => {});\n"
    i2 = {x.id for x in audit_js.auditar_arquivo("a.js", seguro)}
    assert "J10" not in i2 and "J11" not in i2


def test_js_funcao_longa():
    corpo = "\n".join(f"  console.info({n});" for n in range(60))
    i = {x.id for x in audit_js.auditar_arquivo("a.js", "function grande() {\n" + corpo + "\n}\n")}
    assert "J08" in i


# ------------------------------------------------------------------ CSS / cores / tokens
def test_contraste_wcag():
    assert round(cores.contraste((0, 0, 0), (255, 255, 255)), 1) == 21.0
    assert cores.contraste(cores.parse("#777777")[:3], (255, 255, 255)) > 4.4
    assert cores.contraste(cores.parse("#cccccc")[:3], (255, 255, 255)) < 2


@pytest.mark.parametrize("cor", ["#2563eb", "#ffcc00", "#e91e63", "#00ff00", "#888888", "#000000"])
def test_tokens_sempre_acessiveis(cor):
    for tema, v in tokens.paleta(cor).items():
        assert cores.contraste(cores.parse(v["primaria"])[:3], cores.parse(v["fundo"])[:3]) >= 4.5, (cor, tema)
        assert cores.contraste(cores.parse(v["sobre-primaria"])[:3], cores.parse(v["primaria"])[:3]) >= 4.5, (cor, tema)
        assert cores.contraste(cores.parse(v["texto-suave"])[:3], cores.parse(v["superficie"])[:3]) >= 4.5, (cor, tema)
    assert "prefers-color-scheme: dark" in tokens.css(cor)


def test_css_media_query_sem_viewport_e_largura_fixa(tmp_path):
    (tmp_path / "index.html").write_text("<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'><title>x</title><link rel='stylesheet' href='a.css'></head><body><h1>a</h1></body></html>")
    (tmp_path / "a.css").write_text(".c{width:1200px;float:left} .d{color:red!important;float:left} .e{margin:0!important;float:right} .f{padding:0!important;float:left}")
    i = ids(tmp_path)
    assert {"C01", "C09", "C15", "H04"} <= i


# ------------------------------------------------------------------ correções seguras
def test_corrigir_cabecalhos_com_backup(aluno):
    antes = auditar_pasta(aluno)
    site = escanear(aluno)
    feitos = fixes.corrigir_cabecalhos(aluno, site, antes)
    assert feitos and any("lang" in f for f in feitos)
    assert list((aluno / ".tutor_backup").rglob("index.html"))
    depois = auditar_pasta(aluno)
    assert not ({"H01", "H02", "H03", "H04", "H21"} & depois.ids())
    assert depois.geral > antes.geral
    # idempotente
    assert fixes.corrigir_cabecalhos(aluno, escanear(aluno), depois) == []


def test_arquivos_faltantes_nao_sobrescrevem(aluno):
    (aluno / "README.md").write_text("meu readme")
    criados = fixes.criar_arquivos_faltantes(aluno, escanear(aluno), "Aluno", "https://github.com/a/aluno")
    assert "README.md" not in criados and ".gitignore" in criados and "404.html" in criados
    assert (aluno / "README.md").read_text() == "meu readme"
    assert "https://a.github.io/aluno/" in (aluno / "sitemap.xml").read_text()


# ------------------------------------------------------------------ servidor modo GitHub Pages
def _get(url):
    try:
        with urllib.request.urlopen(url) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_servidor_prefixo_e_caso(site_bom):
    with ServidorPages(site_bom, "bom") as s:
        base = s.url
        assert _get(base)[0] == 200
        assert _get(base + "css/base.css")[0] == 200
        assert _get(base + "CSS/base.css")[0] == 404          # Linux diferencia maiúsculas
        assert _get(base.replace("/bom/", "/") + "css/base.css")[0] == 404  # sem o prefixo do repositório
        st, corpo = _get(base + "nao-existe")
        assert st == 404 and "Página não encontrada".encode() in corpo   # usa o 404.html do aluno
        assert _get(base + "..%2f..%2fetc/passwd")[0] == 404


def test_site_ruim_quebra_no_modo_pages(aluno):
    with ServidorPages(aluno, "aluno") as s:
        assert _get(s.url + "js/App.js")[0] == 404 and _get(s.url + "js/app.js")[0] == 200
