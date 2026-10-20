"""Relatório semanal de demandas de clientes no kanban DESIGN do ClickUp.

Roda toda sexta às 18h pelo Agendador de Tarefas do Windows (ver agendar.ps1).
Gera relatorios/AAAA-MM-DD.md, guarda um resumo em dados/ e envia para o GitHub.

Uso:
  python relatorio.py              # gera o relatório da semana (seg a sex) e envia para o GitHub
  python relatorio.py --semana 2026-10-14            # semana que contém essa data
  python relatorio.py --historico 2026-09-01 2026-10-16  # todas as semanas do período
  python relatorio.py --sem-push   # gera só o arquivo, sem commit/push
  python relatorio.py --descobrir  # lista espaços/pastas/listas do ClickUp (para achar o CRM)
  pythonw relatorio.py --agendado  # modo do Agendador: sem janela, registra tudo em logs/execucao.log
"""
import json
import re
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

PASTA = Path(__file__).resolve().parent
API = "https://api.clickup.com/api/v2"


# ---------- utilitários ----------

def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return " ".join(texto.lower().replace("'", "").split())


def ler_token():
    env = PASTA / ".env"
    if env.exists():
        for linha in env.read_text(encoding="utf-8").splitlines():
            if linha.startswith("CLICKUP_TOKEN="):
                token = linha.split("=", 1)[1].strip()
                if token and token != "cole_seu_token_aqui":
                    return token
    sys.exit("Token do ClickUp não configurado: cole o token no arquivo .env desta pasta.")


def api_get(caminho, params=None, token=None):
    url = f"{API}{caminho}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, headers={"Authorization": token})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def dur(minutos):
    if minutos is None:
        return "—"
    horas = minutos / 60
    if horas < 1:
        return f"{int(minutos)}min"
    if horas < 24:
        return f"{horas:.0f}h"
    dias, resto = divmod(horas, 24)
    return f"{int(dias)}d {int(resto)}h" if resto >= 1 else f"{int(dias)}d"


def media(valores):
    valores = [v for v in valores if v is not None]
    return sum(valores) / len(valores) if valores else None


def ms_para_dt(ms):
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc) if ms else None


# ---------- coleta ----------

def buscar_tarefas(list_id, token):
    tarefas, pagina = [], 0
    while True:
        dados = api_get(f"/list/{list_id}/task", {
            "include_closed": "true", "subtasks": "true", "archived": "false", "page": pagina,
        }, token)
        tarefas += dados.get("tasks", [])
        if dados.get("last_page", True) or not dados.get("tasks"):
            return tarefas
        pagina += 1


def buscar_tempo_em_status(ids, token):
    """Usa o 'Time in Status' do ClickUp. Retorna {} se o recurso não estiver ativo."""
    resultado = {}
    for i in range(0, len(ids), 100):
        try:
            resultado.update(api_get("/task/bulk_time_in_status/task_ids",
                                     {"task_ids": ids[i:i + 100]}, token))
        except urllib.error.HTTPError as erro:
            print(f"Aviso: Time in Status indisponível ({erro.code}). Usando datas das tarefas.")
            return {}
    return resultado


def ler_nomes(arquivo):
    """Lê um arquivo de nomes (um por linha, apelidos depois de '=') e devolve [(nome, chave_normalizada)]."""
    vistos, nomes = set(), []
    for linha in (PASTA / arquivo).read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        nome, _, apelidos = linha.partition("=")
        nome = nome.strip()
        for chave in [normalizar(nome)] + [normalizar(a) for a in apelidos.split(",")]:
            if chave and chave not in vistos:
                vistos.add(chave)
                nomes.append((nome, chave))
    return nomes


def carregar_clientes(config, token):
    clientes = ler_nomes("clientes.txt")
    if config.get("crm_list_id"):
        conhecidos = {c for _, c in clientes}
        for t in buscar_tarefas(config["crm_list_id"], token):
            if normalizar(t["name"]) not in conhecidos:
                clientes.append((t["name"], normalizar(t["name"])))
    return clientes


def eh_interna(t, ignorar):
    """Posts da Tastto/Arttico ("C | ..." e "E | ...") ou tarefas de quem não é cliente da Tastto."""
    if re.match(r"\s*[CE]\s*\|", t["name"]):
        return True
    return identificar_cliente(t, ignorar) is not None


def textos_da_tarefa(t):
    textos = [t.get("name", "")] + [tag.get("name", "") for tag in t.get("tags", [])]
    for campo in t.get("custom_fields", []):
        valor = campo.get("value")
        if valor in (None, ""):
            continue
        opcoes = (campo.get("type_config") or {}).get("options") or []
        if campo.get("type") == "drop_down":
            for op in opcoes:
                if str(op.get("orderindex")) == str(valor) or op.get("id") == valor:
                    textos.append(op.get("name", ""))
        elif campo.get("type") == "labels" and isinstance(valor, list):
            textos += [op.get("label") or op.get("name", "") for op in opcoes if op.get("id") in valor]
        elif isinstance(valor, str):
            textos.append(valor)
    return " | ".join(textos)


def identificar_cliente(t, clientes):
    so_palavras = lambda x: " " + " ".join(re.sub(r"[^a-z0-9]+", " ", x).split()) + " "
    texto = so_palavras(normalizar(textos_da_tarefa(t)))
    for nome, chave in sorted(clientes, key=lambda c: -len(c[1])):
        if so_palavras(chave) in texto:
            return nome
    return None


# ---------- análise ----------

def status_em(tis, ref):
    """Status da tarefa no momento ref, estimado pela última entrada em cada status. Devolve (status, desde)."""
    ref_ms = ref.timestamp() * 1000
    candidatos = []
    for h in (tis or {}).get("status_history", []):
        desde = (h.get("total_time") or {}).get("since")
        if desde and int(desde) <= ref_ms:
            candidatos.append((int(desde), h["status"]))
    if not candidatos:
        return None, None
    desde, status = max(candidatos)
    return status, ms_para_dt(desde)


def analisar(tarefa, tis, config, ref, ao_vivo):
    """Situação da tarefa no momento ref. ao_vivo=True usa o status atual do ClickUp (semana em andamento)."""
    finalizados = {normalizar(s) for s in config["status_finalizados"]}
    s_analise = normalizar(config["status_analise"])
    criada = ms_para_dt(tarefa.get("date_created"))
    concluida = ms_para_dt(tarefa.get("date_done") or tarefa.get("date_closed"))
    fechada_agora = normalizar(tarefa["status"]["status"]) in finalizados or tarefa["status"].get("type") in ("done", "closed")
    if fechada_agora and tis:
        # conclusão = primeira chegada a um status finalizado (feito ou finalizado), mesmo sem data no ClickUp
        entradas = [ms_para_dt(h["total_time"]["since"]) for h in tis.get("status_history", [])
                    if normalizar(h["status"]) in finalizados and (h.get("total_time") or {}).get("since")]
        if entradas:
            concluida = min(entradas + ([concluida] if concluida else []))
    finalizada = bool(concluida and concluida <= ref) or (ao_vivo and fechada_agora)

    tempos = {}  # minutos acumulados por status (até hoje)
    if tis:
        for h in tis.get("status_history", []):
            tempos[normalizar(h["status"])] = (h.get("total_time") or {}).get("by_minute", 0)
        atual = tis.get("current_status") or {}
        if atual and normalizar(atual.get("status")) not in tempos:
            tempos[normalizar(atual["status"])] = (atual.get("total_time") or {}).get("by_minute", 0)

    if ao_vivo or finalizada:
        status = tarefa["status"]["status"] if ao_vivo else config["status_finalizados"][-1]
        em_analise = ao_vivo and normalizar(status) == s_analise
        tempo_atual = (tis or {}).get("current_status", {}).get("total_time", {}).get("by_minute") if em_analise else None
        analise = tempos.get(s_analise) if tis else None
    else:
        # semana já encerrada: status no fim da semana, estimado pelo histórico
        status, desde = status_em(tis, ref)
        em_analise = normalizar(status) == s_analise
        tempo_atual = (ref - desde).total_seconds() / 60 if em_analise and desde else None
        analise = tempo_atual
        status = status or "—"

    if finalizada:
        if criada and concluida:
            ciclo = (concluida - criada).total_seconds() / 60
        else:
            ciclo = sum(v for k, v in tempos.items() if k not in finalizados) or None
    else:
        ciclo = (ref - criada).total_seconds() / 60 if criada else None

    prazo = ms_para_dt(tarefa.get("due_date"))
    return {
        "id": tarefa["id"],
        "nome": tarefa["name"],
        "url": tarefa.get("url", ""),
        "status": status,
        "finalizada": finalizada,
        "criada": criada,
        "concluida": concluida,
        "ciclo_min": ciclo,
        "analise_min": analise,
        "em_analise": em_analise,
        "tempo_status_atual_min": tempo_atual,
        "prazo": prazo,
        "atrasada": bool(prazo and not finalizada and prazo < ref),
        "responsaveis": ", ".join(a.get("username") or a.get("email", "") for a in tarefa.get("assignees", [])) or "—",
    }


# ---------- relatório ----------

def fmt_data(dt, fuso):
    return (dt + timedelta(hours=fuso)).strftime("%d/%m") if dt else "—"


def link(item):
    nome = item["nome"].replace("|", r"\|")
    return f"[{nome}]({item['url']})" if item["url"] else nome


def comparar(atual, anterior, menor_melhor=True):
    if atual is None or anterior is None:
        return ""
    diff = atual - anterior
    if abs(diff) < 60:
        return " (igual à semana passada)"
    melhor = (diff < 0) == menor_melhor
    return f" ({'▼' if diff < 0 else '▲'} {dur(abs(diff))} vs semana passada {'✅' if melhor else '⚠️'})"


def montar_relatorio(itens, sem_cliente, config, seg, sex, ao_vivo, anterior):
    fuso = config["fuso_utc"]
    lim_aberto = config["alerta_dias_aberto"] * 1440
    lim_analise = config["alerta_dias_analise"] * 1440
    abertas = sorted([i for i in itens if not i["finalizada"]], key=lambda i: -(i["ciclo_min"] or 0))
    feitas = [i for i in itens if i["finalizada"]]
    em_analise = sorted([i for i in abertas if i["em_analise"]], key=lambda i: -(i["tempo_status_atual_min"] or 0))
    ja_passaram_analise = [i["analise_min"] for i in feitas if i["analise_min"]]

    resumo = {
        "semana": f"{seg:%Y-%m-%d}_a_{sex:%Y-%m-%d}",
        "abertas": len(abertas),
        "finalizadas_semana": len(feitas),
        "em_analise_agora": len(em_analise),
        "atrasadas": sum(i["atrasada"] for i in abertas),
        "media_ciclo_min": media([i["ciclo_min"] for i in feitas]),
        "media_analise_min": media(ja_passaram_analise),
        "media_idade_abertas_min": media([i["ciclo_min"] for i in abertas]),
    }
    ant = anterior or {}

    L = []
    L.append(f"# Relatório de demandas de clientes Tastto — DESIGN")
    agora_local = datetime.now(timezone.utc) + timedelta(hours=fuso)
    L.append(f"**Semana:** segunda {seg:%d/%m} a sexta {sex:%d/%m/%Y} · gerado em {agora_local:%d/%m/%Y %H:%M}\n")
    if not ao_vivo:
        L.append("> Semana já encerrada, reconstruída pelo histórico do ClickUp. Finalizadas e tempos até finalizar "
                 "são exatos; o status das demandas abertas é o do fim da semana (sexta).\n")

    L.append("## Resumo")
    L.append("| Indicador | Valor |\n|---|---|")
    L.append(f"| Demandas em aberto | {resumo['abertas']} |")
    L.append(f"| Finalizadas na semana | {resumo['finalizadas_semana']} |")
    L.append(f"| Em análise {'agora' if ao_vivo else 'no fim da semana'} | {resumo['em_analise_agora']} |")
    L.append(f"| Com prazo vencido | {resumo['atrasadas']} |")
    L.append(f"| **Tempo médio em análise** (finalizadas na semana) | **{dur(resumo['media_analise_min'])}**"
             f"{comparar(resumo['media_analise_min'], ant.get('media_analise_min'))} |")
    L.append(f"| Tempo médio até finalizar | {dur(resumo['media_ciclo_min'])}"
             f"{comparar(resumo['media_ciclo_min'], ant.get('media_ciclo_min'))} |")
    L.append(f"| Idade média das demandas abertas | {dur(resumo['media_idade_abertas_min'])} |\n")

    alertas = []
    for i in em_analise:
        total = max(i["analise_min"] or 0, i["tempo_status_atual_min"] or 0)
        if total > lim_analise:
            if ao_vivo:
                alertas.append(f"- 🔴 **{link(i)}** já soma **{dur(total)}** em análise "
                               f"(está nela agora há {dur(i['tempo_status_atual_min'])})")
            else:
                alertas.append(f"- 🔴 **{link(i)}** estava em análise havia **{dur(total)}** no fim da semana")
    for i in abertas:
        if i["atrasada"]:
            alertas.append(f"- ⏰ **{link(i)}** passou do prazo ({fmt_data(i['prazo'], fuso)}) — status: {i['status']}")
        elif (i["ciclo_min"] or 0) > lim_aberto:
            alertas.append(f"- 🟠 **{link(i)}** está aberta há **{dur(i['ciclo_min'])}** — status: {i['status']}")
    L.append("## ⚠️ Pontos de atenção")
    L.append("\n".join(alertas) if alertas else "Nenhum alerta esta semana. 🎉")
    L.append(f"\n_Critérios: em análise há mais de {config['alerta_dias_analise']} dias, aberta há mais de "
             f"{config['alerta_dias_aberto']} dias ou com prazo vencido._\n")

    L.append("## 🔎 Em análise " + ("agora" if ao_vivo else "no fim da semana"))
    if em_analise:
        L.append("| Demanda | Cliente | Há quanto tempo em análise | Total em análise | Prazo | Responsáveis |\n|---|---|---|---|---|---|")
        for i in em_analise:
            L.append(f"| {link(i)} | {i['cliente']} | {dur(i['tempo_status_atual_min'])} | {dur(i['analise_min'])} | "
                     f"{fmt_data(i['prazo'], fuso)} | {i['responsaveis']} |")
    else:
        L.append("Nenhuma demanda de cliente em análise " + ("neste momento." if ao_vivo else "no fim da semana."))
    L.append("")

    L.append("## 📂 Demandas em aberto " + ("" if ao_vivo else "no fim da semana ") + "(mais antigas primeiro)")
    if abertas:
        L.append("| Demanda | Cliente | Status | Aberta há | Tempo em análise | Prazo | Responsáveis |\n|---|---|---|---|---|---|---|")
        for i in abertas:
            prazo = fmt_data(i["prazo"], fuso) + (" ⏰" if i["atrasada"] else "")
            L.append(f"| {link(i)} | {i['cliente']} | {i['status']} | {dur(i['ciclo_min'])} | {dur(i['analise_min'])} | "
                     f"{prazo} | {i['responsaveis']} |")
    else:
        L.append("Nenhuma demanda de cliente em aberto.")
    L.append("")

    L.append("## ✅ Finalizadas na semana")
    if feitas:
        L.append("| Demanda | Cliente | Tempo total | Tempo em análise | % do tempo em análise | Responsáveis |\n|---|---|---|---|---|---|")
        for i in sorted(feitas, key=lambda i: -(i["ciclo_min"] or 0)):
            pct = f"{100 * i['analise_min'] / i['ciclo_min']:.0f}%" if i["analise_min"] and i["ciclo_min"] else "—"
            L.append(f"| {link(i)} | {i['cliente']} | {dur(i['ciclo_min'])} | {dur(i['analise_min'])} | {pct} | {i['responsaveis']} |")
    else:
        L.append("Nenhuma demanda de cliente finalizada nesta semana.")
    L.append("")

    L.append("## 👥 Por cliente")
    clientes = sorted({i["cliente"] for i in abertas + feitas})
    if clientes:
        L.append("| Cliente | Em aberto | Finalizadas na semana | Tempo médio em análise | Tempo médio até finalizar |\n|---|---|---|---|---|")
        for c in clientes:
            ab = [i for i in abertas if i["cliente"] == c]
            fe = [i for i in feitas if i["cliente"] == c]
            L.append(f"| {c} | {len(ab)} | {len(fe)} | {dur(media([i['analise_min'] for i in fe + ab]))} | "
                     f"{dur(media([i['ciclo_min'] for i in fe]))} |")
    L.append("")

    L.append("## 🧑‍🎨 Por responsável")
    pessoas = {}
    for i in abertas + feitas:
        for p in i["responsaveis"].split(", "):
            pessoas.setdefault(p, []).append(i)
    if pessoas:
        L.append("| Responsável | Em aberto | Finalizadas na semana | Tempo médio até finalizar |\n|---|---|---|---|")
        for p, lst in sorted(pessoas.items()):
            fe = [i for i in lst if i["finalizada"]]
            L.append(f"| {p} | {len(lst) - len(fe)} | {len(fe)} | {dur(media([i['ciclo_min'] for i in fe]))} |")
    L.append("")

    if sem_cliente:
        L.append("## ❔ Demandas abertas sem cliente identificado")
        L.append("Não entraram nos números acima. Se alguma for de cliente da Tastto, inclua o nome dele no título "
                 "da tarefa ou adicione em `clientes.txt` (se não for, adicione em `ignorar.txt`).\n")
        for t in sem_cliente[:30]:
            L.append(f"- [{t['name']}]({t.get('url', '')}) — {t['status']['status']}")
        if len(sem_cliente) > 30:
            L.append(f"- … e mais {len(sem_cliente) - 30}")
        L.append("")

    if not ant:
        L.append("_Primeira semana registrada — sem semana anterior para comparar._")
    return "\n".join(L) + "\n", resumo


# ---------- execução ----------

def descobrir(token):
    for team in api_get("/team", token=token)["teams"]:
        print(f"Workspace: {team['name']} ({team['id']})")
        for esp in api_get(f"/team/{team['id']}/space", {"archived": "false"}, token)["spaces"]:
            print(f"  Espaço: {esp['name']} ({esp['id']})")
            for lst in api_get(f"/space/{esp['id']}/list", {"archived": "false"}, token)["lists"]:
                print(f"    Lista: {lst['name']} ({lst['id']})")
            for pasta in api_get(f"/space/{esp['id']}/folder", {"archived": "false"}, token)["folders"]:
                print(f"    Pasta: {pasta['name']} ({pasta['id']})")
                for lst in pasta.get("lists", []):
                    print(f"      Lista: {lst['name']} ({lst['id']})")


def git(*args, check=True):
    """Roda git sem abrir janela e sem nunca parar esperando senha (o agendamento roda escondido)."""
    import os
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    sem_janela = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    r = subprocess.run(["git", "-C", str(PASTA.parent), *args], env=env, creationflags=sem_janela,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    if r.stdout.strip() or r.stderr.strip():
        print((r.stdout + r.stderr).strip())
    if check and r.returncode != 0:
        raise RuntimeError(f"git {args[0]} falhou (código {r.returncode})")
    return r.returncode


def enviar_github(arquivos, data):
    rel = [str(a.relative_to(PASTA.parent)) for a in arquivos]
    git("add", "--", *rel)
    if git("diff", "--cached", "--quiet", "--", *rel, check=False) == 0:
        print("Nada novo para enviar.")
        return
    git("commit", "-m", f"relatório de demandas design: {data}", "--", *rel)
    git("pull", "--rebase", "--autostash", check=False)
    git("push")
    print("Enviado para o GitHub.")


def semana_de(dia):
    """Segunda e sexta da semana do dia."""
    seg = dia - timedelta(days=dia.weekday())
    return seg, seg + timedelta(days=4)


def semana_padrao(hoje):
    """Sexta, sábado ou domingo: a semana que está fechando. De segunda a quinta: a semana anterior
    (caso o computador estivesse desligado na sexta)."""
    return semana_de(hoje if hoje.weekday() >= 4 else hoje - timedelta(days=7))


def gerar_semana(seg, sex, tarefas, tis, config):
    fuso = config["fuso_utc"]
    agora = datetime.now(timezone.utc)
    inicio = datetime(seg.year, seg.month, seg.day, tzinfo=timezone.utc) - timedelta(hours=fuso)
    fim = datetime(sex.year, sex.month, sex.day, 23, 59, 59, tzinfo=timezone.utc) - timedelta(hours=fuso)
    ao_vivo = fim > agora
    ref = min(fim, agora)

    itens, sem_cliente = [], []
    for t, cliente in tarefas:
        criada = ms_para_dt(t.get("date_created"))
        if not criada or criada > ref:
            continue  # ainda não existia
        if cliente is None:
            fechada = t["status"].get("type") in ("done", "closed") or \
                normalizar(t["status"]["status"]) in {normalizar(x) for x in config["status_finalizados"]}
            if ao_vivo and not fechada:
                sem_cliente.append(t)
            continue
        item = analisar(t, tis.get(t["id"]), config, ref, ao_vivo)
        if item["finalizada"] and not (item["concluida"] and item["concluida"] >= inicio):
            continue  # finalizada antes desta semana
        item["cliente"] = cliente
        itens.append(item)

    nome = f"{seg:%Y-%m-%d}_a_{sex:%Y-%m-%d}"
    anteriores = sorted(h for h in (PASTA / "dados").glob("*_a_*.json") if h.stem < nome)
    anterior = json.loads(anteriores[-1].read_text(encoding="utf-8")) if anteriores else None

    texto, resumo = montar_relatorio(itens, sem_cliente, config, seg, sex, ao_vivo, anterior)
    if not tis and itens:
        texto = texto.replace("## Resumo", "> ⚠️ O recurso **Time in Status** do ClickUp não está ativo neste espaço, "
                              "então o tempo em análise não pôde ser medido. Ative em ClickApps → Time in Status.\n\n## Resumo", 1)
    arq_rel = PASTA / "relatorios" / f"{nome}.md"
    arq_dados = PASTA / "dados" / f"{nome}.json"
    arq_rel.parent.mkdir(exist_ok=True)
    arq_dados.parent.mkdir(exist_ok=True)
    arq_rel.write_text(texto, encoding="utf-8")
    arq_dados.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Relatório salvo em {arq_rel}")
    return [arq_rel, arq_dados]


def main():
    if "--agendado" in sys.argv:
        # Rodando escondido pelo Agendador do Windows: tudo vai para logs/execucao.log
        (PASTA / "logs").mkdir(exist_ok=True)
        log = open(PASTA / "logs" / "execucao.log", "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = log
        print()
        print(f"=== {datetime.now():%d/%m/%Y %H:%M} ===")
    token = ler_token()
    if "--descobrir" in sys.argv:
        return descobrir(token)

    config = json.loads((PASTA / "config.json").read_text(encoding="utf-8"))
    hoje = (datetime.now(timezone.utc) + timedelta(hours=config["fuso_utc"])).date()

    def data_arg(flag, n=1):
        return datetime.strptime(sys.argv[sys.argv.index(flag) + n], "%Y-%m-%d").date()

    # quais semanas gerar (sempre de segunda a sexta)
    if "--historico" in sys.argv:  # --historico AAAA-MM-DD AAAA-MM-DD
        semanas, seg = [], semana_de(data_arg("--historico"))[0]
        while seg <= data_arg("--historico", 2):
            semanas.append(semana_de(seg))
            seg += timedelta(days=7)
    elif "--semana" in sys.argv:  # --semana AAAA-MM-DD (qualquer dia da semana desejada)
        semanas = [semana_de(data_arg("--semana"))]
    else:
        semanas = [semana_padrao(hoje)]

    clientes = carregar_clientes(config, token)
    ignorar = ler_nomes("ignorar.txt")
    tarefas = []
    for list_id in config["list_ids"]:
        for t in buscar_tarefas(list_id, token):
            if re.match(r"\s*[CE]\s*\|", t["name"]):
                continue  # posts da Tastto/Arttico
            cliente = identificar_cliente(t, clientes)
            if not cliente and eh_interna(t, ignorar):
                continue  # cliente da Arttico, marca própria ou evento
            tarefas.append((t, cliente))
    tis = buscar_tempo_em_status([t["id"] for t, c in tarefas if c], token)

    arquivos = []
    for seg, sex in semanas:
        arquivos += gerar_semana(seg, sex, tarefas, tis, config)

    if "--sem-push" not in sys.argv:
        rotulo = f"{semanas[0][0]:%d/%m} a {semanas[-1][1]:%d/%m/%Y}"
        enviar_github(arquivos, rotulo)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
