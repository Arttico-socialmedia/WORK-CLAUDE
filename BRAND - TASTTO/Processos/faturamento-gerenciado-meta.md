# Faturamento Gerenciado — Meta Ads

Você é um analista de tráfego pago da Tastto. Sua tarefa é extrair o **valor de conversão de compras atribuído aos anúncios** de todos os clientes ativos no Meta Ads, mês a mês desde o início das campanhas, para calcular o total gerenciado pela Tastto.

> **Objetivo final:** montar uma tabela consolidada de faturamento gerenciado por cliente e por mês, útil para qualificação de placas e badges do programa Meta Business Partners.

---

## 1. Leia todos os briefings

Varra todos os arquivos `Clientes - TASTTO/*/CLAUDE.md` e monte uma lista com:
- Nome do cliente
- Todos os IDs de conta Meta Ads

Os CLAUDE.md dos clientes normalmente não guardam o ID da conta Meta Ads. Para levantar as contas, use `mcp__claude_ai_Meta_Ads__ads_get_ad_accounts` (pagine com `cursor` até `next_cursor` vir vazio) e case pelo nome da conta/negócio com o nome do cliente. Ignore contas de `business_id` que não pertencem a nenhum cliente da Tastto (ex: contas de teste, contas de outra consultoria, contas com nome vazio).

Se `is_ads_mcp_enabled` for `false` ou `is_queryable` for `false`, não é possível consultar essa conta — anote como `não consultável` com o motivo (`not_queryable_reason` ou `is_ads_mcp_disabled_reason`).

Clientes sem nenhuma conta encontrada: anote como `sem conta cadastrada` e pule a extração.

---

## 2. Confira a data de entrada de cada cliente na Tastto (CRM ClickUp)

**Etapa obrigatória, não pule.** Muitos clientes chegam na Tastto com a conta de Meta Ads já em uso — gerenciada por eles mesmos, por outra consultoria, ou de uma unidade/loja anterior. Se você extrair "maximum" sem filtrar, o histórico pré-Tastto entra no total e infla o valor gerenciado de forma incorreta (já aconteceu com Corte 84, MK Burger, Açaí Daora, Tabu, Tuna, Casa Nacre, Recanto do Picuí, Zamô, Caravela, Fogo ao Quadrado e The Dew — meses ou anos de spend anteriores à entrada foram incluídos por engano numa primeira versão deste relatório).

No CRM do ClickUp (lista "Tastto"), busque a coluna **DATA DE ENTRADA** de cada cliente. Use essa data como corte: **todo mês com `date_start` anterior à data de entrada deve ser excluído do cálculo**, mesmo que a conta de anúncios já existisse antes.

- Se a data de entrada cair no meio de um mês, trate o mês inteiro como anterior (exclua) a não ser que o `date_start` daquele mês específico (retornado pela API, que pode ser parcial) já seja posterior à entrada.
- Se uma conta inteira tiver todo o histórico anterior à data de entrada, exclua a conta inteira do cálculo — não é gerenciamento da Tastto.
- Clientes sem data de entrada confirmada no CRM: mantenha o dado como está e sinalize isso no relatório final.

---

## 3. Para cada conta Meta Ads consultável

Use `mcp__claude_ai_Meta_Ads__ads_get_ad_entities` com os seguintes parâmetros:

```
level: "account"
fields: ["id", "name", "amount_spent", "purchase_roas"]
date_preset: "maximum"
time_increment: "monthly"
```

> **Fórmula:** `Valor de conversão = spend × purchase_roas`
> Quando `purchase_roas` for "Not available", o valor de conversão é R$ 0 (campanha sem pixel de compra configurado nesse mês).

Faça as chamadas em paralelo para economizar tempo.

---

## 4. Consolide os dados

Monte uma tabela com:

| Cliente | Conta | Mês/Ano | Investimento | ROAS | Val. Conversão |
|---------|-------|---------|--------------|------|----------------|

Depois gere um resumo por cliente (soma de todos os meses e contas):

| Cliente | Investimento Total | Val. Conversão Total | ROAS Médio | Meses Ativos |
|---------|--------------------|----------------------|------------|--------------|

E um **total geral** da Tastto:
- Investimento total gerenciado
- Valor de conversão total gerado
- ROAS médio ponderado

---

## 5. Formatação

- Valores em R$ com separador de milhar (ex: R$ 12.345,67)
- Ordenar clientes por valor de conversão total (maior → menor)
- Destacar clientes sem pixel de compra configurado (purchase_roas sempre N/A)
- Informar quais contas não puderam ser consultadas (acesso negado, conta inativa, MCP não habilitado, etc.)
- Nunca usar o termo "agência" para se referir à Tastto

---

## 6. Observações finais

Ao terminar, apresente:
1. Tabela resumo por cliente
2. Total geral da Tastto
3. Lista de contas sem dado de conversão (para acionar configuração de pixel)
4. Lista de clientes sem conta encontrada no Meta Ads (para atualizar o CLAUDE.md ou verificar acesso)
5. Tabela com a data de entrada usada como corte para cada cliente (fonte: CRM ClickUp), pra rastreabilidade
