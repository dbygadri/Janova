"""Le cerveau de JANOVA : ses connaissances en notes Markdown reliées entre elles, lisibles dans Obsidian.

SQLite reste la mémoire de référence, protégée par le journal chaîné. Le cerveau en est le reflet vivant :
un dossier avec une note par compétence (c<id>) et par connaissance (f<id>), reliées par des liens [[...]],
une note d'accueil (Janova.md) et une vue graphe (graphe.html) qui s'ouvre dans n'importe quel navigateur.

Les liens viennent de trois sources :
- « proche » : JANOVA relie d'elle-même les éléments qui parlent de la même chose (mots en commun) ;
- « lien » : un lien choisi avec /lier, inscrit au journal ;
- « note » : un [[lien]] que tu écris dans la section « Mes notes » d'une note.

La section « Mes notes » est à toi : JANOVA la garde (même si le dossier est effacé), l'inscrit au journal
et suit les liens que tu y ajoutes. Le reste de chaque note est régénéré à partir de la mémoire.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from janova.store import Store
from janova.text import tokens

NOTES_HEADING = "## Mes notes"
NOTES_HINT = "<!-- Écris sous cette ligne : JANOVA garde ce texte et suit les [[liens]] que tu ajoutes. -->"
FOLDERS = {"competence": "competences", "connaissance": "connaissances"}
KEY = re.compile(r"^[cf]\d+$")
WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]")
UNSAFE = re.compile(r'[\\/:*?"<>|#^\[\]\n\r\t]+')
LINK_LABELS = {"lien": "lien choisi", "note": "lien de tes notes", "proche": "proche"}
LINK_PRIORITY = {"lien": 3, "note": 2, "proche": 1}


@dataclass
class Node:
    key: str  # c<id> ou f<id>
    kind: str  # competence ou connaissance
    title: str
    summary: str
    words: str  # texte servant à trouver les éléments proches
    body: str  # contenu Markdown propre à l'élément

    @property
    def stem(self) -> str:
        title = UNSAFE.sub(" ", self.title).strip(" .")
        return f"{self.key} {' '.join(title.split())[:60].rstrip()}".rstrip()

    @property
    def path(self) -> str:
        return f"{FOLDERS[self.kind]}/{self.stem}.md"


@dataclass
class Summary:
    notes: int
    links: int
    folder: Path


def collect_nodes(store: Store) -> list[Node]:
    nodes = []
    for s in store.skills():
        examples = "\n".join(f"- {e}" for e in s.examples)
        body = (
            f"{s.description}\n\n## Exemples\n{examples}\n\n## Code\n```python\n{s.code.rstrip()}\n```\n\n"
            f"Utilisée {s.uses} fois · 👍 {s.successes} / 👎 {s.failures}"
        )
        words = " ".join([s.name.replace("_", " "), s.description, *s.examples])
        nodes.append(Node(f"c{s.id}", "competence", s.name, s.description, words, body))
    for f in store.facts():
        agreement = f"{round(f.agreement * f.sources)}/{f.sources} professeurs d'accord"
        nodes.append(Node(f"f{f.id}", "connaissance", f.question, f.answer, f"{f.question} {f.answer}",
                          f"{f.answer}\n\n({agreement})"))
    return nodes


def note_links(text: str, nodes: list[Node]) -> set[str]:
    """Clés des éléments visés par les [[liens]] d'un texte (par clé, nom de fichier ou titre)."""
    by_name = {}
    for n in nodes:
        by_name[n.key] = by_name[n.stem.lower()] = by_name[n.title.lower()] = n.key
    found = set()
    for target in WIKILINK.findall(text):
        target = target.strip()
        first = target.split(" ", 1)[0]
        key = first if KEY.match(first) and first in by_name else by_name.get(target.lower())
        if key:
            found.add(key)
    return found


def build_links(store: Store, nodes: list[Node], neighbours: int, threshold: float) -> dict[tuple[str, str], str]:
    """Tous les liens du cerveau, sans doublon : {(clé, clé): sorte}. Le lien le plus fort l'emporte."""
    keys = {n.key for n in nodes}
    links: dict[tuple[str, str], str] = {}

    def add(a: str, b: str, kind: str) -> None:
        if a == b or a not in keys or b not in keys:
            return
        pair = (a, b) if a <= b else (b, a)
        if LINK_PRIORITY[kind] > LINK_PRIORITY.get(links.get(pair, ""), 0):
            links[pair] = kind

    # Proches : similarité des mots, calculée seulement entre éléments qui partagent au moins un mot.
    vectors = {n.key: Counter(t for t in tokens(n.words) if t != "<n>") for n in nodes}
    norms = {k: math.sqrt(sum(v * v for v in vec.values())) for k, vec in vectors.items()}
    index: dict[str, list[str]] = defaultdict(list)
    for key, vec in vectors.items():
        for token in vec:
            index[token].append(key)
    for key, vec in vectors.items():
        if not norms[key]:
            continue
        dots: Counter = Counter()
        for token, count in vec.items():
            for other in index[token]:
                if other != key:
                    dots[other] += count * vectors[other][token]
        scored = sorted(((d / (norms[key] * norms[o]), o) for o, d in dots.items()), reverse=True)
        for score, other in scored[:neighbours]:
            if score >= threshold:
                add(key, other, "proche")

    notes = store.notes()
    for n in nodes:
        for target in note_links(notes.get(n.key, ""), nodes):
            add(n.key, target, "note")
    for a, b in store.links():
        add(a, b, "lien")
    return links


def neighbours_of(key: str, links: dict[tuple[str, str], str]) -> list[tuple[str, str]]:
    return sorted((b if a == key else a, kind) for (a, b), kind in links.items() if key in (a, b))


class Brain:
    def __init__(self, store: Store, folder: Path, neighbours: int = 3, threshold: float = 0.3) -> None:
        self.store = store
        self.folder = Path(folder)
        self.neighbours = neighbours
        self.threshold = threshold

    def graph(self) -> tuple[list[Node], dict[tuple[str, str], str]]:
        nodes = collect_nodes(self.store)
        return nodes, build_links(self.store, nodes, self.neighbours, self.threshold)

    def sync(self) -> Summary:
        """Relit tes notes, puis réécrit le dossier du cerveau à partir de la mémoire."""
        for folder in FOLDERS.values():
            (self.folder / folder).mkdir(parents=True, exist_ok=True)
        existing = self._existing_notes()
        for key, (_, user_text) in existing.items():
            self.store.set_note(key, user_text)

        nodes, links = self.graph()
        notes = self.store.notes()
        by_key = {n.key: n for n in nodes}
        for n in nodes:
            target = self.folder / n.path
            old = existing.get(n.key, (None, ""))[0]
            if old is not None and old != target:
                old.unlink(missing_ok=True)
            self._write(target, self._render(n, links, by_key, notes.get(n.key, "")))
        for key, (path, _) in existing.items():
            if key not in by_key:
                path.unlink(missing_ok=True)

        self._write(self.folder / "Janova.md", self._render_index(nodes, links))
        self._write(self.folder / "graphe.html", render_graph(nodes, links, notes))
        return Summary(len(nodes), len(links), self.folder)

    # --- Lecture et écriture des notes ----------------------------------------------------------

    def _existing_notes(self) -> dict[str, tuple[Path, str]]:
        """Notes déjà écrites par JANOVA : {clé: (fichier, texte de « Mes notes »)}."""
        found = {}
        for folder in FOLDERS.values():
            for path in (self.folder / folder).glob("*.md"):
                key = path.stem.split(" ", 1)[0]
                if not KEY.match(key):
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                if text.startswith("---\njanova:"):
                    found[key] = (path, user_section(text))
        return found

    @staticmethod
    def _write(path: Path, content: str) -> None:
        # On ne réécrit que ce qui a changé, pour ne pas déranger Obsidian ni user la carte SD d'un téléphone ou d'un Pi.
        try:
            if path.read_text(encoding="utf-8") == content:
                return
        except (OSError, UnicodeDecodeError):
            pass
        path.write_text(content, encoding="utf-8")

    def _render(self, n: Node, links: dict, by_key: dict[str, Node], user_text: str) -> str:
        related = neighbours_of(n.key, links)
        lines = "\n".join(f"- [[{by_key[k].stem}]] · {LINK_LABELS[kind]}" for k, kind in related) or "- (aucun)"
        meta = json.dumps(n.title, ensure_ascii=False)
        return (
            f"---\njanova: {n.kind}\nid: {n.key}\ntitre: {meta}\ntags: [janova/{n.kind}]\n---\n"
            f"# {n.title}\n\n{n.body}\n\n## Liens\n{lines}\n\n"
            f"{NOTES_HEADING}\n{NOTES_HINT}\n{user_text}\n".rstrip() + "\n"
        )

    @staticmethod
    def _render_index(nodes: list[Node], links: dict) -> str:
        sections = []
        for kind, title in (("competence", "Compétences"), ("connaissance", "Connaissances")):
            items = "\n".join(f"- [[{n.stem}]]" for n in nodes if n.kind == kind) or "- (aucune pour l'instant)"
            sections.append(f"## {title}\n{items}")
        return (
            "---\njanova: index\n---\n# Le cerveau de JANOVA\n\n"
            f"{len(nodes)} éléments reliés par {len(links)} liens. Ouvre ce dossier dans Obsidian pour la vue "
            "graphe, ou `graphe.html` dans un navigateur.\n\n"
            "Chaque note est régénérée par JANOVA ; seule la section « Mes notes » est à toi.\n\n"
            + "\n\n".join(sections) + "\n"
        )


def user_section(text: str) -> str:
    _, found, rest = text.partition(f"\n{NOTES_HEADING}\n")
    if not found:
        return ""
    return "\n".join(line for line in rest.splitlines() if line.strip() != NOTES_HINT).strip()


# --- Vue graphe ---------------------------------------------------------------------------------

def render_graph(nodes: list[Node], links: dict[tuple[str, str], str], notes: dict[str, str]) -> str:
    data = {
        "nodes": [
            {"id": n.key, "kind": n.kind, "title": n.title, "summary": n.summary, "note": notes.get(n.key, "")}
            for n in nodes
        ],
        "links": [{"a": a, "b": b, "kind": kind} for (a, b), kind in sorted(links.items())],
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return GRAPH_HTML.replace("/*DATA*/null", payload)


GRAPH_HTML = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cerveau de JANOVA</title>
<style>
:root{--bg:#f6f5f1;--fg:#1d1d1b;--muted:#6b6a65;--panel:#ffffffee;--line:#c9c6bd;--skill:#2f6fde;--fact:#d9822b;--chosen:#1d1d1b}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--fg:#ecebe6;--muted:#9a988f;--panel:#1f1f1dee;--line:#45443f;--skill:#6f9cf0;--fact:#f0a85a;--chosen:#ecebe6}}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:var(--bg);color:var(--fg);font:15px/1.4 system-ui,sans-serif;overflow:hidden}
canvas{display:block;width:100vw;height:100vh;touch-action:none}
header{position:fixed;top:12px;left:12px;right:12px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;pointer-events:none}
header>*{pointer-events:auto}
h1,.legend{background:var(--panel);padding:4px 8px;border-radius:8px}
h1{font-size:16px;margin:0 8px 0 0}
input{flex:1;min-width:140px;max-width:320px;padding:8px 10px;border-radius:8px;border:1px solid var(--line);background:var(--panel);color:var(--fg);font:inherit}
.legend{font-size:13px;color:var(--muted);display:flex;gap:12px}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px;vertical-align:-1px}
#panel{position:fixed;right:12px;bottom:12px;width:min(360px,calc(100vw - 24px));max-height:50vh;overflow:auto;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;display:none;backdrop-filter:blur(6px)}
#panel h2{font-size:16px;margin:0 0 6px}#panel p{margin:6px 0;white-space:pre-wrap}
#panel .meta{color:var(--muted);font-size:13px}#panel ul{padding-left:18px;margin:6px 0}
#panel a{color:inherit;cursor:pointer;text-decoration:underline}
#empty{position:fixed;inset:0;display:none;place-items:center;color:var(--muted);text-align:center;padding:24px}
</style>
</head>
<body>
<header>
  <h1>Cerveau de JANOVA</h1>
  <input id="search" type="search" placeholder="Chercher une compétence, une connaissance…">
  <div class="legend"><span><span class="dot" style="background:var(--skill)"></span>compétence</span><span><span class="dot" style="background:var(--fact)"></span>connaissance</span></div>
</header>
<canvas id="c"></canvas>
<div id="panel"></div>
<div id="empty">JANOVA n'a encore rien appris.<br>Pose-lui des questions, puis tape /cerveau.</div>
<script>
const DATA = /*DATA*/null;
const LABELS = {lien: "lien choisi", note: "lien de tes notes", proche: "proche"};
const canvas = document.getElementById("c"), ctx = canvas.getContext("2d");
const panel = document.getElementById("panel"), search = document.getElementById("search");
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const nodes = DATA.nodes.map((n, i) => {
  const a = i * 2.39996, r = 30 * Math.sqrt(i + 1);
  return {...n, x: Math.cos(a) * r, y: Math.sin(a) * r, vx: 0, vy: 0, links: []};
});
const byId = Object.fromEntries(nodes.map(n => [n.id, n]));
const links = DATA.links.map(l => ({...l, a: byId[l.a], b: byId[l.b]})).filter(l => l.a && l.b);
links.forEach(l => { l.a.links.push(l); l.b.links.push(l); });
if (!nodes.length) document.getElementById("empty").style.display = "grid";

let view = {x: 0, y: 0, k: 1}, selected = null, filter = "", heat = 1, dpr = 1, drag = null;
function resize() {
  dpr = window.devicePixelRatio || 1;
  canvas.width = innerWidth * dpr; canvas.height = innerHeight * dpr;
}
addEventListener("resize", resize); resize();

function step() {
  if (heat < 0.002) return;
  for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
    const a = nodes[i], b = nodes[j];
    const dx = b.x - a.x, dy = b.y - a.y, d2 = dx * dx + dy * dy + 1;
    if (d2 > 90000) continue;
    const d = Math.sqrt(d2), f = Math.min(8, 2500 / d2) * heat / d;
    a.vx -= dx * f; a.vy -= dy * f; b.vx += dx * f; b.vy += dy * f;
  }
  for (const l of links) {
    const dx = l.b.x - l.a.x, dy = l.b.y - l.a.y, d = Math.hypot(dx, dy) || 1;
    const f = (d - 80) / d * 0.05 * heat;
    l.a.vx += dx * f; l.a.vy += dy * f; l.b.vx -= dx * f; l.b.vy -= dy * f;
  }
  for (const n of nodes) {
    n.vx -= n.x * 0.012 * heat; n.vy -= n.y * 0.012 * heat;
    if (n !== drag) { n.x += n.vx; n.y += n.vy; }
    n.vx *= 0.6; n.vy *= 0.6;
  }
  heat *= 0.99;
}

function fit() {
  if (!nodes.length) return;
  const xs = nodes.map(n => n.x), ys = nodes.map(n => n.y);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const top = 96, w = innerWidth, h = innerHeight - top;
  view.k = Math.min(1.6, Math.max(0.2, Math.min(w / (x1 - x0 + 160), h / (y1 - y0 + 120))));
  view.x = -(x0 + x1) / 2 * view.k;
  view.y = top / 2 - (y0 + y1) / 2 * view.k;
}

const matches = n => !filter || (n.title + " " + n.summary + " " + n.note).toLowerCase().includes(filter);
const radius = n => 6 + Math.min(10, n.links.length * 1.5);
function draw() {
  step();
  const w = canvas.width, h = canvas.height;
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, w, h);
  ctx.setTransform(view.k * dpr, 0, 0, view.k * dpr, w / 2 + view.x * dpr, h / 2 + view.y * dpr);
  const near = selected ? new Set([selected, ...selected.links.flatMap(l => [l.a, l.b])]) : null;
  for (const l of links) {
    const lit = near && (l.a === selected || l.b === selected);
    ctx.globalAlpha = near && !lit ? 0.15 : 0.8;
    ctx.strokeStyle = l.kind === "proche" ? css("--line") : css("--chosen");
    ctx.lineWidth = (lit ? 2.2 : 1.2) / view.k;
    ctx.setLineDash(l.kind === "note" ? [5 / view.k, 4 / view.k] : []);
    ctx.beginPath(); ctx.moveTo(l.a.x, l.a.y); ctx.lineTo(l.b.x, l.b.y); ctx.stroke();
  }
  ctx.setLineDash([]);
  for (const n of nodes) {
    const dim = (near && !near.has(n)) || !matches(n);
    ctx.globalAlpha = dim ? 0.2 : 1;
    ctx.fillStyle = css(n.kind === "competence" ? "--skill" : "--fact");
    ctx.beginPath(); ctx.arc(n.x, n.y, radius(n), 0, 7); ctx.fill();
    if (n === selected) { ctx.strokeStyle = css("--fg"); ctx.lineWidth = 2 / view.k; ctx.stroke(); }
    if (view.k > 0.6 || n === selected) {
      ctx.fillStyle = css("--fg"); ctx.font = `${12 / Math.max(view.k, 0.8)}px system-ui,sans-serif`;
      ctx.textAlign = "center";
      const label = n.title.length > 34 ? n.title.slice(0, 32) + "…" : n.title;
      ctx.fillText(label, n.x, n.y + radius(n) + 13 / Math.max(view.k, 0.8));
    }
  }
  ctx.globalAlpha = 1;
  requestAnimationFrame(draw);
}

const esc = s => s.replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
function show(n) {
  selected = n;
  if (!n) { panel.style.display = "none"; return; }
  const items = n.links.map(l => { const o = l.a === n ? l.b : l.a;
    return `<li><a data-id="${o.id}">${esc(o.title)}</a> <span class="meta">· ${LABELS[l.kind]}</span></li>`; }).join("");
  panel.innerHTML = `<div class="meta">${n.kind} · ${n.id}</div><h2>${esc(n.title)}</h2><p>${esc(n.summary)}</p>`
    + (n.note ? `<p class="meta">Mes notes</p><p>${esc(n.note)}</p>` : "")
    + `<p class="meta">Liens</p><ul>${items || "<li>aucun</li>"}</ul>`;
  panel.style.display = "block";
}
panel.addEventListener("click", e => { const id = e.target.dataset.id; if (id) { show(byId[id]); view.x = -byId[id].x * view.k; view.y = -byId[id].y * view.k; } });
search.addEventListener("input", () => { filter = search.value.trim().toLowerCase(); });

const world = (px, py) => ({x: (px - innerWidth / 2 - view.x) / view.k, y: (py - innerHeight / 2 - view.y) / view.k});
const hit = (px, py) => { const p = world(px, py);
  return nodes.find(n => Math.hypot(n.x - p.x, n.y - p.y) < radius(n) + 4 / view.k); };
let pan = null, moved = false;
const pointers = new Map(); let pinch = null;
canvas.addEventListener("pointerdown", e => {
  canvas.setPointerCapture(e.pointerId); pointers.set(e.pointerId, e); moved = false;
  if (pointers.size === 2) { const [a, b] = [...pointers.values()];
    pinch = {d: Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY), k: view.k}; drag = pan = null; return; }
  drag = hit(e.clientX, e.clientY);
  if (!drag) pan = {x: e.clientX - view.x, y: e.clientY - view.y};
});
canvas.addEventListener("pointermove", e => {
  if (!pointers.has(e.pointerId)) return;
  pointers.set(e.pointerId, e); moved = true;
  if (pinch && pointers.size === 2) { const [a, b] = [...pointers.values()];
    view.k = Math.min(4, Math.max(0.2, pinch.k * Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY) / pinch.d)); return; }
  if (drag) { const p = world(e.clientX, e.clientY); drag.x = p.x; drag.y = p.y; heat = Math.max(heat, 0.3); }
  else if (pan) { view.x = e.clientX - pan.x; view.y = e.clientY - pan.y; }
});
const release = e => {
  pointers.delete(e.pointerId);
  if (!moved && !pinch) show(hit(e.clientX, e.clientY) || null);
  if (pointers.size < 2) pinch = null;
  drag = pan = null;
};
canvas.addEventListener("pointerup", release); canvas.addEventListener("pointercancel", release);
canvas.addEventListener("wheel", e => { e.preventDefault();
  view.k = Math.min(4, Math.max(0.2, view.k * (e.deltaY < 0 ? 1.1 : 0.9))); }, {passive: false});
for (let i = 0; i < 400; i++) step();
fit();
draw();
</script>
</body>
</html>
"""
