"""Applicazione FastAPI: pagine HTML con Bootstrap Italia ed esportazione dei risultati validati."""
import csv
import io
import re
from collections import Counter
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape
from starlette.exceptions import HTTPException as StarletteHTTPException

from ui.config import LOOPBACK
from ui.data import (ACTIONS, CATEGORIES, DEVIATIONS, DRAFT_ACTIONS, DRAFT_EDITABLE, DRAFT_REQUIRED, ENTITY_TYPES,
                     OUTCOMES, REGISTER_COLUMNS, apply_decision, load_drafts, load_predictions, load_register, priority,
                     risk, split_path, when)
from ui.decisions import DecisionLog
from ui.security import HEADERS, LOCAL_USER, ROLES, Csrf, check_basic_auth, load_users

HERE = Path(__file__).parent
BI = "vendor/bootstrap-italia-2.18.3"
PAGE_SIZE = 50
MAX_NOTE = 500
MAX_QUERY = 100
ID_RE = re.compile(r"^[0-9a-f]{16}$")


def _cell(v):
    if isinstance(v, bool):
        v = "SI" if v else "NO"
    v = ", ".join(v) if isinstance(v, list) else ("" if v is None else str(v))
    # niente formule quando il CSV si apre in un foglio di calcolo
    return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") else v


def _csv(header, rows, filename):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(header)
    w.writerows([_cell(v) for v in r] for r in rows)
    return Response("\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


class Store:
    """Predizioni ricaricate quando il file cambia (es. nuova analisi della pipeline)."""

    def __init__(self, settings):
        self.settings, self.mtime, self.docs = settings, None, []
        self.register = load_register(settings.register)
        # shortcut: bozze lette all'avvio; dopo make drafts va riavviata la UI, ricaricarle come le predizioni se serve
        self.drafts = load_drafts(settings.drafts)
        self.refresh()

    def refresh(self):
        mtime = self.settings.predictions.stat().st_mtime
        if mtime != self.mtime:
            self.docs, self.mtime = load_predictions(self.settings.predictions), mtime
        return self.docs


def create_app(settings):
    users = load_users(settings.users_file) if settings.users_file else None
    if users is None and settings.host not in LOOPBACK:
        raise ValueError("senza file degli utenti (UI_UTENTI) la UI ascolta solo su 127.0.0.1")
    store = Store(settings)
    log = DecisionLog(settings.db)
    csrf = Csrf(settings.secret)
    templates = Jinja2Templates(directory=HERE / "templates")  # autoescape attivo sui .html
    templates.env.globals.update(ente=settings.ente, bi=f"/static/{BI}", outcomes=OUTCOMES, deviations=DEVIATIONS,
                                 entity_types=ENTITY_TYPES, categories=CATEGORIES, roles=ROLES, actions=ACTIONS,
                                 local_mode=users is None, schede=store.register, priority=priority)
    def breakable(text):
        # a capo dopo _ - / . invece che a metà parola (prima si fa l'escape, poi si aggiunge <wbr>)
        return Markup(re.sub(r"([_\-/.])", r"\1<wbr>", str(escape(text))))
    templates.env.filters.update(cartella=lambda p: split_path(p)[0], nome_file=lambda p: split_path(p)[1], quando=when,
                                 spezza=breakable)

    app = FastAPI(title="Classificatore del patrimonio informativo", docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")

    @app.middleware("http")
    async def security(request, call_next):
        if not request.url.path.startswith("/static/"):
            if users is None:
                request.state.user = LOCAL_USER
            else:
                user = check_basic_auth(request.headers.get("authorization"), users)
                if user is None:
                    return Response("Accesso richiesto", status_code=401, headers={
                        "WWW-Authenticate": 'Basic realm="Patrimonio informativo", charset="UTF-8"', **HEADERS})
                request.state.user = user
        response = await call_next(request)
        response.headers.update(HEADERS)
        return response

    def page(request, name, status=200, **ctx):
        user = request.state.user
        return templates.TemplateResponse(request, name, {"user": user, "csrf": csrf.token(user), **ctx},
                                          status_code=status)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        if not hasattr(request.state, "user"):
            return Response(str(exc.detail), status_code=exc.status_code)
        titles = {400: "Richiesta non valida", 403: "Operazione non consentita", 404: "Pagina non trovata"}
        return page(request, "errore.html", status=exc.status_code, title=titles.get(exc.status_code, "Errore"),
                    message=exc.detail)

    def guard(request, token, action):
        """Controlli comuni ai moduli: stessa origine, ruolo RPD, token anti-CSRF."""
        user = request.state.user
        origin = request.headers.get("origin")
        if origin and origin.split("://", 1)[-1] != request.headers.get("host"):
            raise HTTPException(403, "Richiesta da un'altra origine.")
        if user["ruolo"] != "rpd":
            raise HTTPException(403, f"Solo l'RPD può {action}.")
        if not csrf.valid(user, token):
            raise HTTPException(403, "Modulo scaduto o non valido: ricarica la pagina e riprova.")
        return user

    def documents():
        latest = log.latest()
        return [apply_decision(d, latest.get((d["file"], d["sha256"]))) for d in store.refresh()]

    def queue_of(docs):
        """Documenti da validare, dal più rischioso."""
        return sorted((d for d in docs if d["dati_personali"] and not d["validato"]
                       and d["esito"] != "NESSUN_DATO_PERSONALE"), key=lambda d: (-risk(d), d["file"]))

    def find(doc_id):
        if not ID_RE.match(doc_id):
            raise HTTPException(404, "Documento non trovato.")
        doc = next((d for d in documents() if d["id"] == doc_id), None)
        if doc is None:
            raise HTTPException(404, "Documento non trovato.")
        return doc

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request):
        docs = documents()
        by_outcome = Counter(d["esito"] for d in docs)
        by_deviation = Counter(s for d in docs for s in d["scostamenti"])
        by_record = Counter(d["scheda"] for d in docs if d["scheda"])
        missing = [d for d in docs if d["esito"] == "SCHEDA_MANCANTE"]
        return page(request, "cruscotto.html", nav="cruscotto", docs=docs, by_outcome=by_outcome,
                    by_deviation=by_deviation, by_record=by_record.most_common(), missing=missing,
                    validated=sum(d["validato"] for d in docs), register=store.register,
                    personal=sum(d["dati_personali"] for d in docs), urgent=queue_of(docs)[:5],
                    sensitive=sum(bool(d["categorie_particolari"]) for d in docs))

    @app.get("/documenti", response_class=HTMLResponse)
    def inventory(request: Request, esito: str = "", scheda: str = "", scostamento: str = "", pagina: int = 1):
        if (esito and esito not in OUTCOMES) or (scostamento and scostamento not in DEVIATIONS) \
                or (scheda and scheda not in store.register) or not 1 <= pagina <= 10_000:
            raise HTTPException(400, "Filtro non valido.")
        docs = [d for d in documents() if (not esito or d["esito"] == esito)
                and (not scheda or d["scheda"] == scheda) and (not scostamento or scostamento in d["scostamenti"])]
        pages = max(1, -(-len(docs) // PAGE_SIZE))
        return page(request, "inventario.html", nav="documenti", docs=docs[(pagina - 1) * PAGE_SIZE:pagina * PAGE_SIZE],
                    total=len(docs), pagina=min(pagina, pages), pages=pages, register=store.register,
                    filters={"esito": esito, "scheda": scheda, "scostamento": scostamento})

    @app.get("/documenti/{doc_id}", response_class=HTMLResponse)
    def detail(request: Request, doc_id: str):
        doc = find(doc_id)
        history = [d for d in log.all() if d["documento"] == doc["file"]]
        queue = queue_of(documents())
        ids = [d["id"] for d in queue]
        position = ids.index(doc_id) + 1 if doc_id in ids else None
        # il prossimo dopo questo nella coda; per un documento già validato, il primo della coda
        following = ids[position:] if position else ids
        return page(request, "documento.html", nav="coda" if position else "documenti", doc=doc, history=history,
                    record=store.register.get(doc["scheda"] or ""), register=store.register,
                    can_decide=request.state.user["ruolo"] == "rpd", position=position, queue_size=len(ids),
                    next_id=following[0] if following else None)

    @app.post("/documenti/{doc_id}/decisione")
    def decide(request: Request, doc_id: str, csrf_token: str = Form("", alias="csrf"), azione: str = Form(""),
               esito: str = Form(""), scheda: str = Form(""), nota: str = Form(""), poi: str = Form("")):
        user = guard(request, csrf_token, "registrare decisioni")
        doc = find(doc_id)
        nota = re.sub(r"[\x00-\x1f\x7f]", " ", nota).strip()[:MAX_NOTE]
        if azione == "CONFERMA":
            esito, scheda = doc["esito"], doc["scheda"] or ""
        elif azione == "CORREZIONE":
            if esito not in OUTCOMES:
                raise HTTPException(400, "Esito non valido.")
            if scheda and scheda not in store.register:
                raise HTTPException(400, "Scheda non presente nel registro.")
            if esito in ("CONFORME", "NON_CONFORME") and not scheda:
                raise HTTPException(400, "Per un documento conforme o non conforme indica la scheda.")
            if esito in ("SCHEDA_MANCANTE", "NESSUN_DATO_PERSONALE"):
                scheda = ""
        else:
            raise HTTPException(400, "Azione non valida.")
        before = [d["id"] for d in queue_of(documents())]
        log.add(user["nome"], doc, azione, esito, scheda, nota)
        if poi == "prossimo":
            # il documento che veniva dopo questo nella coda, ripartendo dall'inizio dopo l'ultimo
            k = before.index(doc_id) if doc_id in before else -1
            remaining = {d["id"] for d in queue_of(documents())}
            nxt = next((i for i in before[k + 1:] + before[:max(k, 0)] if i in remaining), None)
            if nxt is None:
                return RedirectResponse("/coda?finita=1", status_code=303)
            return RedirectResponse(f"/documenti/{nxt}?registrata=1", status_code=303)
        return RedirectResponse(f"/documenti/{doc_id}?registrata=1", status_code=303)

    @app.get("/coda", response_class=HTMLResponse)
    def queue(request: Request, pagina: int = 1):
        docs = queue_of(documents())
        pages = max(1, -(-len(docs) // PAGE_SIZE))
        if not 1 <= pagina <= pages:
            raise HTTPException(400, "Pagina non valida.")
        return page(request, "coda.html", nav="coda", docs=docs[(pagina - 1) * PAGE_SIZE:pagina * PAGE_SIZE],
                    total=len(docs), by_outcome=Counter(d["esito"] for d in docs), pagina=pagina, pages=pages,
                    start=(pagina - 1) * PAGE_SIZE, first=docs[0] if docs else None)

    @app.get("/ricerca", response_class=HTMLResponse)
    def search(request: Request, q: str = ""):
        q = q.strip()[:MAX_QUERY]
        results = []
        if q:
            terms = q.lower().split()

            def haystack(d):
                return " ".join([d["file"], d["esito"], OUTCOMES[d["esito"]][0], d["scheda"] or "",
                                 *d["scostamenti"], *(DEVIATIONS[s][0] for s in d["scostamenti"]),
                                 *d["categorie_particolari"], *(e["tipo"] for e in d["entita"]),
                                 *(ENTITY_TYPES.get(e["tipo"], "") for e in d["entita"]),
                                 *(p["motivazione"] for p in d["proposte"])]).lower()
            results = [d for d in documents() if all(t in haystack(d) for t in terms)]
        return page(request, "ricerca.html", nav="ricerca", q=q, results=results)

    @app.get("/decisioni", response_class=HTMLResponse)
    def decisions(request: Request):
        ids = {d["file"]: d["id"] for d in store.refresh()}
        return page(request, "decisioni.html", nav="decisioni", rows=log.all(), ids=ids)

    def export_rows():
        keys = ("file", "sha256", "dati_personali", "categorie_particolari", "livello", "scheda", "esito",
                "scostamenti", "validato")
        return [{k: d[k] for k in keys} | {"entita": [{k: e[k] for k in ("tipo", "valore_mascherato", "inizio",
                                                                         "confidenza")} for e in d["entita"]],
                                           "proposte": d["proposte"]} for d in documents()]

    @app.get("/esporta.json")
    def export_json():
        return JSONResponse(export_rows(), headers={"Content-Disposition": 'attachment; filename="risultati.json"'})

    @app.get("/esporta.csv")
    def export_csv():
        cols = ["file", "sha256", "esito", "scheda", "scostamenti", "categorie_particolari", "dati_personali",
                "validato", "nota_rpd"]
        latest = log.latest()
        rows = []
        for d in documents():
            dec = latest.get((d["file"], d["sha256"]))
            rows.append([d[c] for c in cols[:-1]] + [dec["nota"] if dec else ""])
        return _csv(cols, rows, "risultati.csv")

    @app.get("/bozze", response_class=HTMLResponse)
    def drafts(request: Request):
        ids = {d["file"]: d["id"] for d in store.refresh()}
        return page(request, "bozze.html", nav="bozze", drafts=store.drafts, decided=log.drafts(), ids=ids,
                    editable=DRAFT_EDITABLE, required=DRAFT_REQUIRED, draft_actions=DRAFT_ACTIONS,
                    can_decide=request.state.user["ruolo"] == "rpd", drafts_file=settings.drafts.exists())

    @app.get("/bozze/approvate.csv")
    def approved_drafts():
        """Righe nel formato del registro, da incollare nel registro dei trattamenti dopo la revisione."""
        decided = log.drafts()
        rows = [[decided[d["id"]]["campi"].get(c, "") for c in REGISTER_COLUMNS] for d in store.drafts
                if decided.get(d["id"], {}).get("azione") == "APPROVA"]
        return _csv(REGISTER_COLUMNS, rows, "nuove_schede.csv")

    @app.post("/bozze/{draft_id}")
    async def decide_draft(request: Request, draft_id: str):
        form = await request.form()
        user = guard(request, form.get("csrf", ""), "decidere sulle bozze")
        draft = next((d for d in store.drafts if d["id"] == draft_id), None) if ID_RE.match(draft_id) else None
        if draft is None:
            raise HTTPException(404, "Bozza non trovata.")
        action = form.get("azione")
        if action not in DRAFT_ACTIONS:
            raise HTTPException(400, "Azione non valida.")
        fields = dict(draft["campi"])
        for name, col in DRAFT_EDITABLE.items():
            value = form.get(name, "")
            if not isinstance(value, str):
                raise HTTPException(400, "Campo non valido.")
            fields[col] = re.sub(r"[\x00-\x1f\x7f]", " ", value).strip()[:MAX_NOTE]
        if action == "APPROVA":
            if not all(fields[c] for c in DRAFT_REQUIRED):
                raise HTTPException(400, f"Per approvare servono: {', '.join(DRAFT_REQUIRED).lower()}.")
            if fields["Conservazione in anni"] and not re.fullmatch(r"\d{1,3}", fields["Conservazione in anni"]):
                raise HTTPException(400, "Conservazione in anni: scrivi un numero intero.")
        log.add_draft(user["nome"], draft_id, action, fields if action == "APPROVA" else {})
        return RedirectResponse(f"/bozze?registrata={draft_id}#bozza-{draft_id}", status_code=303)

    return app
