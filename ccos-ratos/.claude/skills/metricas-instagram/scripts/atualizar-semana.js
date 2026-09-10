#!/usr/bin/env node
// Preenche a semana mais recente e completa ainda vazia nas planilhas de metricas do Instagram (Arttico e Tastto).
// Le a estrutura ja existente nas abas mensais (nao cria abas novas, nao mexe em nada alem das celulas de semana).

const https = require("https");
const path = require("path");
const fs = require("fs");

const ENV_PATH = path.join(__dirname, "..", ".env");

function loadEnv() {
  const raw = fs.readFileSync(ENV_PATH, "utf8");
  const env = {};
  for (const line of raw.split("\n")) {
    const m = line.match(/^([A-Z_]+)="?(.*?)"?\s*$/);
    if (m) env[m[1]] = m[2];
  }
  return env;
}

function httpsRequest(options, body) {
  return new Promise((resolve, reject) => {
    const req = https.request(options, (res) => {
      let data = "";
      res.on("data", (c) => (data += c));
      res.on("end", () => {
        try {
          resolve({ status: res.statusCode, json: JSON.parse(data) });
        } catch (e) {
          resolve({ status: res.statusCode, json: null, raw: data });
        }
      });
    });
    req.on("error", reject);
    if (body) req.write(body);
    req.end();
  });
}

async function getGoogleAccessToken(env) {
  const body = new URLSearchParams({
    client_id: env.GOOGLE_CLIENT_ID,
    client_secret: env.GOOGLE_CLIENT_SECRET,
    refresh_token: env.GOOGLE_REFRESH_TOKEN,
    grant_type: "refresh_token",
  }).toString();
  const { json } = await httpsRequest(
    {
      hostname: "oauth2.googleapis.com",
      path: "/token",
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded", "Content-Length": Buffer.byteLength(body) },
    },
    body
  );
  if (!json || !json.access_token) throw new Error("Falha ao renovar token do Google: " + JSON.stringify(json));
  return json.access_token;
}

async function sheetsGet(spreadsheetId, range, accessToken) {
  const { json } = await httpsRequest({
    hostname: "sheets.googleapis.com",
    path: `/v4/spreadsheets/${spreadsheetId}/values/${encodeURIComponent(range)}`,
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return json;
}

async function sheetsBatchUpdate(spreadsheetId, data, accessToken) {
  const body = JSON.stringify({ valueInputOption: "USER_ENTERED", data });
  const { json } = await httpsRequest(
    {
      hostname: "sheets.googleapis.com",
      path: `/v4/spreadsheets/${spreadsheetId}/values:batchUpdate`,
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(body),
      },
    },
    body
  );
  return json;
}

async function igInsight(accountId, token, metric, since, until, breakdown) {
  const params = new URLSearchParams({
    metric,
    period: "day",
    metric_type: "total_value",
    since: String(since),
    until: String(until),
    access_token: token,
  });
  if (breakdown) params.set("breakdown", breakdown);
  const { json } = await httpsRequest({
    hostname: "graph.facebook.com",
    path: `/v21.0/${accountId}/insights?${params.toString()}`,
    method: "GET",
  });
  if (!json || json.error) throw new Error(`Erro Instagram (${metric}): ` + JSON.stringify(json && json.error));
  return json.data[0];
}

async function igFollowerDelta(accountId, token, since, until) {
  const params = new URLSearchParams({
    metric: "follower_count",
    period: "day",
    metric_type: "time_series",
    since: String(since),
    until: String(until),
    access_token: token,
  });
  const { json } = await httpsRequest({
    hostname: "graph.facebook.com",
    path: `/v21.0/${accountId}/insights?${params.toString()}`,
    method: "GET",
  });
  if (!json || json.error) throw new Error("Erro Instagram (follower_count): " + JSON.stringify(json && json.error));
  return json.data[0].values.reduce((sum, v) => sum + v.value, 0);
}

function breakdownValue(insight, key) {
  const b = insight.total_value.breakdowns && insight.total_value.breakdowns[0];
  if (!b) return {};
  const out = {};
  for (const r of b.results) out[r.dimension_values[0]] = r.value;
  return out;
}

const MESES = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];

function currentTabName(date) {
  const mes = MESES[date.getMonth()];
  const yy = String(date.getFullYear()).slice(2);
  return `${mes} ${yy}`;
}

function parseWeekLabel(label) {
  // ex: "Semana 1 | (01.09 a 06.09 )" -> {start:{d:1,m:9}, end:{d:6,m:9}}
  const m = label.match(/\((\d{2})\.(\d{2})\s*a\s*(\d{2})\.(\d{2})\s*\)/);
  if (!m) return null;
  return {
    start: { d: parseInt(m[1], 10), mo: parseInt(m[2], 10) },
    end: { d: parseInt(m[3], 10), mo: parseInt(m[4], 10) },
  };
}

async function processarMarca(nome, spreadsheetId, accountId, env, accessToken) {
  console.log(`\n=== ${nome} ===`);
  const hoje = new Date();
  const tab = currentTabName(hoje);
  const ano = hoje.getFullYear();

  const colG = await sheetsGet(spreadsheetId, `'${tab}'!G21:H25`, accessToken);
  const colJR = await sheetsGet(spreadsheetId, `'${tab}'!J37:Z41`, accessToken);

  const semanasG = colG.values || [];
  const semanasJR = colJR.values || [];

  let alvo = null;
  for (let i = 0; i < semanasG.length; i++) {
    const label = semanasG[i] && semanasG[i][0];
    if (!label) continue;
    const parsed = parseWeekLabel(label);
    if (!parsed) continue; // placeholder tipo "Semana 5 | (XX.XX)"
    const fimSemana = new Date(ano, parsed.end.mo - 1, parsed.end.d, 23, 59, 59);
    const jaTemDado = semanasG[i][1] !== undefined && semanasG[i][1] !== "";
    if (fimSemana < hoje && !jaTemDado) {
      alvo = { rowG: 21 + i, parsed };
      break; // pega a mais antiga ainda vazia
    }
  }

  if (!alvo) {
    console.log(`Nada a preencher em ${tab} (nenhuma semana completa esta pendente).`);
    return;
  }

  const rowJR = 37 + alvo.rowG - 21; // mesma posicao relativa (Semana1->37, Semana2->38, ...)
  const inicio = new Date(ano, alvo.parsed.start.mo - 1, alvo.parsed.start.d, 0, 0, 0);
  const fim = new Date(ano, alvo.parsed.end.mo - 1, alvo.parsed.end.d + 1, 0, 0, 0);
  const since = Math.floor(inicio.getTime() / 1000);
  const until = Math.floor(fim.getTime() / 1000);

  console.log(`Preenchendo linha da semana ${alvo.rowG - 20} (${inicio.toISOString().slice(0,10)} a ${alvo.parsed.end.d}/${alvo.parsed.end.mo})`);

  const token = env.INSTAGRAM_ACCESS_TOKEN;
  const [reach, engaged, interactions, profileViews, websiteClicks, followerDelta] = await Promise.all([
    igInsight(accountId, token, "reach", since, until, "follow_type"),
    igInsight(accountId, token, "accounts_engaged", since, until),
    igInsight(accountId, token, "total_interactions", since, until, "media_product_type"),
    igInsight(accountId, token, "profile_views", since, until),
    igInsight(accountId, token, "website_clicks", since, until),
    igFollowerDelta(accountId, token, since, until),
  ]);

  const reachBd = breakdownValue(reach);
  const interBd = breakdownValue(interactions);
  if (interBd.AD) {
    console.log(`Aviso: ${interBd.AD} interacoes vieram de conteudo impulsionado (AD) e nao entram em nenhuma coluna (sem coluna propria na planilha).`);
  }

  const alcanceGeral = reach.total_value.value;
  const seguidoresAlcance = reachBd.FOLLOWER || 0;
  const naoSeguidoresAlcance = reachBd.NON_FOLLOWER || 0;
  const visitasPerfil = profileViews.total_value.value;
  const toquesSite = websiteClicks.total_value.value;
  const engajamento = engaged.total_value.value;
  const interacoesGeral = interactions.total_value.value;
  const interPost = interBd.POST || 0;
  const interReel = interBd.REEL || 0;
  const interStory = interBd.STORY || 0;

  const updates = [
    { range: `'${tab}'!H${alvo.rowG}`, values: [[followerDelta]] },
    { range: `'${tab}'!K${rowJR}:P${rowJR}`, values: [[alcanceGeral, alcanceGeral, seguidoresAlcance, naoSeguidoresAlcance, visitasPerfil, toquesSite]] },
    { range: `'${tab}'!S${rowJR}:Z${rowJR}`, values: [[engajamento, "", "", interacoesGeral, interacoesGeral, interPost, interReel, interStory]] },
  ];

  const result = await sheetsBatchUpdate(spreadsheetId, updates, accessToken);
  console.log(`Escrito: ${result.totalUpdatedCells} celulas atualizadas em "${tab}".`);
}

async function renovarTokenInstagram(env) {
  const params = new URLSearchParams({
    grant_type: "fb_exchange_token",
    client_id: env.META_APP_ID,
    client_secret: env.META_APP_SECRET,
    fb_exchange_token: env.INSTAGRAM_ACCESS_TOKEN,
  });
  const { json } = await httpsRequest({
    hostname: "graph.facebook.com",
    path: `/v21.0/oauth/access_token?${params.toString()}`,
    method: "GET",
  });
  if (!json || !json.access_token) {
    console.log("Aviso: nao foi possivel renovar o token do Instagram, seguindo com o atual. " + JSON.stringify(json));
    return;
  }
  const raw = fs.readFileSync(ENV_PATH, "utf8");
  const atualizado = raw.replace(/INSTAGRAM_ACCESS_TOKEN="[^"]*"/, `INSTAGRAM_ACCESS_TOKEN="${json.access_token}"`);
  fs.writeFileSync(ENV_PATH, atualizado);
  env.INSTAGRAM_ACCESS_TOKEN = json.access_token;
  console.log(`Token do Instagram renovado (novos ${Math.round(json.expires_in / 86400)} dias de validade).`);
}

async function main() {
  const env = loadEnv();
  await renovarTokenInstagram(env);
  const accessToken = await getGoogleAccessToken(env);

  await processarMarca("Arttico", "1dJ0U7OyfJmp96boDx5bYFZFn5GlQwgiVwaTjKekoDSs", env.INSTAGRAM_USER_ID_ARTTICO, env, accessToken);
  await processarMarca("Tastto", "1KV5QpcRytdSxwrSoQ5eyME0i2yrXClvk-6OnTgK7S3w", env.INSTAGRAM_USER_ID_TASTTO, env, accessToken);
}

main().catch((err) => {
  console.error("ERRO:", err.message);
  process.exit(1);
});
