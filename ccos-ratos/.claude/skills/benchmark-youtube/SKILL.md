---
name: benchmark-youtube
description: >
  Transcreve vídeos de referência (YouTube ou qualquer link suportado pela /transcribe),
  extrai os insights de estratégia de conteúdo (gancho, tática, estrutura, CTA),
  acumula num banco de insights e transforma isso em estratégia de conteúdo e
  direcionamento de roteiro adaptados pra Arttico e Tastto.
  Diferente da /youtube-ratos (que lê métricas do canal próprio via API) — essa skill
  analisa vídeos de fora pra virar referência estratégica.
  Use quando o usuário mandar um link de vídeo pra analisar, mencionar "benchmark de
  conteúdo", "video de referencia", "analisa esse video e tira insights", "o que
  esta funcionando nesse nicho", "adapta isso pra nossa estrategia", ou "pesquisa de
  concorrencia no youtube".
---

# /benchmark-youtube — Benchmark de Conteúdo a partir de Vídeos de Referência

## Dependências

- **Transcrição:** skill `/transcribe` (já instalada globalmente)
- **Contexto do negócio:** `_contexto/empresa.md`
- **Tom de voz:** `_contexto/preferencias.md`
- **Foco atual:** `_contexto/estrategia.md`
- **Formato de roteiro de vídeo curto:** mesmo padrão da skill `roteiro-post` (beats com tempo aproximado)

## Antes de começar

Ler `_contexto/empresa.md`, `_contexto/preferencias.md` e `_contexto/estrategia.md` pra saber o momento atual das marcas e calibrar tom.

---

## Workflow

### Passo 1 — Receber o vídeo

Pedir (se não vier junto) o link do vídeo de referência. Aceita um ou vários de uma vez.

### Passo 2 — Transcrever

Invocar a skill `/transcribe` pra cada link. Não reimplementar a transcrição aqui.

### Passo 3 — Extrair insights

A partir da transcrição, preencher esse checklist (não inventar o que não está no texto — se um ponto não aparece, marcar como "não identificado"):

- **Gancho inicial:** como o vídeo prende atenção nos primeiros segundos
- **Tema central:** de que o vídeo realmente trata, em uma frase
- **Tática/mecanismo ensinado:** o "como fazer" específico que o vídeo revela (não a ideia genérica)
- **Prova social/autoridade:** números, cases, credenciais usadas pra validar o argumento
- **Estrutura narrativa:** ordem em que as ideias aparecem (ex: promessa → mecanismo → prova → CTA)
- **CTA:** o que o vídeo pede no final
- **Por que parece estar funcionando:** sinais no próprio conteúdo (não inventar dados de audiência que não existem)

### Passo 4 — Decidir relevância por marca

Comparar os insights com `_contexto/empresa.md` e `_contexto/estrategia.md`. Se não estiver óbvio, perguntar:

> "Esse insight faz mais sentido pra Arttico, pra Tastto, ou pras duas?"

### Passo 5 — Registrar no banco de insights

Arquivo: `relatorios/youtube-insights/banco-insights.md` (criar pasta e arquivo se não existirem, com um cabeçalho simples).

Adicionar uma entrada nova (nunca reescrever entradas antigas):

```markdown
## [data] — [título do vídeo] ([marca: Arttico/Tastto/Ambas])
Fonte: [link]
- Gancho: ...
- Tema: ...
- Tática: ...
- Prova social: ...
- Estrutura: ...
- CTA: ...
- Por que funciona: ...
```

### Passo 6 — Atualizar a estratégia

Ler o banco de insights inteiro (não só a entrada nova) e gerar/atualizar `relatorios/youtube-insights/estrategia-atual.md` com:

- **Padrões recorrentes** (o que se repete entre os vídeos analisados até agora)
- **Temas prioritários** pra Arttico e pra Tastto, separados
- **Formatos recomendados** (Reels, YouTube longo, carrossel) por tema
- **O que adaptar** (não copiar tática pura — dizer como ela se encaixa no posicionamento e tom de cada marca, conforme `preferencias.md`)

Reescrever esse arquivo do zero a cada atualização (é sempre a síntese mais atual do banco), mantendo o banco de insights como histórico intocado.

### Passo 7 — Direcionamento de roteiro

Escolher com o usuário pelo menos uma ideia concreta da estratégia atualizada e transformar em direcionamento de roteiro (não roteiro pronto linha a linha — direção estrutural pra quem for produzir):

- **Marca e formato** (ex: Tastto — Reels)
- **Gancho proposto** (adaptado ao tom da marca, não copiado do vídeo-fonte)
- **Beats com tempo aproximado**, seguindo o padrão de `roteiro-post`:
  - 0-3s: hook visual + frase de abertura
  - 4-20s: o problema ou a promessa
  - 21-45s: o mecanismo/resposta
  - 46-60s: conclusão + CTA
  - (ajustar os tempos se o formato for YouTube longo em vez de vídeo curto)
- **Referência:** de qual vídeo/insight do banco essa direção partiu

Salvar em `conteudo/[arttico|tastto]/roteiros/direcionamento-[tema]-[data].md` (criar as pastas `conteudo/arttico/roteiros/` ou `conteudo/tastto/roteiros/` se não existirem).

### Passo 8 — Confirmar

> "Analisei [N] vídeo(s), atualizei o banco de insights e a estratégia, e deixei um direcionamento de roteiro pronto em [caminho]. Quer que eu gere mais algum roteiro a partir da estratégia atual, ou seguimos pro próximo vídeo?"

---

## Regras

- Nunca inventar métrica de audiência que não está na transcrição ou que o usuário não informou
- O banco de insights é histórico — só adiciona, nunca reescreve entradas antigas
- A estratégia é síntese — pode e deve ser reescrita inteira a cada atualização
- Tática de outro criador nunca é copiada literalmente — sempre adaptada ao tom e posicionamento da marca (`preferencias.md`)
- Se o vídeo analisado for de um nicho muito distante de food service/growth, avisar antes de forçar adaptação: "Esse conteúdo é de um nicho bem diferente do nosso — os insights podem não se aplicar direto. Quer que eu tente adaptar mesmo assim?"
- Direcionamento de roteiro é estrutura, não texto final — quem quiser o roteiro linha a linha usa `/roteiro-post` depois
