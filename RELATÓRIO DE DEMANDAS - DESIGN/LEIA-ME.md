# Relatório de demandas — DESIGN

Relatório semanal das demandas **de clientes da Tastto** no kanban DESIGN do ClickUp, com foco em:
- quanto tempo as demandas ficam **em aberto**;
- quanto tempo levam até serem **finalizadas**;
- quanto tempo passam **em análise**.

## Semanas
Cada relatório cobre uma semana de **segunda a sexta**.
- `relatorios/AAAA-MM-DD_a_AAAA-MM-DD.md`: um relatório por semana (ex.: `2026-10-12_a_2026-10-16.md`)
- `dados/AAAA-MM-DD_a_AAAA-MM-DD.json`: resumo numérico da semana, usado para comparar com a semana anterior

Histórico disponível desde a semana de 31/08 a 04/09/2026. As semanas passadas foram reconstruídas pelo histórico do ClickUp:
- finalizadas e tempos até finalizar são exatos;
- o status das demandas abertas é o do fim da semana (sexta).

Uma demanda conta como concluída quando chega pela primeira vez em **feito** ou **finalizado**.

## Como roda
Toda **sexta às 19h** o Agendador de Tarefas do Windows (tarefa "Relatorio Demandas Design") gera, sem abrir janela, o relatório da semana e envia para o GitHub.
- O computador precisa estar **ligado e com internet**.
- Se estiver desligado na sexta, o relatório roda assim que ele for ligado e gera a semana que ficou faltando.
- Para gerar na hora: dê dois cliques em `executar.bat`.
- Para refazer semanas: `python relatorio.py --historico 2026-09-01 2026-10-16`
- Histórico de execuções e erros: `logs/execucao.log`.

## Ajustes
- **`clientes.txt`**: clientes da Tastto, um por linha.
  - Uma tarefa conta como "de cliente" quando o nome do cliente aparece no título, nas tags ou nos campos dela.
  - A seção "A CONFIRMAR" traz nomes ainda não confirmados: tire o `#` dos que forem clientes da Tastto.
- **`ignorar.txt`**: nomes que não são clientes da Tastto (clientes da Arttico, marcas próprias). Tarefas que começam com `C |` ou `E |` são sempre ignoradas.
- **`config.json`**:
  - `list_ids`: listas do ClickUp analisadas
  - `crm_list_id`: lista do CRM, para atualizar os clientes sozinho
  - `alerta_dias_aberto` e `alerta_dias_analise`: limites dos alertas
- **`.env`**: token do ClickUp. Não vai para o GitHub.
