# Aprendizados — Comentario DM Ratos

<!-- O Claude registra aqui erros, descobertas e regras aprendidas durante o uso.
     Formato:
     ### {DATA} — {titulo curto}
     **Regra:** {o que fazer sempre/nunca}
     **Contexto:** {o que aconteceu pra gerar esse aprendizado}
-->

### 2026-06-20 — Resolver media_id com token Instagram Login
**Regra:** Pra converter URL/shortcode em media_id quando o token é do tipo "Instagram API with Instagram Login" (começa com IGAA/IGAG), NÃO usar `business_discovery` — esse campo não existe nesse tipo de token (retorna erro code 100 "Tried accessing nonexisting field"). Usar o endpoint direto da própria conta: `GET https://graph.instagram.com/v22.0/{ACCOUNT_ID}/media?fields=id,shortcode,caption,timestamp&limit=50&access_token=...` e casar pelo shortcode.
**Contexto:** No setup demo da @dobralabs o business_discovery (que era o comando sugerido no SKILL.md) falhou; o endpoint /media direto funcionou e achou o post na hora.
