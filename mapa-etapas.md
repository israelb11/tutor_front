# Mapa de etapas — Tutor Front

Cada etapa segue o padrão: **[F] fazer sozinho** (o tutor confere) ou **[A] ajuda** (o tutor faz e explica). Verificação com **erro** bloqueia; **avisos e dicas** aparecem como sugestão e não bloqueiam. Toda falha oferece corrigir, aceitar ou sair.

| Id | Fase | Título | Objetivo | Material do professor |
|---|---|---|---|---|
| E00 | Início | IA opcional: pegar a chave grátis do Gemini | Criar (se quiser) uma chave gratuita do Google Gemini para ter ajuda de IA em todas as etapas. | — |
| E01 | Início | Preparar o tutor | Conferir se o computador tem o básico para o tutor funcionar. | — |
| E02 | Início | Em qual fase do projeto você está? | Saber onde você está para mostrar só o que faz sentido agora. | — |
| A1 | Planejamento | Mapa da Fase 1: onde estamos na arquitetura | Ver o projeto inteiro e entender qual parte a Fase 1 constrói. | — |
| E03 | Planejamento | Arquivo de requisitos (PDF) | Ler seus requisitos para entender o escopo do projeto. | 1 - Introdução à programação web |
| Q1 | Planejamento | Quiz da Fase 1: você está pronto para seguir? | Responder 5 perguntas para confirmar se o conteúdo desta fase ficou claro. | — |
| A2 | Desenvolvimento | Mapa da Fase 2: onde estamos na arquitetura | Ver o projeto inteiro e entender qual parte a Fase 2 constrói. | — |
| E04 | Desenvolvimento | Onde está o código do site? | Apontar a pasta do site (ou pedir um site inicial) para o tutor analisar. | 2 - HTML |
| E05 | Desenvolvimento | Raio-X do site: onde você está hoje | Medir a qualidade atual em 8 áreas (HTML, CSS, Responsivo, Acessibilidade, SEO, JavaScript, Desempenho, Publicação). | — |
| E06 | Desenvolvimento | O site está pronto para o GitHub? | Conferir organização: links internos, nomes de arquivo, README, .gitignore e ausência de arquivos sensíveis. | — |
| E07 | Desenvolvimento | Conta e repositório no GitHub | Criar sua conta e um repositório vazio onde o código vai morar na internet. | — |
| E08 | Desenvolvimento | Ambiente: o que existe e o que posso instalar? | Verificar Python (para o servidor local do tutor) e Git; instalar o que faltar (se você tiver permissão). | — |
| E09 | Desenvolvimento | Máquina virtual com Linux leve | Montar uma máquina virtual (VirtualBox + Linux) para continuar o projeto com liberdade total. | — |
| E10 | Desenvolvimento | Editor de código leve | Instalar um editor leve, com autocompletar e destaque da linguagem, para editar o projeto na VM. | — |
| E11 | Desenvolvimento | Enviar o código ao GitHub | Colocar o código da sua pasta no repositório online. | — |
| E12 | Desenvolvimento | HTML semântico e válido | Estruturar as páginas com os elementos certos: header, nav, main, section, article, footer e títulos em ordem. | 2 - HTML |
| E13 | Desenvolvimento | CSS organizado: variáveis, reset e classes | Organizar o CSS em camadas (tokens, base, componentes) com variáveis, reset básico e seletores simples. | 2.1 - CSS |
| E14 | Desenvolvimento | Layout responsivo (mobile first) | Fazer o site funcionar de 320 px a telas grandes, sem rolagem horizontal, com Flexbox/Grid e media queries. | 3 - Design responsivo |
| E15 | Desenvolvimento | Design visual e acessibilidade | Aplicar boas práticas de design (hierarquia, espaçamento, tipografia, contraste) e deixar o site utilizável por todos. | 2.1 - CSS |
| E16 | Desenvolvimento | JavaScript de qualidade | Escrever JavaScript legível, modular e seguro: DOM, eventos, validação, localStorage e tratamento de erros. | Java Script, JS Relâmpago |
| E17 | Desenvolvimento | SEO e arquivos de publicação | Ajustar title, description, Open Graph, favicon, robots.txt, sitemap.xml e 404.html. | — |
| E18 | Desenvolvimento | Desempenho: imagens, fontes e peso | Deixar as páginas leves: imagens otimizadas, poucos arquivos, fontes com display=swap. | — |
| Q2 | Desenvolvimento | Quiz da Fase 2: você está pronto para seguir? | Responder 5 perguntas para confirmar se o conteúdo desta fase ficou claro. | — |
| A3 | Implantação | Mapa da Fase 3: onde estamos na arquitetura | Ver o projeto inteiro e entender qual parte a Fase 3 constrói. | — |
| E19 | Implantação | Teste final no modo GitHub Pages | Testar o site do jeito que ele será servido (prefixo do repositório, maiúsculas/minúsculas) e comparar a nota inicial com a final. | — |
| E20 | Implantação | Enviar a versão final ao GitHub | Registrar (commit) e enviar (push) todas as melhorias para o repositório. | — |
| E21 | Implantação | Publicar no GitHub Pages | Colocar o site no ar, de graça, em https://seu-usuario.github.io/seu-repositorio/. | — |
| E22 | Implantação | Depois de publicar | Medir com Lighthouse, divulgar o link, manter o site e conhecer as alternativas de hospedagem. | — |
| E23 | Implantação | Documentação técnica do site | Gerar e completar a documentação (modelo do curso) com páginas, design, qualidade e publicação. | — |
| Q3 | Implantação | Quiz da Fase 3: você está pronto para seguir? | Responder 5 perguntas para confirmar se o conteúdo desta fase ficou claro. | — |
| A4 | Web app (Fase 4) | Mapa da Fase 4: onde estamos na arquitetura | Ver o projeto inteiro e entender qual parte a Fase 4 constrói. | — |
| E24 | Web app (Fase 4) | O que do seu site precisa de banco de dados? | Identificar, no SEU código, os formulários e as funções que deveriam gravar dados num banco. | — |
| E25 | Web app (Fase 4) | Modelagem: desenhe as tabelas do seu banco | Planejar tabelas, colunas, chaves primárias e estrangeiras e os relacionamentos entre elas. | — |
| E26 | Web app (Fase 4) | Seu primeiro banco SQLite e o primeiro CRUD | Criar o banco a partir do seu modelo e executar Create, Read, Update e Delete. | — |
| E27 | Web app (Fase 4) | Transformar o site em web app (Flask, automático) | Instalar o Flask, gerar o back-end com API e painel, e ligar os formulários do seu site ao banco. | — |
| E28 | Web app (Fase 4) | Atualizar o GitHub com o web app | Registrar (commit) e enviar (push) o back-end para o repositório, sem enviar segredos nem arquivos pesados. | — |
| E29 | Web app (Fase 4) | Publicar o web app no Render | Colocar o Flask no ar, de graça, com endereço público e painel protegido. | — |
| E30 | Web app (Fase 4) | Migrar o banco para o Supabase | Trocar o SQLite local por PostgreSQL na nuvem, mantendo o mesmo código do site. | — |
| Q4 | Web app (Fase 4) | Quiz da Fase 4: você está pronto para seguir? | Responder 5 perguntas para confirmar se o conteúdo desta fase ficou claro. | — |
## Regras da auditoria
98 regras em 8 categorias. Veja `tutor/front/regras.py`: cada regra tem *porquê*, *como corrigir* e links.
## Pontuação
Erro = 14 pontos, aviso = 6, dica = 2 por REGRA violada; repetições pesam só 15% a mais (até 4x). Sem `index.html` a nota geral fica limitada a 60.

**Mapas (A1–A4)** mostram o diagrama da arquitetura com a fase atual destacada. **Quizzes (Q1–Q4)** têm 5 questões por fase; nota ≥ 4 = pronto, 3 = vale revisar, ≤ 2 = o tutor recomenda rever as etapas indicadas.
