# Checklist — Tutor Front (sites estáticos, sem banco)
Material do Drive lido: 2-HTML, 2.1-CSS, 3-Design responsivo (Bootstrap), Java Script (completo), JS Relâmpago, Links externos, 1-Introdução (React ignorado: fora do escopo estático).

## Estrutura
- [x] 1. Derivar projeto de tutor_projeto → tutor_front (estado em ~/.tutor_front, entrada tutor_front.py)
- [x] 2. Remover: banco/CRUD/Flask/Render/Supabase/POO-python (etapas, geradores, testes)
- [x] 3. Módulos novos `tutor/front/`: htmlparse, audit_html, audit_css, audit_js, audit_site, audit_a11y_seo, audit_perf, score, tokens, starter, seo_gen, pages, servidor_local, docgen_front
- [x] 4. Etapas novas (catálogo) — ver mapa-etapas.md
- [x] 5. Referências (MDN, web.dev, W3C, GitHub Pages…) + material do professor mapeado por etapa
- [x] 6. UI web: botão "ver meu site" (servidor local), placar de qualidade, glossário front
- [x] 7. Testes pytest (auditores com sites bons/ruins, starter passa 100%, base-path/case, Pages mock, navegador opcional)
- [x] 8. README, mapa-etapas, checklist final, zip, relatório

## Progresso detalhado (atualizado)
- [x] htmlparse, cores, regras (98), site, audit_html, audit_css, audit_js, audit_site, auditoria (notas), tokens, starter (nota 100; testado no Chromium 320/768/1280 sem overflow nem erro de console)
- [x] pages.py, servidor_local.py (modo GitHub Pages), navegador.py (Playwright opcional), docgen_front.py, seo_gen para sites existentes
- [x] Reescrever: etapas/__init__, util, inicio, repositorio, web + novas etapas front; cli, ia.recomendar, docgen
- [x] referencias.json, glossário/UI web (placar, ver site), testes, README, mapa-etapas, zip, relatório

## Ajuste de layout (navegação e fases)
- [x] Caixa de interação não cobre mais o texto: rolagem interna (#rolagem) + painel fixo abaixo
- [x] Trilha de fases (chips) + menu lateral agrupado por fase com contagem e IDs de etapa
- [x] Etapas que não se aplicam ocultas (toggle "Mostrar etapas que não se aplicam") e sem mensagens no container principal
- [x] Testes: 90 ok (py3.10/3.13), Playwright 1280/390 px sem erros nem overflow

## Fase 4 · Do estático ao web app (pedido 11:59)
- [x] 1 Ler código existente (motor, etapas, ui, util.quiz, fase do projeto)
- [x] 2 Mídia: PIL opcional, diagramas de arquitetura por fase, GIFs; suporte a imagens na UI web/terminal
- [x] 3 Análise do projeto: identificar formulários/funções candidatos a banco
- [x] 4 Modelagem: perguntas guiadas + mini app modelador (HTML) + validação PK/FK + IA opcional
- [x] 5 SQLite: schema.sql, db.py, primeiro CRUD baseado no código do aluno
- [x] 6 Flask automático (venv, pip, app.py, API, rodar local)
- [x] 7 GitHub atualizar + Render (render.yaml) + Supabase (migração)
- [x] 8 Quiz de 5 questões por fase + avaliação de prontidão
- [x] 9 Registrar etapas no catálogo, fase no E02, testes, docs, zip
- [x] Verificação final: 146 testes (py3.13) e 140+6 ignorados (py3.10); modelador e web UI conferidos no Chromium (1280/390 px)
