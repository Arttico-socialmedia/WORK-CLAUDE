"""Relatório semanal de demandas de clientes no kanban DESIGN do ClickUp.

Roda toda sexta às 18h pelo Agendador de Tarefas do Windows (ver agendar.ps1).
Gera relatorios/AAAA-MM-DD.md, guarda um resumo em dados/ e envia para o GitHub.

Uso:
  python relatorio.py              # gera o relatório e envia para o GitHub
  python relatorio.py --sem-push   # gera só o arquivo, sem commit/push
  python relatorio.py --descobrir  # lista espaços/pastas/listas do ClickUp (para achar o CRM)
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


def carregar_clientes(config, token):
    nomes = [l.strip() for l in (PASTA / "clientes.txt").read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.startswith("#")]
    if config.get("crm_list_id"):
        for t in buscar_tarefas(config["crm_list_id"], token):
            nomes.append(t["name"])
    vistos, clientes = set(), []
    for nome in nomes:
        chave = normalizar(nome)
        if chave and chave not in vistos:
            vistos.add(chave)
            clientes.append((nome, chave))
    return clientes


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

def analisar(tarefa, tis, config, agora):
    status = tarefa["status"]["status"]
    s_norm = normalizar(status)
    finalizados = {normalizar(s) for s in config["status_finalizados"]}
    s_analise = normalizar(config["status_analise"])
    criada = ms_para_dt(tarefa.get("date_created"))
    concluida = ms_para_dt(tarefa.get("date_done") or tarefa.get("date_closed"))
    finalizada = s_norm in finalizados or tarefa["status"].get("type") in ("done", "closed")

    tempos = {}  # minutos por status
    if tis:
        for h in tis.get("status_history", []):
            tempos[normalizar(h["status"])] = h.get("total_time", {}).get("by_minute", 0)
        atual = tis.get("current_status") or {}
        if atual and normalizar(atual.get("status")) not in tempos:
            tempos[normalizar(atual["status"])] = atual.get("total_time", {}).get("by_minute", 0)

    if finalizada:
        if criada and concluida:
            ciclo = (concluida - criada).total_seconds() / 60
        else:
            ciclo = sum(v for k, v in tempos.items() if k not in finalizados) or None
    else:
        ciclo = (agora - criada).total_seconds() / 60 if criada else None

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
        "analise_min": tempos.get(s_analise) if tis else None,
        "em_analise": s_norm == s_analise,
        "tempo_status_atual_min": (tis or {}).get("current_status", {}).get("total_time", {}).get("by_minute"),
        "prazo": prazo,
        "atrasada": bool(prazo and not finalizada and prazo < agora),
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


def montar_relatorio(itens, sem_cliente, config, agora, inicio, anterior):
    fuso = config["fuso_utc"]
    lim_aberto = config["alerta_dias_aberto"] * 1440
    lim_analise = config["alerta_dias_analise"] * 1440
    abertas = sorted([i for i in itens if not i["finalizada"]], key=lambda i: -(i["ciclo_min"] or 0))
    feitas = [i for i in itens if i["finalizada"] and i["concluida"] and i["concluida"] >= inicio]
    em_analise = sorted([i for i in abertas if i["em_analise"]], key=lambda i: -(i["tempo_status_atual_min"] or 0))
    ja_passaram_analise = [i["analise_min"] for i in feitas if i["analise_min"]]

    resumo = {
        "data": agora.date().isoformat(),
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
    L.append(f"# Relatório de demandas de clientes — DESIGN")
    L.append(f"**Semana:** {fmt_data(inicio, fuso)} a {fmt_data(agora, fuso)}/{(agora + timedelta(hours=fuso)).year} · "
             f"gerado em {(agora + timedelta(hours=fuso)).strftime('%d/%m/%Y %H:%M')}\n")

    L.append("## Resumo")
    L.append("| Indicador | Valor |\n|---|---|")
    L.append(f"| Demandas em aberto | {resumo['abertas']} |")
    L.append(f"| Finalizadas na semana | {resumo['finalizadas_semana']} |")
    L.append(f"| Em análise agora | {resumo['em_analise_agora']} |")
    L.append(f"| Com prazo vencido | {resumo['atrasadas']} |")
    L.append(f"| **Tempo médio em análise** (finalizadas na semana) | **{dur(resumo['media_analise_min'])}**"
             f"{comparar(resumo['media_analise_min'], ant.get('media_analise_min'))} |")
    L.append(f"| Tempo médio até finalizar | {dur(resumo['media_ciclo_min'])}"
             f"{comparar(resumo['media_ciclo_min'], ant.get('media_ciclo_min'))} |")
    L.append(f"| Idade média das demandas abertas | {dur(resumo['media_idade_abertas_min'])} |\n")

    alertas = []
    for i in em_analise:
        if (i["tempo_status_atual_min"] or 0) > lim_analise:
            alertas.append(f"- 🔴 **{link(i)}** está em análise há **{dur(i['tempo_status_atual_min'])}**")
    for i in abertas:
        if i["atrasada"]:
            alertas.append(f"- ⏰ **{link(i)}** passou do prazo ({fmt_data(i['prazo'], fuso)}) — status: {i['status']}")
        elif (i["ciclo_min"] or 0) > lim_aberto:
            alertas.append(f"- 🟠 **{link(i)}** está aberta há **{dur(i['ciclo_min'])}** — status: {i['status']}")
    L.append("## ⚠️ Pontos de atenção")
    L.append("\n".join(alertas) if alertas else "Nenhum alerta esta semana. 🎉")
    L.append(f"\n_Critérios: em análise há mais de {config['alerta_dias_analise']} dias, aberta há mais de "
             f"{config['alerta_dias_aberto']} dias ou com prazo vencido._\n")

    L.append("## 🔎 Em análise agora")
    if em_analise:
        L.append("| Demanda | Cliente | Há quanto tempo em análise | Total em análise | Prazo | Responsáveis |\n|---|---|---|---|---|---|")
        for i in em_analise:
            L.append(f"| {link(i)} | {i['cliente']} | {dur(i['tempo_status_atual_min'])} | {dur(i['analise_min'])} | "
                     f"{fmt_data(i['prazo'], fuso)} | {i['responsaveis']} |")
    else:
        L.append("Nenhuma demanda de cliente em análise neste momento.")
    L.append("")

    L.append("## 📂 Demandas em aberto (mais antigas primeiro)")
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
        L.append("Não entraram nos números acima. Se alguma for de cliente, inclua o nome dele no título "
                 "da tarefa ou adicione o cliente em `clientes.txt`.\n")
        for t in sem_cliente[:30]:
            L.append(f"- [{t['name']}]({t.get('url', '')}) — {t['status']['status']}")
        if len(sem_cliente) > 30:
            L.append(f"- … e mais {len(sem_cliente) - 30}")
        L.append("")

    if not ant:
        L.append("_Primeira semana registrada — a comparação com a semana anterior começa no próximo relatório._")
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


def enviar_github(arquivos, data):
    repo = PASTA.parent
    rel = [str(a.relative_to(repo)) for a in arquivos]
    subprocess.run(["git", "-C", str(repo), "add", "--", *rel], check=True)
    if subprocess.run(["git", "-C", str(repo), "diff", "--cached", "--quiet"]).returncode == 0:
        print("Nada novo para enviar.")
        return
    subprocess.run(["git", "-C", str(repo), "commit", "-m", f"relatório de demandas design: {data}", "--", *rel], check=True)
    subprocess.run(["git", "-C", str(repo), "pull", "--rebase", "--autostash"], check=False)
    subprocess.run(["git", "-C", str(repo), "push"], check=True)
    print("Enviado para o GitHub.")


def main():
    token = ler_token()
    if "--descobrir" in sys.argv:
        return descobrir(token)

    config = json.loads((PASTA / "config.json").read_text(encoding="utf-8"))
    agora = datetime.now(timezone.utc)
    inicio = agora - timedelta(days=7)
    clientes = carregar_clientes(config, token)

    tarefas = []
    for list_id in config["list_ids"]:
        tarefas += buscar_tarefas(list_id, token)

    finalizados = {normalizar(s) for s in config["status_finalizados"]}
    relevantes, sem_cliente = [], []
    for t in tarefas:
        fechada = normalizar(t["status"]["status"]) in finalizados or t["status"].get("type") in ("done", "closed")
        concluida = ms_para_dt(t.get("date_done") or t.get("date_closed"))
        if fechada and not (concluida and concluida >= inicio):
            continue  # finalizada antes desta semana
        cliente = identificar_cliente(t, clientes)
        if cliente:
            relevantes.append((t, cliente))
        elif not fechada and not re.search(r"\|\s*(arttico|tastto)\s*$", normalizar(t["name"])):
            sem_cliente.append(t)  # posts internos (título terminando em | ARTTICO / | TASTTO) ficam de fora

    tis = buscar_tempo_em_status([t["id"] for t, _ in relevantes], token)
    itens = []
    for t, cliente in relevantes:
        item = analisar(t, tis.get(t["id"]), config, agora)
        item["cliente"] = cliente
        itens.append(item)

    data = (agora + timedelta(hours=config["fuso_utc"])).date().isoformat()
    historico = sorted((PASTA / "dados").glob("*.json"))
    anterior = None
    for h in reversed(historico):
        if h.stem != data:
            anterior = json.loads(h.read_text(encoding="utf-8"))
            break

    texto, resumo = montar_relatorio(itens, sem_cliente, config, agora, inicio, anterior)
    if not tis and itens:
        texto = texto.replace("## Resumo", "> ⚠️ O recurso **Time in Status** do ClickUp não está ativo neste espaço, "
                              "então o tempo em análise não pôde ser medido. Ative em ClickApps → Time in Status.\n\n## Resumo", 1)

    arq_rel = PASTA / "relatorios" / f"{data}.md"
    arq_dados = PASTA / "dados" / f"{data}.json"
    arq_rel.write_text(texto, encoding="utf-8")
    arq_dados.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Relatório salvo em {arq_rel}")

    if "--sem-push" not in sys.argv:
        enviar_github([arq_rel, arq_dados], data)


if __name__ == "__main__":
    main()
