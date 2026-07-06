# Arttico & Tastto — Claude Code OS

## O que é esse workspace
Workspace de trabalho da Ilze, social media interna do Grupo Arttico (Agência Arttico) e da Tastto. Aqui fica o planejamento estratégico de conteúdo, redes sociais, retenção de dados e materiais de marketing das duas marcas.

**Estrutura de pastas:**
- `_contexto/` — memória do sistema (não apagar)
- `marca/arttico/` e `marca/tastto/` — identidade visual de cada marca
- `conteudo/arttico/` e `conteudo/tastto/` — roteiros, carrosséis e ideias por marca
- `reunioes/` — atas e anotações de reunião
- `relatorios/` — relatórios e análises de métricas
- `dados/` — drop zone pra arquivos analisar (CSV, XLSX, TXT, PDF)
- `templates/skills/` — templates de skills prontos pra personalizar com /mapear
- `templates/ferramentas/catalogo.md` — APIs e ferramentas disponíveis pra usar em skills
- `tarefas.md` — lista de tarefas corrente

Material recebido do time da Tastto (id-visual com logos/paleta/MIV, cases, marketing e relatórios de campanha, processos) fica fora desse repositório, na pasta irmã `../BRAND - TASTTO/` — esse repositório é o kit compartilhado do curso (github.com/dobralabs/ccos-ratos), então dado de negócio/cliente não deve ficar aqui dentro pra não ser commitado nele.

## Sobre o negócio
Grupo Arttico atua em marketing, growth e performance, ajudando empresas a captar mais clientes, aumentar conversão comercial e vender mais pra própria base — com forte atuação em consultoria pra food service. Tastto é a plataforma do grupo voltada pra inteligência de dados e crescimento de restaurantes. Ilze é a social media interna, responsável pela estratégia de conteúdo e retenção de dados nas redes sociais das duas marcas.

## O que mais fazemos aqui
- Planejamento estratégico de conteúdo e redes sociais (Arttico e Tastto)
- Roteiros pra Reels, YouTube e vídeos
- Planejamento editorial e SEO pro YouTube
- Análise de métricas e retenção de dados
- Apresentações e briefings internos
- Direcionamento criativo pra designers e videomakers

## Clientes e contexto
Foco 100% interno por enquanto — conteúdo e estratégia pras marcas Arttico e Tastto. O grupo atende clientes externos de agência, mas esse workspace não cobre esse atendimento no momento.

## Tom de voz
Varia por marca: Arttico é estratégico, direto e educativo, sem frase motivacional vazia; Tastto é consultivo e baseado em dados; conteúdo social é natural e conversacional, sem cara de texto de IA. Evitar clichês tipo "não é sobre X, é sobre Y" e "no mundo de hoje". Detalhes em `_contexto/preferencias.md`.

## Ferramentas conectadas
- [x] Google Drive
- [ ] Google Docs / Sheets / Slides
- [x] Meta Ads (skill /meta-ads-ratos)
- [x] Google Ads (skill /google-ads-ratos)
- [x] Google Analytics (skill /ga4-ratos)
- [ ] RD Station CRM
- [ ] Titan CRM
- [ ] PipeDrive
- [ ] Reportei
- [ ] WhatsApp Business API
- [ ] GitHub (deploys)

*(Marcar conforme for instalando os MCPs)*

---

## Contexto do negócio

No início de toda conversa, ler os seguintes arquivos (se existirem e estiverem configurados):

1. `_contexto/empresa.md` — quem é o usuário, o que faz, como funciona o negócio
2. `_contexto/preferencias.md` — tom de voz, estilo de escrita, o que evitar
3. `_contexto/estrategia.md` — foco atual, prioridades, o que pode esperar

Usar essas informações como base pra qualquer resposta ou decisão. Ao sugerir prioridades, formatos ou abordagens, considerar o foco atual descrito em `estrategia.md`.

Para qualquer tarefa visual (carrossel, proposta, slide, landing page), consultar `marca/arttico/design-guide.md` ou `marca/tastto/design-guide.md` conforme a marca do pedido.

Não é necessário listar o que foi lido nem confirmar a leitura. Apenas usar o contexto naturalmente.

---

## Fluxo de trabalho

Antes de executar qualquer tarefa, verificar se existe uma skill relevante em `.claude/skills/` ou `.claude/commands/`.
Se encontrar, seguir as instruções da skill.
Se não encontrar, executar a tarefa normalmente.

Ao concluir uma tarefa que não tinha skill mas parece repetível, perguntar se o usuário quer transformar em skill. Não perguntar pra tarefas pontuais.

---

## Aprender com correções

Quando o usuário corrigir algo ou der uma instrução que parece permanente ("na verdade é assim", "não faça mais isso", "prefiro assim", "sempre que...", "evita..."), perguntar se quer salvar. Se sim:

- **Sobre o negócio** → `_contexto/empresa.md`
- **Preferências e estilo** → `_contexto/preferencias.md`
- **Prioridades e foco atual** → `_contexto/estrategia.md`
- **Regra de comportamento nessa pasta** → este `CLAUDE.md`
- **Mudança visual** → `marca/arttico/design-guide.md` ou `marca/tastto/design-guide.md`

Salvar só a linha nova, sem reformatar o arquivo inteiro.

---

## Manter contexto atualizado

Ao terminar uma tarefa que mudou algo relevante no projeto (nova prioridade, nova skill, mudança de foco, novo processo, ferramenta instalada), perguntar se quer atualizar os arquivos de memória. Mostrar o que vai mudar antes de salvar, sem reformatar o arquivo inteiro.

**Dica:** se não souber se algo mudou, rodar `/atualizar` faz uma varredura completa.
