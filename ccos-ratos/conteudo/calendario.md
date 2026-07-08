# Calendário de Agendamento — Instagram (Arttico + Tastto)

Fonte única de verdade de tudo que está programado pra publicar. Controlado por status — nada vai ao ar sem passar por "aprovado" e sem confirmação individual no momento da publicação.

> Este arquivo é gerado automaticamente a partir de `calendario.json`. Não editar a tabela abaixo à mão — use `/calendario` (calendário visual) ou peça pro Claude. Editar `calendario.json` diretamente também funciona, mas prefira o comando `cli.js` pra manter os dois arquivos sincronizados.

## Status

| Status | Significado |
|---|---|
| `rascunho` | Ideia/conteúdo em produção, sem data confirmada |
| `pronto` | Conteúdo finalizado (imagens + legenda), aguardando data ou aprovação |
| `aprovado` | Data confirmada e liberado pra publicar. Só nesse status entra na fila do `/publicar-instagram` |
| `publicado` | Já foi ao ar. Preencher o link |
| `cancelado` | Não vai mais publicar (manter na tabela pra histórico, não apagar linha) |

## Como o agendamento funciona

1. Post entra na tabela como `rascunho` ou `pronto`.
2. Quando a Ilze define data/hora e marca como `aprovado`, o Claude cria um lembrete no Google Calendar (padrão: 1 dia antes e 2h antes) com preview da legenda e caminho do conteúdo.
3. No dia, ao ver o lembrete, ela abre o Claude Code e roda `/publicar-instagram agenda` (ou pede "o que tá aprovado pra hoje").
4. O Claude mostra o preview de cada post `aprovado` com data batendo e pede confirmação **individual** antes de publicar cada um. Nada publica em lote sem passar por essa confirmação.
5. Após publicar, o Claude atualiza o status pra `publicado` e preenche o link nesta tabela.

Publicação continua 100% local (as chaves do Instagram/Post for Me ficam só no `.env` da máquina, nunca em nuvem ou no GitHub).

## Fila de posts

| Data | Hora | Marca | Conteúdo | Legenda (resumo) | Status | Link publicado |
|---|---|---|---|---|---|---|
| 2026-07-07 |  | Tastto | conteudo/tastto/carrosseis/delivery-x-fidelizacao/instagram/ (carrossel, 5 cards em vídeo) | PENDENTE — localizar o comentário com a legenda | publicado (falta legenda) |  |
| 2026-07-07 |  | Arttico | conteudo/arttico/carrosseis/atualizacoes-api-oficial/instagram/ (carrossel, 3 slides) | "A Meta mudou a forma como a API oficial do WhatsApp funciona..." | aprovado |  |
