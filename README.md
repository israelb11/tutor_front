# Tutor Front

Leva um **site estático** (HTML, CSS e JavaScript) do código até a publicação **gratuita no GitHub Pages** e, na **Fase 4**, transforma-o em **web app** (Flask + SQLite, publicado no Render, com migração para o Supabase),
com foco em páginas bem construídas, layout responsivo, boas práticas de design/acessibilidade e JavaScript de qualidade.
Só biblioteca padrão do Python 3.10+ (Playwright/Node são opcionais).

## Como usar
```
python3 tutor_front.py            # terminal
python3 tutor_front.py --web      # navegador (recomendado para iniciantes)
python3 tutor_front.py --lista    # etapas e progresso
python3 tutor_front.py --dry-run  # mostra sem alterar nada
python3 tutor_front.py --reset    # recomeça
```
O progresso fica em `~/.tutor_front/` (estado, checklist.md, historico_qualidade.json, log).

## O que o tutor faz
- **IA opcional primeiro (E00)**: ensina a criar a chave grátis do Gemini (AI Studio → projeto → *Create API key*). Com ela, `[?]` responde dúvidas em qualquer etapa e as etapas de qualidade oferecem a IA para explicar os problemas encontrados (trechos com segredos nunca são enviados). Sem chave, tudo funciona igual.
- **Raio-X (E05)**: audita o site em 8 categorias e dá nota de 0 a 100 (HTML, CSS, Responsivo, Acessibilidade, SEO, JavaScript, Desempenho, Publicação). Cada problema vem com *por quê* e *como corrigir*.
- **Etapas de qualidade (E12–E18)**: uma área por etapa, com diagnóstico, correções seguras, mini-quiz e links (MDN, web.dev, W3C e o material do professor no Drive).
- **Site inicial (E04)**: se o aluno não tem código, o tutor gera um site responsivo e acessível (4 páginas, tema claro/escuro, menu acessível, formulário validado, lista de tarefas com localStorage) que tira 100 na própria auditoria.
- **Teste em modo GitHub Pages (E19)**: servidor local que imita o GitHub (prefixo `/repositorio/`, maiúsculas/minúsculas exatas, `404.html`) e, se houver Playwright, teste em Chromium real a 320/768/1280 px.
- **Publicação (E20–E21)**: commit/push, passo a passo do *Settings → Pages* e verificação do endereço com novas tentativas.
- **Depois (E22–E23)**: Lighthouse, domínio próprio, alternativas (Netlify, Cloudflare Pages, Vercel) e documentação técnica (`docs/DOCUMENTACAO.md`, `docs/QUALIDADE.md`).
- Herdado: fase do projeto (planejamento/desenvolvimento/implantação), PDF de requisitos, conta e repositório no GitHub, ambiente sem permissão (modo só execução ou VM com Geany), IA opcional (Gemini).

### Fase 4 · Do estático ao web app (E24–E30)
Numerada como Fase 4 porque Implantação já era a Fase 3. Libera-se ao concluir a publicação no Pages (ou ao escolhê-la no E02).
- **E24 Análise**: acha no *seu* código formulários, `localStorage`, listas em JS, `fetch('*.json')` e funções que parecem C/R/U/D, e sugere tabelas.
- **E25 Modelagem**: perguntas guiadas (tabelas, PK, FK, relações 1:N / N:N), rascunho automático ou **mini app de modelagem** (página local em 127.0.0.1, clicar e arrastar; valida PK/FK e mostra o SQL). IA opcional recebe só nomes de tabelas/colunas. Gera `modelagem/modelo.json`, `schema.sql`, `schema_postgres.sql` e `docs/modelo_de_dados.png`.
- **E26 SQLite + primeiro CRUD** com GIFs; **E27 Flask automático** (venv, pip, `app.py`, API `/api/<tabela>`, `js/api.js`, `/painel/`, formulários ligados com confirmação); **E28 GitHub**; **E29 Render** (`render.yaml`); **E30 Supabase** (`db.py` duplo SQLite/PostgreSQL, script de migração, RLS ligado).
- **Mapas A1–A4** (diagrama da arquitetura com a fase atual em destaque) e **quizzes Q1–Q4** (5 questões por fase; nota ≥ 4 = pronto, 3 = vale revisar, ≤ 2 = recomenda rever e leva às etapas indicadas).
- **Imagens e GIFs** gerados com Pillow (opcional: sem ele, o tutor usa desenho em texto). Na interface web só são servidas imagens registradas pelo tutor.
- Segurança do back-end gerado: SQL sempre com parâmetros e nomes de tabela/coluna de lista fixa; senhas só como hash; `ADMIN_TOKEN` para listar/editar tabelas privadas; `DATABASE_URL` só como variável de ambiente (nunca no código nem no GitHub); arquivos do servidor (`app.py`, `.db`, `.env`) não são servidos.

Veja `mapa-etapas.md`. Em cada etapa: **[F]** fazer sozinho · **[A]** ajuda · pular, voltar, repetir, perguntar à IA, sair.

## Interface web (--web)
- **Menu superior** sempre ativo: ◀ Anterior, Próxima ▶ (segue sem concluir), 🔄 Fase (refaz a escolha de fase), 📖 Glossário, ⏻ Fechar; no celular, ☰ Etapas.
- **Trilha de fases** (acima do texto) e **menu lateral esquerdo** agrupado por fase (Preparação, Fase 1 Planejamento, Fase 2 Desenvolvimento, Fase 3 Implantação, Fase 4 Web app) com contagem de etapas feitas. Etapas que não se aplicam ao seu projeto ficam ocultas (marque "Mostrar etapas que não se aplicam" para vê-las).
- A área de texto rola sozinha; a caixa de interação fica fixa abaixo e nunca cobre o conteúdo.
- **Menu lateral direito**: botões de ação compactos (Eu faço, Faça por mim, Pular, Ver de novo, Voltar, Lista, IA, Salvar e sair). Em telas estreitas vira uma barra inferior.
- Ao chegar ao fim da lista o tutor **não encerra**: pergunta se o aluno quer escolher uma etapa, mudar de fase ou sair. Etapas que não se aplicam à fase atual não ficam mais marcadas como "puladas".

## Segurança e princípios
- O código do aluno **nunca é reescrito**. O tutor só cria arquivos novos (README, .gitignore, robots, sitemap, favicon, 404, tokens.css, docs) e, com autorização `SIM`, ajusta o cabeçalho do HTML (doctype, lang, charset, viewport, defer) guardando cópia em `.tutor_backup/`.
- Nunca roda como root; passos que alteram algo pedem `SIM`. Senha de sudo só em memória; segredos mascarados no log.
- Interface web só em 127.0.0.1, com token, cookie HttpOnly, checagem de Host/Origin e CSP.
- A auditoria alerta para chaves de API no JavaScript (tudo no front-end é público).

## Testes
`pip install -r requirements-dev.txt && python3 -m pytest -q` (o teste de VM real exige `--vm`; o teste em navegador usa Playwright se instalado).

## Limitações
- GitHub Pages gratuito: apenas repositório **público**, site até 1 GB, ~100 GB/mês de tráfego (soft), 10 builds/hora (soft). Só arquivos estáticos.
- A auditoria é estática (leitura de arquivos): ela não executa o JavaScript nem calcula contraste de imagens, gradientes ou estilos aplicados por script. Não substitui o Lighthouse (E22) nem um teste com leitor de tela.
- Contraste: calculado só para pares `color`/`background` declarados na mesma regra (com variáveis CSS resolvidas no tema claro).
- Login/push no GitHub, VM real e a ativação do Pages só foram testados com simulações/repositório local; a verificação do endereço público usa o site real apenas quando o aluno publica.
- Render gratuito: o app dorme após ~15 min sem uso (acorda em ~1 min) e o **disco é efêmero** (um SQLite no Render perde os dados a cada deploy: por isso a migração para o Supabase). Supabase gratuito: 500 MB, 2 projetos, pausa após 1 semana sem uso; use o *Session pooler* (IPv4).
- Formulários de login/senha não são ligados automaticamente (exigem sessão e autenticação, fora do escopo).
- Testes do Render/Supabase usam respostas simuladas; o fluxo real só roda quando o aluno publica.
- Links de referência (`referencias.json`) e o nome do modelo Gemini podem mudar. React (apostila 5) ficou fora do escopo (não é site estático puro).
