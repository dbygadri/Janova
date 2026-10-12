"""Le noyau : la boucle de vie de JANOVA.

Pour chaque demande :
1. commande interne (/aide, /etat…) ;
2. compétence déjà apprise → exécutée seule, sans LLM ;
3. connaissance déjà apprise → répondue seule, sans LLM ;
4. sinon, JANOVA demande à son entourage. Elle apprend une compétence (code testé) si la demande s'y
   prête, mémorise une connaissance validée par consensus, ou se contente de converser.

Plus elle apprend, plus les étapes 2 et 3 répondent seules : c'est son taux d'autonomie.
"""

from __future__ import annotations

from dataclasses import dataclass

from janova.cerveau import KEY, LINK_LABELS, Brain, neighbours_of
from janova.config import Config
from janova.meaning import Meaning, build_embedder
from janova.sandbox import ALLOWED_IMPORTS, run_skill
from janova.store import Skill, Store
from janova.teachers import Entourage, TeacherError, build_teachers, extract_json
from janova.text import same_answer, similarity

AUTONOMOUS_ROUTES = ("competence", "memoire")
SKILL_ROUTES = ("competence", "apprend-competence")
FACT_ROUTES = ("memoire", "apprend-connaissance")
LEARNING_ROUTES = SKILL_ROUTES + FACT_ROUTES + ("professeur", "inconnu")

TEACHER_SYSTEM = (
    "Tu es un professeur qui aide JANOVA, une jeune IA locale, à apprendre. "
    "Réponds en français et respecte exactement le format demandé."
)

CLASSIFY_PROMPT = """Classe la demande ci-dessous dans UNE catégorie :
- "competence" : une tâche qu'un petit programme Python déterministe peut résoudre à partir du seul texte
  de la demande (calcul, conversion, dates, transformation de texte...). Une demande semblable avec
  d'autres valeurs doit pouvoir être traitée par le même programme.
- "connaissance" : une question factuelle dont la réponse est stable dans le temps.
- "conversation" : tout le reste (discussion, avis, créativité, actualité, informations personnelles).
Réponds uniquement avec ce JSON : {{"type": "competence" | "connaissance" | "conversation"}}
Demande : <<<{request}>>>"""

SKILL_PROMPT = """Écris une compétence Python pour JANOVA.
Elle doit traiter la demande ci-dessous ET toutes les demandes semblables avec d'autres valeurs ou
d'autres formulations.
Règles :
- définir au premier niveau `def run(demande: str) -> str`, qui lit les valeurs dans le texte et renvoie
  une réponse courte en texte ;
- Python standard uniquement ; seuls imports autorisés : {imports} ;
- interdits : fichiers, réseau, eval/exec, getattr, type, attributs ou noms commençant par "_" ;
- au moins 3 tests avec des formulations et des valeurs différentes ; "attendu" est EXACTEMENT la chaîne
  renvoyée par run.
Réponds uniquement avec ce JSON :
{{"nom": "...", "description": "...", "code": "...", "tests": [{{"entree": "...", "attendu": "..."}}]}}
Demande : <<<{request}>>>{errors}"""

FACT_PROMPT = """Réponds à cette question factuelle en une ou deux phrases, sans détour.
Si tu n'es pas sûr, réponds exactement : JE NE SAIS PAS.
Question : {request}"""

HELP = """Commandes :
  /aide              cette aide
  /etat              ce que JANOVA sait et son taux d'autonomie
  /competences       liste des compétences apprises
  /connaissances     liste des connaissances apprises
  /bon  /mauvais     ton avis sur la dernière réponse (elle en tient compte)
  /oublie c<id>      oublier une compétence (ex. /oublie c3) ; /oublie f<id> pour une connaissance
  /cerveau           mettre à jour le cerveau (notes reliées, à ouvrir dans Obsidian ou graphe.html)
  /liens c<id>       les éléments reliés à une compétence (ou f<id> pour une connaissance)
  /lier c1 f2        relier deux éléments ; /delier c1 f2 pour défaire le lien
  /journal           les derniers apprentissages inscrits dans le journal chaîné
  /verifier          vérifier que rien n'a été modifié en douce
  /professeurs       l'entourage configuré"""


_DEFAULT = object()


@dataclass
class Reply:
    text: str
    route: str  # commande, competence, memoire, apprend-competence, apprend-connaissance, professeur, inconnu


class Janova:
    def __init__(
        self, config: Config, entourage: Entourage | None = None, store: Store | None = None, embedder=_DEFAULT
    ) -> None:
        self.config = config
        self.store = store or Store(config.db_path)
        self.entourage = entourage or Entourage(build_teachers(config.teachers, config.teacher_timeout))
        self.meaning = Meaning(build_embedder(config.embedder) if embedder is _DEFAULT else embedder, self.store)
        self.brain = Brain(self.store, config.brain_dir, config.brain_neighbours, config.brain_link_threshold)

    def close(self) -> None:
        self.store.close()

    def handle(self, message: str) -> Reply:
        message = message.strip()
        if not message:
            return Reply("", "commande")
        head = self.store.head()
        if message.startswith("/"):
            reply = Reply(self._command(message), "commande")
        else:
            reply, ref = self._from_skill(message)
            if reply is None:
                reply, ref = self._from_memory(message)
            if reply is None:
                reply, ref = self._from_entourage(message)
            self.store.add_episode(message, reply.text, reply.route, ref)
        if self.config.brain_autosync and self.store.head() != head:
            self.sync_brain()  # quelque chose a été appris ou oublié : le cerveau suit
        return reply

    def sync_brain(self) -> str:
        try:
            summary = self.brain.sync()
        except OSError as exc:
            return f"Impossible d'écrire le cerveau dans {self.brain.folder} : {exc}"
        return (
            f"Cerveau à jour : {summary.notes} notes reliées par {summary.links} liens.\n"
            f"Dossier : {summary.folder} (à ouvrir comme coffre dans Obsidian)\n"
            f"Vue graphe : {summary.folder / 'graphe.html'}"
        )

    # --- Reconnaissance : mots et sens --------------------------------------------------------

    def _recognize(self, message: str, candidates: list[tuple], word_threshold: float):
        """Renvoie la clé du candidat le plus proche de `message`, ou None si aucun n'est assez proche.

        Chaque candidat est jugé sur ses mots et, si le modèle de sens répond, sur son sens. On garde
        celui qui dépasse le plus nettement l'un de ses deux seuils.
        """
        if not candidates:
            return None
        meanings = self.meaning.similarities(message, [text for _, text in candidates])
        best_key, best_margin = None, 1.0
        for i, (key, text) in enumerate(candidates):
            margin = similarity(message, text) / word_threshold
            if meanings is not None:
                margin = max(margin, meanings[i] / self.config.meaning_threshold)
            if margin >= best_margin:
                best_key, best_margin = key, margin
        return best_key

    # --- 2. Compétences -------------------------------------------------------------------------

    def _from_skill(self, message: str) -> tuple[Reply | None, int | None]:
        candidates = [(s, example) for s in self.store.skills() for example in s.examples]
        skill = self._recognize(message, candidates, self.config.skill_match_threshold)
        if skill is None:
            return None, None
        result = run_skill(skill.code, [message], self.config.sandbox_timeout)[0]
        if not result.ok or not result.output.strip():
            self._penalize(skill, f"échec d'exécution : {result.output}")
            return None, None
        self.store.skill_used(skill, message)
        return Reply(result.output, "competence"), skill.id

    def _penalize(self, skill: Skill, reason: str) -> None:
        skill = self.store.skill_feedback(skill.id, good=False)
        if skill.failures >= 2 and skill.failures > skill.successes:
            self.store.disable_skill(skill.id, reason)

    # --- 3. Connaissances -----------------------------------------------------------------------

    def _from_memory(self, message: str) -> tuple[Reply | None, int | None]:
        fact = self._recognize(message, [(f, f.question) for f in self.store.facts()], self.config.fact_match_threshold)
        if fact is None:
            return None, None
        return Reply(fact.answer + self._confidence_note(fact.sources, fact.agreement), "memoire"), fact.id

    @staticmethod
    def _confidence_note(sources: int, agreement: float) -> str:
        if sources < 2:
            return "\n(appris d'un seul professeur, non confirmé)"
        if agreement < 1:
            return f"\n({round(agreement * sources)}/{sources} professeurs d'accord)"
        return ""

    # --- 4. Apprendre de l'entourage ------------------------------------------------------------

    def _from_entourage(self, message: str) -> tuple[Reply, int | None]:
        if not self.entourage.teachers:
            return Reply("Je ne sais pas encore faire ça, et aucun professeur n'est configuré.", "inconnu"), None
        try:
            kind = self._classify(message)
            if kind == "competence":
                learned = self._learn_skill(message)
                if learned:
                    return learned
            if kind == "connaissance":
                return self._learn_fact(message)
            return self._converse(message), None
        except TeacherError as exc:
            return Reply(f"Je ne sais pas encore faire ça et je n'ai pas pu demander : {exc}", "inconnu"), None

    def _classify(self, message: str) -> str:
        answer, _ = self.entourage.ask_first(CLASSIFY_PROMPT.format(request=message), TEACHER_SYSTEM)
        try:
            return str(extract_json(answer).get("type", "conversation")).strip().lower()
        except TeacherError:
            return "conversation"

    def _learn_skill(self, message: str) -> tuple[Reply, int] | None:
        errors = ""
        for _ in range(self.config.max_learning_attempts):
            answer, teacher = self.entourage.ask_first(
                SKILL_PROMPT.format(imports=", ".join(sorted(ALLOWED_IMPORTS)), request=message, errors=errors),
                TEACHER_SYSTEM,
            )
            try:
                lesson = extract_json(answer)
                code = str(lesson["code"])
                tests = [(str(t["entree"]), str(t["attendu"])) for t in lesson.get("tests", [])]
            except (TeacherError, KeyError, TypeError) as exc:
                errors = f"\n\nTa réponse précédente était inutilisable ({exc}). Recommence."
                continue
            if len(tests) < 3:
                errors = "\n\nIl faut au moins 3 tests. Recommence."
                continue

            results = run_skill(code, [t[0] for t in tests] + [message], self.config.sandbox_timeout)
            failures = [
                f"- run({entree!r}) a donné {r.output!r} au lieu de {attendu!r}" if r.ok
                else f"- run({entree!r}) a échoué : {r.output}"
                for (entree, attendu), r in zip(tests, results)
                if not (r.ok and same_answer(r.output, attendu))
            ]
            final = results[-1]
            if not final.ok or not final.output.strip():
                failures.append(f"- run({message!r}) a échoué : {final.output}")
            if failures:
                errors = "\n\nTon code précédent :\n" + code + "\nProblèmes :\n" + "\n".join(failures) + "\nCorrige."
                continue

            skill = self.store.add_skill(
                name=str(lesson.get("nom", "competence")),
                description=str(lesson.get("description", "")),
                code=code,
                examples=[message] + [t[0] for t in tests],
                teacher=teacher,
            )
            return Reply(f"{final.output}\n(nouvelle compétence apprise : {skill.name})", "apprend-competence"), skill.id
        return None

    def _learn_fact(self, message: str) -> tuple[Reply, int | None]:
        result = self.entourage.consensus(FACT_PROMPT.format(request=message), TEACHER_SYSTEM)
        if result.agreement < 0.5:
            note = "\n(mes professeurs ne sont pas d'accord ou ne savent pas : je ne le mémorise pas)"
            return Reply(result.answer + note, "professeur"), None
        fact = self.store.add_fact(message, result.answer, result.sources, result.agreement)
        return Reply(result.answer + self._confidence_note(fact.sources, fact.agreement), "apprend-connaissance"), fact.id

    def _converse(self, message: str) -> Reply:
        history = "\n".join(
            f"Utilisateur : {e['request']}\nJANOVA : {e['answer']}"
            for e in self.store.recent_episodes(self.config.history_size)
        )
        prompt = (f"Conversation récente :\n{history}\n\n" if history else "") + f"Utilisateur : {message}\nJANOVA :"
        answer, _ = self.entourage.ask_first(
            prompt, "Tu parles au nom de JANOVA, une jeune IA locale qui apprend. Réponds en français, brièvement."
        )
        return Reply(answer, "professeur")

    # --- 1. Commandes ---------------------------------------------------------------------------

    def _command(self, message: str) -> str:
        name, _, arg = message[1:].partition(" ")
        name, arg = name.lower(), arg.strip()
        if name == "aide":
            return HELP
        if name == "etat":
            return self._status()
        if name == "competences":
            skills = self.store.skills()
            if not skills:
                return "Aucune compétence apprise pour l'instant."
            return "\n".join(
                f"c{s.id}  {s.name} : {s.description} (utilisée {s.uses} fois, 👍 {s.successes} / 👎 {s.failures})"
                for s in skills
            )
        if name == "connaissances":
            facts = self.store.facts()
            if not facts:
                return "Aucune connaissance apprise pour l'instant."
            return "\n".join(f"f{f.id}  {f.question} → {f.answer}" for f in facts)
        if name in ("bon", "mauvais"):
            return self._feedback(name == "bon")
        if name == "oublie":
            return self._forget(arg)
        if name == "journal":
            rows = self.store.journal()
            if not rows:
                return "Journal vide."
            return "\n".join(f"#{r['id']} {r['at']} {r['kind']} {r['payload']}  [{r['hash'][:12]}]" for r in rows)
        if name == "cerveau":
            return self.sync_brain()
        if name == "liens":
            return self._links(arg)
        if name in ("lier", "delier"):
            return self._link(arg, add=name == "lier")
        if name == "verifier":
            problems = self.store.verify()
            return "Intégrité vérifiée : rien n'a été modifié." if not problems else "\n".join(problems)
        if name == "professeurs":
            return "\n".join(t.name for t in self.entourage.teachers) or "Aucun professeur configuré."
        return f"Commande inconnue : /{name}\n\n{HELP}"

    def _status(self) -> str:
        counts = self.store.route_counts()
        total = sum(counts.get(r, 0) for r in LEARNING_ROUTES)
        alone = sum(counts.get(r, 0) for r in AUTONOMOUS_ROUTES)
        rate = f"{100 * alone / total:.0f} %" if total else "—"
        if self.meaning.active:
            sense = f"par le sens ({self.meaning.embedder.name}) et par les mots"
        elif self.meaning.embedder is not None:
            sense = f"par les mots seulement ({self.meaning.error})"
        else:
            sense = "par les mots seulement (aucun modèle de sens configuré)"
        return (
            f"Reconnaissance : {sense}\n"
            f"Compétences : {len(self.store.skills())}\n"
            f"Connaissances : {len(self.store.facts())}\n"
            f"Demandes traitées : {total}, dont {alone} sans aucun LLM\n"
            f"Taux d'autonomie : {rate}"
        )

    def _feedback(self, good: bool) -> str:
        episode = self.store.last_episode()
        if episode is None:
            return "Il n'y a pas encore de réponse à évaluer."
        self.store.set_feedback(episode["id"], 1 if good else -1)
        ref = episode["ref"]
        if episode["route"] in SKILL_ROUTES and ref and self.store.get_skill(ref):
            skill = self.store.get_skill(ref)
            if good:
                self.store.skill_feedback(skill.id, good=True)
                return f"Merci, je renforce la compétence « {skill.name} »."
            self._penalize(skill, "avis négatif")
            if not self.store.get_skill(skill.id).active:
                return f"Compris, j'abandonne la compétence « {skill.name} ». Je la réapprendrai autrement."
            return f"Compris, je note que la compétence « {skill.name} » s'est trompée."
        if episode["route"] in FACT_ROUTES and ref and not good:
            self.store.forget_fact(ref, "avis négatif")
            return "Compris, j'oublie cette connaissance."
        return "Merci, c'est noté."

    def _forget(self, arg: str) -> str:
        if len(arg) < 2 or arg[0] not in "cf" or not arg[1:].isdigit():
            return "Utilisation : /oublie c<id> (compétence) ou /oublie f<id> (connaissance)."
        item_id = int(arg[1:])
        if arg[0] == "c":
            return "Compétence oubliée." if self.store.disable_skill(item_id, "demande de l'utilisateur") else "Introuvable."
        return "Connaissance oubliée." if self.store.forget_fact(item_id, "demande de l'utilisateur") else "Introuvable."

    def _keys(self) -> dict[str, str]:
        return {f"c{s.id}": s.name for s in self.store.skills()} | {f"f{f.id}": f.question for f in self.store.facts()}

    def _links(self, arg: str) -> str:
        keys = self._keys()
        if arg not in keys:
            return "Utilisation : /liens c<id> ou /liens f<id> (voir /competences et /connaissances)."
        _, links = self.brain.graph()
        related = neighbours_of(arg, links)
        if not related:
            return f"« {keys[arg]} » n'est relié à rien pour l'instant."
        return f"{arg}  {keys[arg]}\n" + "\n".join(f"  → {k}  {keys[k]} ({LINK_LABELS[kind]})" for k, kind in related)

    def _link(self, arg: str, add: bool) -> str:
        parts = arg.split()
        keys = self._keys()
        if len(parts) != 2 or not all(KEY.match(p) for p in parts) or parts[0] == parts[1]:
            return "Utilisation : /lier c1 f2 (ou /delier c1 f2)."
        missing = [p for p in parts if p not in keys]
        if missing:
            return f"Introuvable : {', '.join(missing)}."
        a, b = parts
        if add:
            return f"Relié : {keys[a]} ↔ {keys[b]}." if self.store.add_link(a, b) else "Ces deux éléments sont déjà reliés."
        return "Lien défait." if self.store.remove_link(a, b) else "Il n'y avait pas de lien choisi entre eux."
