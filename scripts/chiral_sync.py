#!/usr/bin/env python3
"""
CHIRAL SYNC — sincroniza o README com a Rede Quiral (API do GitHub + clima).

Gera:
  assets/porter-card.svg       -> ID de porter com estatísticas reais
  assets/timefall.svg          -> previsão de "timefall" (clima real de Vitória da Conquista)
  assets/cargo/<repo>.svg      -> um card de carga animado por repositório público
E reescreve, no README.md, os blocos entre marcadores:
  <!--CARGO:START--> ... <!--CARGO:END-->
  <!--DELIVERIES:START--> ... <!--DELIVERIES:END-->
  <!--STRAND:START--> ... <!--STRAND:END-->

Sem dependências externas. Use GITHUB_TOKEN no ambiente para evitar rate limit.
Só repositórios PÚBLICOS entram no manifesto.
"""
import datetime as dt
import json
import math
import os
import re
import urllib.request
from html import escape
from pathlib import Path

USER = os.environ.get("PROFILE_USER", "Tepanniaky")
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
CARGO_DIR = ASSETS / "cargo"
README = ROOT / "README.md"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
LAT, LON, CITY = -14.8615, -40.8442, "VITÓRIA DA CONQUISTA"
TZ = dt.timezone(dt.timedelta(hours=-3))
NOW = dt.datetime.now(TZ)

# Ajustes manuais por repositório (texto curto + destino). Repos novos sem
# entrada aqui usam a descrição do próprio GitHub automaticamente.
OVERRIDES = {
    "Projeto-Brasa-Hackaton-NASA": {
        "title": "BRASA · NASA Space Apps",
        "desc": "Dados de satélite da NASA viram mapas e calendários do fogo na Bahia. Mais fogo, ou só enxergando melhor?",
        "dest": "NASA SPACE APPS 2026",
        "priority": 0,
    },
    "jujutsu-battle": {
        "title": "Jujutsu Battle",
        "desc": "Batalha por turnos com técnica, energia e regeneração. React no front, Spring Boot no back.",
        "dest": "ARENA FULL STACK",
        "priority": 1,
    },
    "Warm-memories-template": {
        "title": "Warm Memories",
        "desc": "Memórias navegáveis: carta animada, galeria, música e mapa Leaflet com marcadores de coração.",
        "dest": "TEMPLATE PÚBLICO",
        "priority": 2,
    },
    "api-filmes-avaliacoes": {
        "title": "API Filmes & Avaliações",
        "desc": "API REST com CRUD, filtros por gênero e ano e média de avaliações. Feita em equipe.",
        "dest": "API REST",
        "priority": 3,
    },
    "analisador-texto-flutter": {
        "title": "Analisador de Texto",
        "desc": "App Flutter em MVVM: login com SHA-256, SQLite local e estatísticas de leitura.",
        "dest": "MOBILE",
        "priority": 4,
    },
    "Consulta-de-Temperatura": {
        "title": "Consulta de Temperatura",
        "desc": "Clima em tempo real de qualquer cidade via WeatherAPI e Fetch.",
        "dest": "WEB",
        "priority": 5,
    },
    "Landing-page-inicial": {
        "title": "Landing Page",
        "desc": "Landing page responsiva fiel ao Figma, com busca interativa e carrossel.",
        "dest": "GITHUB PAGES",
        "priority": 6,
    },
}

LANG_COLORS = {
    "Python": "#3776ab", "TypeScript": "#3178c6", "JavaScript": "#f1e05a",
    "Java": "#ed8b00", "Dart": "#00b4ab", "HTML": "#e34c26", "CSS": "#663399",
    "Kotlin": "#a97bff", "Swift": "#f05138", "C++": "#f34b7d", "C": "#8a8a8a",
    "CMake": "#da3434", "Objective-C": "#438eff", "Shell": "#89e051",
    "Dockerfile": "#384d54",
}

STRANDS = [
    "Todo bug é só uma ponte que ainda não foi construída.",
    "Nenhum deploy é pesado demais quando a rota está bem planejada.",
    "Commit pequeno, passo firme. Carga grande, passo nenhum.",
    "Conectar pessoas é o propósito. O código é só a estrada.",
    "Quem documenta deixa escadas para o próximo porter.",
    "A chuva apaga o caminho, mas o git lembra de tudo.",
    "Teste antes de atravessar o rio. Sempre.",
    "Um README bem feito é um Like que dura para sempre.",
    "Nenhuma entrega é solitária: alguém sempre deixou uma ponte antes.",
    "Refatorar é reorganizar a carga para andar mais longe.",
    "Se o build caiu, levante. Equilíbrio é prática.",
    "Cada repositório é uma cidade reconectada à rede.",
]

WMO = {
    0: "CÉU LIMPO", 1: "POUCAS NUVENS", 2: "PARCIALMENTE NUBLADO", 3: "NUBLADO",
    45: "NEBLINA", 48: "NEBLINA GELADA", 51: "GAROA FRACA", 53: "GAROA", 55: "GAROA FORTE",
    61: "CHUVA FRACA", 63: "CHUVA", 65: "CHUVA FORTE", 80: "PANCADAS", 81: "PANCADAS FORTES",
    82: "TEMPESTADE", 95: "TROVOADA", 96: "TROVOADA C/ GRANIZO", 99: "TROVOADA SEVERA",
}

FONT = "'JetBrains Mono','Fira Code',Consolas,'Courier New',monospace"


# --------------------------------------------------------------------------- http
def get(url, gh=True):
    headers = {"User-Agent": "chiral-sync"}
    if gh:
        headers["Accept"] = "application/vnd.github+json"
        if TOKEN:
            headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode()), r.headers


def commit_count(full_name):
    try:
        data, headers = get(f"https://api.github.com/repos/{full_name}/commits?per_page=1")
    except Exception:
        return 0
    m = re.search(r'[?&]page=(\d+)>; rel="last"', headers.get("Link", "") or "")
    return int(m.group(1)) if m else len(data)


# ------------------------------------------------------------------------ helpers
def wrap(text, width, max_lines):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= width:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: width - 1].rstrip() + "…"
    return lines


def human_size(kb):
    return f"{kb / 1024:.1f} MB" if kb >= 1024 else f"{kb} KB"


def write_if_changed(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def replace_block(text, tag, new):
    pat = re.compile(rf"(<!--{tag}:START-->)(.*?)(<!--{tag}:END-->)", re.S)
    return pat.sub(lambda m: f"{m.group(1)}\n{new}\n{m.group(3)}", text)


# -------------------------------------------------------------------- cargo cards
def cargo_svg(cargo_id, repo, langs, commits, max_commits, in_transit):
    ov = OVERRIDES.get(repo["name"], {})
    title = ov.get("title") or repo["name"].replace("-", " ")
    desc = ov.get("desc") or repo.get("description") or "Carga sem manifesto. Abra para inspecionar."
    dest = ov.get("dest") or (repo.get("language") or "DESCONHECIDO").upper()
    lines = wrap(desc, 54, 2)
    status, scol = ("EM TRÂNSITO", "#f5a623") if in_transit else ("ENTREGUE", "#5ce1e6")
    pct = max(0.08, commits / max_commits) if max_commits else 0.08
    bar_w = round(300 * pct)

    chips, x = [], 24
    for lang in langs[:4]:
        w = 16 + len(lang) * 7.4
        col = LANG_COLORS.get(lang, "#8a7a62")
        chips.append(
            f'<g transform="translate({x:.0f},176)"><rect width="{w:.0f}" height="20" rx="10" fill="{col}" fill-opacity=".14" stroke="{col}" stroke-opacity=".6"/>'
            f'<circle cx="10" cy="10" r="3" fill="{col}"/><text x="18" y="14" class="chip">{escape(lang)}</text></g>'
        )
        x += w + 6

    desc_svg = "".join(
        f'<text x="24" y="{106 + i * 18}" class="desc">{escape(l)}</text>' for i, l in enumerate(lines)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="420" height="214" viewBox="0 0 420 214" role="img" aria-label="Carga {escape(title)}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#14100b"/><stop offset="1" stop-color="#07090c"/></linearGradient>
    <linearGradient id="fill" x1="0" x2="1"><stop offset="0" stop-color="#c48a1c"/><stop offset="1" stop-color="#ffd27a"/></linearGradient>
    <style>
      text{{font-family:{FONT}}}
      .id{{fill:#5ce1e6;font-size:10px;letter-spacing:2px}}
      .title{{fill:#f3ede2;font-size:19px;font-weight:700;font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif}}
      .desc{{fill:#a89a85;font-size:11.5px}}
      .lbl{{fill:#8a7a62;font-size:9.5px;letter-spacing:2px}}
      .val{{fill:#e8e2d6;font-size:10px;letter-spacing:1px}}
      .chip{{fill:#e8e2d6;font-size:10.5px}}
      .st{{font-size:9.5px;letter-spacing:2px;font-weight:700}}
      .bar{{animation:grow 1.6s cubic-bezier(.2,.8,.2,1) .3s both;transform-origin:24px 0}}
      @keyframes grow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
      .scan{{fill:#f5a623;opacity:.07;animation:scan 4s linear infinite}}
      @keyframes scan{{from{{transform:translateY(-30px)}}to{{transform:translateY(230px)}}}}
      .dot{{animation:blink 1.4s steps(1) infinite}}
      @keyframes blink{{50%{{opacity:.15}}}}
    </style>
    <clipPath id="c"><rect width="420" height="214" rx="10"/></clipPath>
  </defs>
  <g clip-path="url(#c)">
    <rect width="420" height="214" fill="url(#bg)"/>
    <rect class="scan" width="420" height="24"/>
  </g>
  <rect x=".5" y=".5" width="419" height="213" rx="10" fill="none" stroke="#3a2a10"/>
  <path d="M8 26 V8 H26 M394 8 H412 V26 M8 188 V206 H26 M412 188 V206 H394" stroke="#f5a623" stroke-width="1.6" fill="none"/>
  <text x="24" y="34" class="id">{cargo_id} ▸ {escape(dest)}</text>
  <g transform="translate(396,34)" text-anchor="end">
    <circle class="dot" cx="-{len(status) * 7.9 + 8:.0f}" cy="-3.5" r="3.5" fill="{scol}"/>
    <text class="st" fill="{scol}">{status}</text>
  </g>
  <text x="24" y="72" class="title">{escape(title)}</text>
  {desc_svg}
  <text x="24" y="156" class="lbl">COMMITS</text>
  <rect x="94" y="149" width="230" height="6" rx="3" fill="#2a2015"/>
  <rect class="bar" x="94" y="149" width="{bar_w * 230 // 300}" height="6" rx="3" fill="url(#fill)"/>
  <text x="396" y="156" class="val" text-anchor="end">{commits} · {human_size(repo.get("size", 0))}</text>
  {"".join(chips)}
</svg>
"""


# -------------------------------------------------------------------- porter card
def porter_svg(stats):
    level = max(1, int(math.sqrt(stats["commits"])))
    nxt = (level + 1) ** 2
    cur = level ** 2
    xp = (stats["commits"] - cur) / max(1, nxt - cur)
    rows = [
        ("ENTREGAS PÚBLICAS", stats["repos"], 20),
        ("COMMITS TRANSPORTADOS", stats["commits"], max(400, stats["commits"])),
        ("LIKES RECEBIDOS", stats["likes"], max(50, stats["likes"])),
        ("LINGUAGENS NA MOCHILA", stats["langs"], 15),
        ("DIAS NA REDE QUIRAL", stats["days"], max(1000, stats["days"])),
    ]
    bars = []
    for i, (label, val, cap) in enumerate(rows):
        y = 70 + i * 34
        w = round(260 * min(1, val / cap)) if cap else 0
        bars.append(
            f'<text x="440" y="{y}" class="lbl">{label}</text>'
            f'<text x="796" y="{y}" class="num" text-anchor="end">{val}</text>'
            f'<rect x="440" y="{y + 8}" width="356" height="5" rx="2.5" fill="#2a2015"/>'
            f'<rect class="bar" style="animation-delay:{0.2 + i * 0.15:.2f}s" x="440" y="{y + 8}" width="{max(6, round(356 * w / 260))}" height="5" rx="2.5" fill="url(#fill)"/>'
        )
    stars = "★" * min(5, 1 + level // 5) + "☆" * (5 - min(5, 1 + level // 5))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="840" height="250" viewBox="0 0 840 250" role="img" aria-label="Porter ID: nível {level}, {stats['repos']} entregas públicas, {stats['commits']} commits">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1a1208"/><stop offset=".6" stop-color="#0a0c10"/><stop offset="1" stop-color="#07090c"/></linearGradient>
    <linearGradient id="fill" x1="0" x2="1"><stop offset="0" stop-color="#c48a1c"/><stop offset="1" stop-color="#ffd27a"/></linearGradient>
    <style>
      text{{font-family:{FONT}}}
      .lbl{{fill:#8a7a62;font-size:10.5px;letter-spacing:2px}}
      .num{{fill:#ffd27a;font-size:13px;font-weight:700}}
      .k{{fill:#5ce1e6;font-size:10px;letter-spacing:3px}}
      .name{{fill:#f3ede2;font-size:30px;font-weight:800;letter-spacing:6px;font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif}}
      .v{{fill:#e8e2d6;font-size:12px;letter-spacing:1px}}
      .lvl{{fill:#f5a623;font-size:46px;font-weight:800;font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif}}
      .bar{{animation:grow 1.4s cubic-bezier(.2,.8,.2,1) both;transform-origin:440px 0}}
      .xp{{animation:grow 2s cubic-bezier(.2,.8,.2,1) .6s both;transform-origin:30px 0}}
      @keyframes grow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
      .holo{{animation:holo 3s ease-in-out infinite}}
      @keyframes holo{{0%,100%{{opacity:.85}}50%{{opacity:1}}}}
      .scan{{fill:#5ce1e6;opacity:.06;animation:scan 5s linear infinite}}
      @keyframes scan{{from{{transform:translateY(-30px)}}to{{transform:translateY(260px)}}}}
    </style>
    <clipPath id="c"><rect width="840" height="250" rx="12"/></clipPath>
  </defs>
  <g clip-path="url(#c)"><rect width="840" height="250" fill="url(#bg)"/><rect class="scan" width="840" height="30"/></g>
  <rect x=".5" y=".5" width="839" height="249" rx="12" fill="none" stroke="#3a2a10"/>
  <line x1="410" y1="30" x2="410" y2="220" stroke="#3a2a10"/>
  <g class="holo">
    <text x="30" y="40" class="k">▲ ID DE PORTER</text>
    <text x="30" y="84" class="name">ZÉ FILHO</text>
    <text x="30" y="108" class="v">@{USER} · {stars}</text>
    <text x="30" y="138" class="lbl">CLASSE</text><text x="120" y="138" class="v">FULL STACK EM FORMAÇÃO</text>
    <text x="30" y="160" class="lbl">ORIGEM</text><text x="120" y="160" class="v">{CITY} · BA</text>
    <text x="30" y="182" class="lbl">BASE</text><text x="120" y="182" class="v">SISTEMAS DE INFORMAÇÃO</text>
  </g>
  <text x="380" y="92" class="lvl" text-anchor="end">{level}</text>
  <text x="380" y="40" class="k" text-anchor="end">NÍVEL</text>
  <text x="30" y="212" class="lbl">XP ATÉ O NÍVEL {level + 1}</text>
  <rect x="30" y="220" width="350" height="5" rx="2.5" fill="#2a2015"/>
  <rect class="xp" x="30" y="220" width="{max(6, round(350 * xp))}" height="5" rx="2.5" fill="#5ce1e6"/>
  <text x="440" y="40" class="k">ESTATÍSTICAS DE ENTREGA</text>
  {"".join(bars)}
  <text x="810" y="238" class="lbl" text-anchor="end" style="font-size:8.5px">SINCRONIZADO {NOW:%d/%m/%Y %H:%M} BRT</text>
</svg>
"""


# ---------------------------------------------------------------------- timefall
def timefall_svg():
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}"
        "&current=temperature_2m,precipitation,weather_code,wind_speed_10m"
        "&daily=precipitation_probability_max&timezone=America%2FBahia&forecast_days=1"
    )
    w, _ = get(url, gh=False)
    cur = w["current"]
    prob = (w.get("daily", {}).get("precipitation_probability_max") or [0])[0] or 0
    temp, wind, code = cur["temperature_2m"], cur["wind_speed_10m"], cur["weather_code"]
    cond = WMO.get(code, "CONDIÇÃO DESCONHECIDA")
    if prob < 25:
        risk, col, tip, drops = "BAIXO", "#5ce1e6", "Rota livre. Bom dia para fazer deploy.", 6
    elif prob < 60:
        risk, col, tip, drops = "MODERADO", "#f5a623", "Leve o guarda-chuva e faça commits pequenos.", 16
    else:
        risk, col, tip, drops = "ALTO", "#ff4d6d", "Timefall forte. Fique no abrigo e escreva testes.", 30

    rain = "".join(
        f'<line class="r" x1="{(i * 53) % 840}" y1="0" x2="{(i * 53) % 840 - 8}" y2="18" style="animation-delay:-{(i * 0.37) % 1.4:.2f}s"/>'
        for i in range(drops)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="840" height="150" viewBox="0 0 840 150" role="img" aria-label="Previsão de timefall: risco {risk}, {temp} graus, {prob}% de chuva">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0d1218"/><stop offset="1" stop-color="#07090c"/></linearGradient>
    <style>
      text{{font-family:{FONT}}}
      .r{{stroke:#9fb4c4;stroke-width:1.2;opacity:.35;animation:fall 1.4s linear infinite}}
      @keyframes fall{{from{{transform:translate(0,-30px)}}to{{transform:translate(-40px,170px)}}}}
      .k{{fill:#5ce1e6;font-size:10px;letter-spacing:3px}}
      .big{{fill:#f3ede2;font-size:34px;font-weight:800;font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif}}
      .lbl{{fill:#8a7a62;font-size:10px;letter-spacing:2px}}
      .v{{fill:#e8e2d6;font-size:12px}}
      .risk{{fill:{col};font-size:22px;font-weight:800;letter-spacing:4px;animation:pulse 2s ease-in-out infinite}}
      @keyframes pulse{{50%{{opacity:.55}}}}
    </style>
    <clipPath id="c"><rect width="840" height="150" rx="12"/></clipPath>
  </defs>
  <g clip-path="url(#c)"><rect width="840" height="150" fill="url(#bg)"/>{rain}</g>
  <rect x=".5" y=".5" width="839" height="149" rx="12" fill="none" stroke="#1f2a36"/>
  <text x="28" y="34" class="k">☂ PREVISÃO DE TIMEFALL · {CITY}</text>
  <text x="28" y="82" class="big">{temp:.0f}°C</text>
  <text x="130" y="66" class="v">{cond}</text>
  <text x="130" y="86" class="lbl">VENTO {wind:.0f} KM/H · CHUVA {prob}%</text>
  <text x="28" y="122" class="v">» {escape(tip)}</text>
  <text x="812" y="34" class="lbl" text-anchor="end">RISCO DE TIMEFALL</text>
  <text x="812" y="72" class="risk" text-anchor="end">{risk}</text>
  <text x="812" y="122" class="lbl" text-anchor="end" style="font-size:8.5px">ATUALIZADO {NOW:%d/%m %H:%M} BRT · OPEN-METEO</text>
</svg>
"""


# -------------------------------------------------------------------------- main
def main():
    user, _ = get(f"https://api.github.com/users/{USER}")
    repos, _ = get(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&sort=pushed")
    repos = [r for r in repos if not r["private"] and not r["fork"] and r["name"] != USER]

    all_langs, total_commits, total_stars = set(), 0, 0
    enriched = []
    for r in repos:
        langs_map, _ = get(r["languages_url"])
        langs = sorted(langs_map, key=langs_map.get, reverse=True)
        c = commit_count(r["full_name"])
        all_langs.update(langs)
        total_commits += c
        total_stars += r["stargazers_count"]
        pushed = dt.datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00"))
        enriched.append((r, langs, c, pushed))

    enriched.sort(key=lambda e: (OVERRIDES.get(e[0]["name"], {}).get("priority", 99), -e[3].timestamp()))
    max_c = max((e[2] for e in enriched), default=1)

    CARGO_DIR.mkdir(parents=True, exist_ok=True)
    keep = set()
    cells = []
    for i, (r, langs, c, pushed) in enumerate(enriched, 1):
        cid = f"BR-{i:02d}"
        in_transit = (NOW - pushed).days < 30
        fname = f"{r['name']}.svg"
        keep.add(fname)
        write_if_changed(CARGO_DIR / fname, cargo_svg(cid, r, langs, c, max_c, in_transit))
        demo = f' · <a href="{r["homepage"]}">🌐 demo</a>' if r.get("homepage") else ""
        cells.append(
            f'<td width="50%" align="center"><a href="{r["html_url"]}"><img src="assets/cargo/{fname}" alt="{escape(r["name"])}" width="100%"/></a>'
            f'<br/><sub><a href="{r["html_url"]}">📦 abrir carga</a>{demo}</sub></td>'
        )
    for f in CARGO_DIR.glob("*.svg"):
        if f.name not in keep:
            f.unlink()

    rows = ["<table>"]
    for i in range(0, len(cells), 2):
        pair = cells[i:i + 2]
        if len(pair) == 1:
            pair[0] = pair[0].replace('<td width="50%"', '<td colspan="2"').replace('width="100%"/>', 'width="50%"/>')
        rows.append("<tr>" + "".join(pair) + "</tr>")
    rows.append("</table>")
    cargo_md = "\n".join(rows)

    log = ["```diff", f"# LOG DA REDE QUIRAL · sincronizado em {NOW:%d/%m/%Y %H:%M} BRT"]
    for r, _, c, pushed in sorted(enriched, key=lambda e: e[3], reverse=True)[:5]:
        local = pushed.astimezone(TZ)
        sign = "+" if (NOW - pushed).days < 30 else " "
        status = "EM TRÂNSITO" if sign == "+" else "ENTREGUE ✔"
        name = r["name"][:30]
        log.append(f"{sign} [{local:%d/%m/%Y %H:%M}] {name} {'.' * (32 - len(name))} {status}")
    log.append("```")
    deliveries_md = "\n".join(log)

    strand = STRANDS[NOW.timetuple().tm_yday % len(STRANDS)]
    strand_md = f"> 🧬 **Strand do dia** (muda todo dia, sorteado pelo Chiral Sync):\n> *“{strand}”*"

    created = dt.datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
    stats = {
        "repos": len(enriched),
        "commits": total_commits,
        "likes": user["followers"] + total_stars,
        "langs": len(all_langs),
        "days": (NOW - created).days,
    }
    write_if_changed(ASSETS / "porter-card.svg", porter_svg(stats))

    try:
        write_if_changed(ASSETS / "timefall.svg", timefall_svg())
    except Exception as e:  # clima fora do ar: mantém o último arquivo
        print(f"[timefall] mantendo versão anterior: {e}")

    text = README.read_text(encoding="utf-8")
    text = replace_block(text, "CARGO", cargo_md)
    text = replace_block(text, "DELIVERIES", deliveries_md)
    text = replace_block(text, "STRAND", strand_md)
    write_if_changed(README, text)
    print(f"[chiral-sync] ok · {stats}")


if __name__ == "__main__":
    main()
