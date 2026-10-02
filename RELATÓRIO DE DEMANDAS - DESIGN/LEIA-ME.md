# Relatório de demandas — DESIGN

Relatório semanal das demandas **de clientes da Tastto** no kanban DESIGN do ClickUp, com foco em:
- quanto tempo as demandas ficam **em aberto**;
- quanto tempo levam até serem **finalizadas**;
- quanto tempo passam **em análise**.

## Onde ficam os relatórios
- `relatorios/AAAA-MM-DD.md`: um relatório por semana
- `dados/AAAA-MM-DD.json`: resumo numérico de cada semana, usado para comparar com a semana anterior

## Como roda
Toda **sexta às 18h** o Agendador de Tarefas do Windows roda `executar.bat` (tarefa "Relatorio Demandas Design").
Ele lê o ClickUp, gera o relatório e envia sozinho para o GitHub.
- O computador precisa estar **ligado e com internet**. Se estiver desligado às 18h, o relatório roda assim que ele for ligado.
- Para gerar na hora: dê dois cliques em `executar.bat`.
- Histórico de execuções e erros: `logs/execucao.log`.

## Ajustes
- **`clientes.txt`**: clientes da Tastto (um por linha). Tem uma seção "A CONFIRMAR" — tire o `#` dos que forem clientes. Uma tarefa conta como "de cliente" quando o nome do cliente aparece no título, nas tags ou nos campos dela.
- **`ignorar.txt`**: nomes que não são clientes da Tastto (clientes da Arttico, marcas próprias). Tarefas que começam com `C |` ou `E |` são sempre ignoradas.
- **`config.json`**:
  - `list_ids`: listas do ClickUp analisadas
  - `crm_list_id`: lista do CRM para atualizar os clientes sozinho
  - `alerta_dias_aberto` e `alerta_dias_analise`: limites dos alertas
- **`.env`**: token do ClickUp. Não vai para o GitHub.
- O **tempo em análise** depende do recurso *Time in Status* do ClickUp estar ativo (ClickApps → Time in Status).
