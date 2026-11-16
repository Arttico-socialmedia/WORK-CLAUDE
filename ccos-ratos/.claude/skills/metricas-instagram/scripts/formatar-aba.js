#!/usr/bin/env node
// Aplica o visual "dash" (cores Arttico/Tastto) a uma aba mensal da planilha de metricas do Instagram.
// SO formatacao: nao move celulas nem altera numeros/formulas (o atualizar-semana.js le posicoes fixas).
// Unica escrita de conteudo: o titulo em A1 (linha 1 e vazia no modelo).
// Uso: node formatar-aba.js <arttico|tastto> "<Aba>"     ex.: node formatar-aba.js arttico "Agosto 26"
// Pode rodar de novo na mesma aba sem duplicar nada.

const https = require("https");
const path = require("path");
const fs = require("fs");

const PLANILHAS = {
  arttico: "1dJ0U7OyfJmp96boDx5bYFZFn5GlQwgiVwaTjKekoDSs",
  tastto: "1KV5QpcRytdSxwrSoQ5eyME0i2yrXClvk-6OnTgK7S3w",
};
const MESES = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];

// Paletas por marca. Os nomes das chaves sao papeis (nao cores literais).
// Arttico: so o navy #010130, o secundario #1B1446 (C100 M99 Y40 K40) e tons claros do proprio navy + branco.
// Tastto: paleta Tastto (#6C6CFF, #B0AFFF, #D6E1EA, #F96A2B).
const PALETAS = {
  arttico: {
    navy: "#010130",
    branco: "#FFFFFF",
    lilas: "#9C9CB8",      // destaque medio (gradiente, linha 2025)
    lilasClaro: "#E6E6EF", // linha do mes em destaque
    azul: "#1B1446",       // secundario (fio do titulo, grafico de alcance)
    cinzaAzul: "#D9D9E4",  // cabecalhos de coluna e bordas externas
    zebra: "#F6F6F9",
    linha: "#E6E6EC",
    laranja: "#C0392B",    // saldo negativo (unica cor fora da marca, so sinalizacao)
    texto: "#010130",
    textoSuave: "#5A5A78",
  },
  // Tastto (BRAND - TASTTO/design-guide.md): azul profundo #1A1A2D, azul eletrico #6C6CFF,
  // lavanda tech #B0AFFF, cinza azulado #D6E1EA, laranja vibrante #F96A2B (alertas)
  tastto: {
    navy: "#1A1A2D",       // azul profundo: faixa de titulo, titulos de tabela, textos, grafico de seguidores
    branco: "#FFFFFF",
    lilas: "#B0AFFF",      // lavanda tech: gradiente, linha do ano anterior
    lilasClaro: "#EEEEFF", // tom claro da lavanda: linha do mes em destaque
    azul: "#6C6CFF",       // azul eletrico: fio do titulo, grafico de alcance
    cinzaAzul: "#D6E1EA",  // cinza azulado: cabecalhos de coluna e bordas externas
    zebra: "#F3F6F9",      // tom claro do cinza azulado
    linha: "#E2E9EF",
    laranja: "#F96A2B",    // laranja vibrante: saldo negativo
    texto: "#1A1A2D",
    textoSuave: "#5C5C75",
  },
};
// papeis visuais por marca (o que torna Arttico e Tastto diferentes alem da cor)
const ESTILO = {
  // Arttico: sobria, tudo no navy; Raleway/Lato
  arttico: (C) => ({ faixa: C.navy, fio: C.azul, secao: C.navy, cabecalho: C.cinzaAzul, cabecalhoTexto: C.navy, aba: C.navy,
    serieAtual: C.navy, serieAnt: C.lilas, serieSeg: C.navy, serieAlc: C.azul, fonteTitulo: "Raleway", fonte: "Lato" }),
  // Tastto: azul eletrico como protagonista, fio laranja, cabecalhos lavanda, tipografia mono (tech); IBM Plex
  tastto: (C) => ({ faixa: C.azul, fio: C.laranja, secao: C.azul, cabecalho: C.lilas, cabecalhoTexto: C.navy, aba: C.azul,
    serieAtual: C.azul, serieAnt: C.lilas, serieSeg: C.azul, serieAlc: C.navy, fonteTitulo: "IBM Plex Mono", fonte: "IBM Plex Sans" }),
};
let C = PALETAS.arttico;
let E = ESTILO.arttico(C);
let FONTE_TITULO = "Raleway";
let FONTE = "Lato";

function rgb(hex) {
  const h = hex.replace("#", "");
  return { red: parseInt(h.slice(0, 2), 16) / 255, green: parseInt(h.slice(2, 4), 16) / 255, blue: parseInt(h.slice(4, 6), 16) / 255 };
}
const cs = (hex) => ({ rgbColor: rgb(hex) });

function loadEnv() {
  const raw = fs.readFileSync(path.join(__dirname, "..", ".env"), "utf8");
  const env = {};
  for (const line of raw.split("\n")) {
    const m = line.match(/^([A-Z_]+)="?(.*?)"?\s*$/);
    if (m) env[m[1]] = m[2];
  }
  return env;
}
function req(options, body) {
  return new Promise((resolve, reject) => {
    const r = https.request(options, (res) => {
      let d = "";
      res.on("data", (c) => (d += c));
      res.on("end", () => { try { resolve(JSON.parse(d)); } catch (e) { resolve(d); } });
    });
    r.on("error", reject);
    if (body) r.write(body);
    r.end();
  });
}
async function googleToken(env) {
  const body = new URLSearchParams({ client_id: env.GOOGLE_CLIENT_ID, client_secret: env.GOOGLE_CLIENT_SECRET, refresh_token: env.GOOGLE_REFRESH_TOKEN, grant_type: "refresh_token" }).toString();
  const r = await req({ hostname: "oauth2.googleapis.com", path: "/token", method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded", "Content-Length": Buffer.byteLength(body) } }, body);
  if (!r.access_token) throw new Error("Falha no token Google: " + JSON.stringify(r));
  return r.access_token;
}

// A1 notation -> GridRange (linhas/colunas 0-based, fim exclusivo)
function colIdx(s) { let n = 0; for (const ch of s) n = n * 26 + (ch.charCodeAt(0) - 64); return n - 1; }
function gr(sheetId, a1) {
  const [a, b] = a1.split(":");
  const p = (x) => { const m = x.match(/^([A-Z]+)(\d+)$/); return { c: colIdx(m[1]), r: parseInt(m[2], 10) - 1 }; };
  const s = p(a), e = p(b || a);
  return { sheetId, startRowIndex: s.r, endRowIndex: e.r + 1, startColumnIndex: s.c, endColumnIndex: e.c + 1 };
}

function fmt(sheetId, a1, f, fields) {
  return { repeatCell: { range: gr(sheetId, a1), cell: { userEnteredFormat: f }, fields } };
}
function rowsHeight(sheetId, start, end, px) {
  return { updateDimensionProperties: { range: { sheetId, dimension: "ROWS", startIndex: start - 1, endIndex: end }, properties: { pixelSize: px }, fields: "pixelSize" } };
}
function borda(hex, style = "SOLID") { return { style, colorStyle: cs(hex) }; }

async function main() {
  const [marca, tab] = process.argv.slice(2);
  if (!PLANILHAS[marca] || !tab) {
    console.log('Uso: node formatar-aba.js <arttico|tastto> "<Aba>"');
    process.exit(1);
  }
  const ID = PLANILHAS[marca];
  C = PALETAS[marca];
  E = ESTILO[marca](C);
  FONTE_TITULO = E.fonteTitulo;
  FONTE = E.fonte;
  const env = loadEnv();
  const token = await googleToken(env);
  const H = { Authorization: `Bearer ${token}` };
  const get = (p) => req({ hostname: "sheets.googleapis.com", path: p, headers: H });
  const post = (p, obj) => { const b = JSON.stringify(obj); return req({ hostname: "sheets.googleapis.com", path: p, method: "POST", headers: { ...H, "Content-Type": "application/json", "Content-Length": Buffer.byteLength(b) } }, b); };

  const meta = await get(`/v4/spreadsheets/${ID}?ranges=${encodeURIComponent(`'${tab}'`)}&fields=sheets(properties,charts,bandedRanges,conditionalFormats,merges)`);
  if (!meta.sheets) throw new Error("Aba nao encontrada: " + JSON.stringify(meta.error || meta));
  const sh = meta.sheets[0];
  const sid = sh.properties.sheetId;

  // Confere se a aba segue o modelo esperado antes de mexer
  const check = await get(`/v4/spreadsheets/${ID}/values:batchGet?ranges=${encodeURIComponent(`'${tab}'!A1:Z2`)}&ranges=${encodeURIComponent(`'${tab}'!J20:J21`)}&ranges=${encodeURIComponent(`'${tab}'!J35:J36`)}`);
  const [topo, alc, sem] = check.valueRanges.map((v) => v.values || []);
  const topoTexto = topo.flat().join("").trim();
  const handle = ((sh.charts || []).map((c) => c.spec.title || "").join(" ").match(/@[\w.]+/) || [`@${marca}`])[0];
  const mesIndex = MESES.findIndex((m) => tab.startsWith(m));
  // ano: do cabecalho "Contas alcançadas / 2025" (abas antigas nao tem ano no nome); senao do sufixo "26"
  const anoCab = (alc[0][0].match(/(20\d{2})/) || [])[1];
  const anoSuf = (tab.match(/(\d{2})\s*$/) || [])[1];
  const ano = anoCab || (anoSuf ? "20" + anoSuf : "");
  // anos do grafico anual: serie 2 (coluna E) e o ano da aba; serie 1 (coluna B) e o ano anterior
  const anoAtual = ano || "";
  const anoAnt = ano ? String(Number(ano) - 1) : "";
  const tituloEsperado =`Métricas Instagram  ·  ${handle}  ·  ${mesIndex >= 0 ? MESES[mesIndex] : tab}${ano ? " " + ano : ""}`;
  // linhas 1-2 precisam estar vazias; aceita sobrescrever so lixo obvio (espacos ou um numero solto, ex. 6666666666666)
  const lixo = /^[\d.,\s]*$/.test(topoTexto);
  if (topoTexto && !topoTexto.startsWith("Métricas Instagram") && !lixo) throw new Error(`Linhas 1-2 de "${tab}" nao estao vazias (${topoTexto.slice(0, 60)}...). Abortando para nao sobrescrever.`);
  if (topoTexto && lixo) console.log(`Aviso: "${tab}" tinha "${topoTexto.trim() || "(espaços)"}" na linha 1, substituído pelo título.`);
  if (!(alc[0] && /Contas alcan/.test(alc[0][0])) || !(sem[0] && /Contas alcan/.test(sem[0][0]))) throw new Error(`"${tab}" nao segue o modelo (J20/J35). Abortando.`);

  const R = [];

  // limpa o que este script cria, para poder rodar de novo
  for (const b of sh.bandedRanges || []) R.push({ deleteBanding: { bandedRangeId: b.bandedRangeId } });
  for (let i = (sh.conditionalFormats || []).length - 1; i >= 0; i--) R.push({ deleteConditionalFormatRule: { sheetId: sid, index: i } });

  R.push({ updateSheetProperties: { properties: { sheetId: sid, tabColorStyle: cs(E.aba), gridProperties: { hideGridlines: true } }, fields: "tabColorStyle,gridProperties.hideGridlines" } });

  // base: fonte e cor de texto em toda a area usada
  R.push(fmt(sid, "A1:Z60", { textFormat: { fontFamily: FONTE, foregroundColorStyle: cs(C.texto) }, verticalAlignment: "MIDDLE" }, "userEnteredFormat.textFormat.fontFamily,userEnteredFormat.textFormat.foregroundColorStyle,userEnteredFormat.verticalAlignment"));

  // ---- faixa de titulo (linha 1) ----
  if (!(sh.merges || []).some((m) => m.startRowIndex === 0 && m.startColumnIndex === 0 && m.endColumnIndex === 26)) {
    R.push({ mergeCells: { range: gr(sid, "A1:Z1"), mergeType: "MERGE_ALL" } });
  }
  R.push({ updateCells: { range: gr(sid, "A1"), rows: [{ values: [{ userEnteredValue: { stringValue: tituloEsperado } }] }], fields: "userEnteredValue" } });
  R.push(fmt(sid, "A1:Z1", { backgroundColorStyle: cs(E.faixa), horizontalAlignment: "LEFT", verticalAlignment: "MIDDLE", padding: { left: 16 }, textFormat: { fontFamily: FONTE_TITULO, fontSize: 18, bold: true, foregroundColorStyle: cs(C.branco) } }, "userEnteredFormat(backgroundColorStyle,horizontalAlignment,verticalAlignment,padding,textFormat)"));
  R.push(fmt(sid, "A2:Z2", { backgroundColorStyle: cs(E.fio) }, "userEnteredFormat.backgroundColorStyle"));
  R.push(rowsHeight(sid, 1, 1, 56));
  R.push(rowsHeight(sid, 2, 2, 4));
  R.push(rowsHeight(sid, 3, 19, 21));

  // ---- tabelas ----
  const secoes = ["A20:B20", "D20:E20", "G20:H20", "J20:P20", "R20:Z20", "J35:P35", "R35:Z35"];
  const cabecalhos = ["J21:P21", "R21:Z21", "J36:P36", "R36:Z36"];
  const corpos = ["A21:B32", "D21:E32", "G21:H25", "J22:P33", "R22:Z33", "J37:P41", "R37:Z41"];
  const tabelas = ["A20:B32", "D20:E32", "G20:H25", "J20:P33", "R20:Z33", "J35:P41", "R35:Z41"];
  const rotulos = ["A21:A32", "D21:D32", "G21:G25", "J22:J33", "R22:R33", "J37:J41", "R37:R41"];

  for (const a1 of secoes) {
    R.push(fmt(sid, a1, { backgroundColorStyle: cs(E.secao), horizontalAlignment: "CENTER", verticalAlignment: "MIDDLE", wrapStrategy: "CLIP", textFormat: { fontFamily: FONTE_TITULO, fontSize: 11, bold: true, foregroundColorStyle: cs(C.branco) } }, "userEnteredFormat(backgroundColorStyle,horizontalAlignment,verticalAlignment,wrapStrategy,textFormat)"));
  }
  for (const a1 of cabecalhos) {
    R.push(fmt(sid, a1, { backgroundColorStyle: cs(E.cabecalho), horizontalAlignment: "CENTER", verticalAlignment: "MIDDLE", wrapStrategy: "WRAP", textFormat: { fontFamily: FONTE, fontSize: 9, bold: true, foregroundColorStyle: cs(E.cabecalhoTexto) } }, "userEnteredFormat(backgroundColorStyle,horizontalAlignment,verticalAlignment,wrapStrategy,textFormat)"));
  }
  for (const a1 of corpos) {
    R.push(fmt(sid, a1, { horizontalAlignment: "CENTER", textFormat: { fontFamily: FONTE, fontSize: 10, bold: false, foregroundColorStyle: cs(C.texto) } }, "userEnteredFormat(horizontalAlignment,textFormat)"));
    R.push({ addBanding: { bandedRange: { range: gr(sid, a1), rowProperties: { firstBandColorStyle: cs(C.branco), secondBandColorStyle: cs(C.zebra) } } } });
    R.push({ updateBorders: { range: gr(sid, a1), innerHorizontal: borda(C.linha), innerVertical: borda(C.linha) } });
  }
  for (const a1 of rotulos) {
    R.push(fmt(sid, a1, { horizontalAlignment: "LEFT", padding: { left: 8 }, textFormat: { fontFamily: FONTE, fontSize: 10, bold: true, foregroundColorStyle: cs(C.navy) } }, "userEnteredFormat(horizontalAlignment,padding,textFormat)"));
  }
  for (const a1 of cabecalhos) {
    R.push({ updateBorders: { range: gr(sid, a1), innerVertical: borda(C.branco) } });
  }
  // colunas espacadoras: tira tracos antigos soltos (so bordas internas, para nao apagar a borda das tabelas vizinhas)
  for (const a1 of ["C20:C41", "F20:F41", "I20:I41", "Q20:Q41"]) {
    R.push({ updateBorders: { range: gr(sid, a1), innerHorizontal: { style: "NONE" } } });
  }
  for (const a1 of tabelas) {
    const b = borda(C.cinzaAzul);
    R.push({ updateBorders: { range: gr(sid, a1), top: b, bottom: b, left: b, right: b } });
  }
  // separador fino antes da coluna de semana de Engajamento/Alcance: nada; colunas espacadoras ficam brancas
  R.push(rowsHeight(sid, 20, 20, 34));
  R.push(rowsHeight(sid, 35, 35, 34));
  R.push(rowsHeight(sid, 21, 21, 40));
  R.push(rowsHeight(sid, 36, 36, 40));
  R.push(rowsHeight(sid, 22, 33, 24));
  R.push(rowsHeight(sid, 37, 41, 26));
  R.push(rowsHeight(sid, 34, 34, 16));

  // ---- formatacao condicional (fica por cima da zebra) ----
  let idx = 0;
  const addCF = (rule) => R.push({ addConditionalFormatRule: { rule, index: idx++ } });
  // mes da aba em destaque nas tabelas anuais de 2026
  if (mesIndex >= 0) {
    const destaque = { backgroundColorStyle: cs(C.lilasClaro), textFormat: { bold: true, foregroundColorStyle: cs(C.navy) } };
    const linhasMes = [`D${21 + mesIndex}:E${21 + mesIndex}`, `J${22 + mesIndex}:P${22 + mesIndex}`, `R${22 + mesIndex}:Z${22 + mesIndex}`];
    addCF({ ranges: linhasMes.map((a) => gr(sid, a)), booleanRule: { condition: { type: "CUSTOM_FORMULA", values: [{ userEnteredValue: "=TRUE" }] }, format: destaque } });
  }
  // saldo negativo de seguidores em laranja
  addCF({ ranges: ["B21:B32", "E21:E32", "H21:H25"].map((a) => gr(sid, a)), booleanRule: { condition: { type: "NUMBER_LESS", values: [{ userEnteredValue: "0" }] }, format: { textFormat: { bold: true, foregroundColorStyle: cs(C.laranja) } } } });
  // gradiente nas semanas: alcance geral e engajamento
  for (const a1 of ["K37:K41", "S37:S41"]) {
    addCF({ ranges: [gr(sid, a1)], gradientRule: { minpoint: { type: "MIN", colorStyle: cs(C.branco) }, maxpoint: { type: "MAX", colorStyle: cs(C.lilas) } } });
  }

  // ---- graficos ----
  const titulo = { fontFamily: FONTE_TITULO, fontSize: 12, bold: true, foregroundColorStyle: cs(C.navy) };
  // rotulo "DATA" (valor do proprio ponto); o tipo CUSTOM com customLabelData da erro 500 na API
  const label = () => ({ type: "DATA", textFormat: { fontFamily: FONTE, fontSize: 9, bold: true, foregroundColorStyle: cs(C.navy) } });
  const eixos = [
    { position: "BOTTOM_AXIS", format: { fontFamily: FONTE, fontSize: 9, foregroundColorStyle: cs(C.textoSuave) } },
    { position: "LEFT_AXIS", format: { fontFamily: FONTE, fontSize: 9, foregroundColorStyle: cs(C.textoSuave) } },
  ];
  const src = (a1) => gr(sid, a1);
  const base = (t, sub) => ({ title: t, subtitle: sub || "", titleTextFormat: titulo, subtitleTextFormat: { fontFamily: FONTE, fontSize: 9, foregroundColorStyle: cs(C.textoSuave) }, titleTextPosition: { horizontalAlignment: "LEFT" }, subtitleTextPosition: { horizontalAlignment: "LEFT" }, fontName: FONTE, backgroundColorStyle: cs(C.branco), hiddenDimensionStrategy: "SKIP_HIDDEN_ROWS_AND_COLUMNS" });

  for (const ch of sh.charts || []) {
    // identifica pelo titulo; se o titulo foi mudado, pela coluna da 1a serie (B/E = anual, H = semanas, L = alcance)
    const s0 = ch.spec.basicChart && ch.spec.basicChart.series && ch.spec.basicChart.series[0];
    const col0 = s0 && s0.series.sourceRange.sources[0].startColumnIndex;
    const t = (ch.spec.title || "") + " " + ({ 1: "Seguidores Anual", 4: "Seguidores Anual", 7: "Seguidores Mensal", 11: "Contas alcan" }[col0] || "");
    let spec = null;
    if (/Seguidores Anual/i.test(t)) {
      spec = { ...base(`Seguidores Anual | ${handle}`, `Novos seguidores por mês  ·  ${marca === "arttico" ? `cinza ${anoAnt}  ·  azul-marinho ${anoAtual}` : `lavanda ${anoAnt}  ·  azul elétrico ${anoAtual}`}`), basicChart: {
        chartType: "LINE", legendPosition: "NO_LEGEND", axis: eixos, headerCount: 0,
        domains: [{ domain: { sourceRange: { sources: [src("D21:D32")] } } }],
        series: [
          { series: { sourceRange: { sources: [src("B21:B32")] } }, targetAxis: "LEFT_AXIS", colorStyle: cs(E.serieAnt), lineStyle: { width: 3, type: "SOLID" }, pointStyle: { size: 5 } },
          { series: { sourceRange: { sources: [src("E21:E32")] } }, targetAxis: "LEFT_AXIS", colorStyle: cs(E.serieAtual), lineStyle: { width: 3, type: "SOLID" }, pointStyle: { size: 6 }, dataLabel: { ...label(src("E21:E32")), placement: "ABOVE" } },
        ],
      } };
    } else if (/Seguidores Mensal/i.test(t)) {
      spec = { ...base(`Seguidores por semana | ${handle}`, "Saldo de seguidores (ganhos − perdas)"), basicChart: {
        chartType: "COLUMN", legendPosition: "NO_LEGEND", axis: eixos, headerCount: 0,
        domains: [{ domain: { sourceRange: { sources: [src("J37:J41")] } } }],
        series: [{ series: { sourceRange: { sources: [src("H21:H25")] } }, targetAxis: "LEFT_AXIS", colorStyle: cs(E.serieSeg), dataLabel: { ...label(src("H21:H25")), placement: "OUTSIDE_END" } }],
      } };
    } else if (/Contas alcan/i.test(t)) {
      spec = { ...base(`Contas alcançadas por semana | ${handle}`, "Alcance orgânico"), basicChart: {
        chartType: "COLUMN", legendPosition: "NO_LEGEND", axis: eixos, headerCount: 0,
        domains: [{ domain: { sourceRange: { sources: [src("J37:J41")] } } }],
        series: [{ series: { sourceRange: { sources: [src("L37:L41")] } }, targetAxis: "LEFT_AXIS", colorStyle: cs(E.serieAlc), dataLabel: { ...label(src("L37:L41")), placement: "OUTSIDE_END" } }],
      } };
    }
    if (spec) R.push({ updateChartSpec: { chartId: ch.chartId, spec } });
    // desce o grafico para a linha 3 (abaixo da faixa de titulo), mantendo a coluna
    const op = ch.position.overlayPosition;
    if (op) {
      R.push({ updateEmbeddedObjectPosition: { objectId: ch.chartId, newPosition: { overlayPosition: { ...op, anchorCell: { sheetId: sid, rowIndex: 2, columnIndex: op.anchorCell.columnIndex || 0 }, offsetYPixels: 10, heightPixels: 330 } }, fields: "*" } });
    }
  }

  // graficos vao em chamadas separadas: um erro num grafico nao derruba a formatacao das tabelas
  const ehGrafico = (q) => q.updateChartSpec || q.updateEmbeddedObjectPosition;
  const r = await post(`/v4/spreadsheets/${ID}:batchUpdate`, { requests: R.filter((q) => !ehGrafico(q)) });
  if (r.error) throw new Error("tabelas: " + JSON.stringify(r.error));
  for (const q of R.filter(ehGrafico)) {
    const rr = await post(`/v4/spreadsheets/${ID}:batchUpdate`, { requests: [q] });
    if (rr.error) console.log("Aviso grafico (" + Object.keys(q)[0] + " " + (q.updateChartSpec ? q.updateChartSpec.spec.title : q.updateEmbeddedObjectPosition.objectId) + "): " + rr.error.message);
  }
  console.log(`OK: "${tab}" (${marca}) formatada — ${R.length} operações, ${(sh.charts || []).length} gráficos.`);
}

main().catch((e) => { console.error("ERRO:", e.message); process.exit(1); });
