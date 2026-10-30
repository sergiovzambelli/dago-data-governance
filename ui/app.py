"""Applicazione FastAPI: pagine HTML con Bootstrap Italia ed esportazione dei risultati validati."""
import csv
import hashlib
import io
import re
import secrets
import tempfile
import threading
import time
from collections import Counter
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException as StarletteHTTPException

from ui.config import LOOPBACK
from ui.data import (ACTIONS, CATEGORIES, DEVIATIONS, DRAFT_ACTIONS, DRAFT_EDITABLE, DRAFT_REQUIRED, ENTITY_TYPES,
                     NO_LIMIT, OUTCOMES, RECORD_ACTIONS, RECORD_CODE, RECORD_HINTS, RECORD_LONG, RECORD_REQUIRED,
                     RECORD_SECTIONS, REGISTER_COLUMNS, apply_decision, apply_records, clean_record, highlight,
                     load_drafts, load_predictions, load_register, parse_predictions, priority, record_view, risk,
                     sector, split_path, when)
from ui.decisions import DecisionLog
from ui.gauge import average, compliance_score, gauge_svg, level
from ui.security import HEADERS, LOCAL_USER, ROLES, Csrf, check_basic_auth, load_users

HERE = Path(__file__).parent
BI = "vendor/bootstrap-italia-2.18.3"
PAGE_SIZE = 50
MAX_NOTE = 500
MAX_QUERY = 100
ID_RE = re.compile(r"^[0-9a-f]{16}$")
MAX_UPLOAD = 20 * 1024 * 1024
MAX_TEXT_SHOWN = 5000
FOLDER_RE = re.compile(r"^[\w .()-]+(/[\w .()-]+)*$")
# fasi reali dell'analisi di Prova un file, nell'ordine in cui avvengono (barra di avanzamento)
TRY_PHASES = ["Lettura del file", "Estrazione del testo", "Dati personali, categorie, scheda e controlli",
              "Evidenziazione nel testo", "Risultato"]
JOB_TTL = 15 * 60          # secondi: un risultato mai aperto viene buttato
MAX_JOBS_PER_USER = 2      # analisi contemporanee per utente


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
        self.base = load_register(settings.register)  # CSV del registro: la UI non lo scrive mai
        self.records, self.register = {}, {}
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
                                 local_mode=users is None, priority=priority, gauge=gauge_svg, score=compliance_score)

    def sync_register():
        """Schede in uso = CSV + versioni salvate. Si riassegna il dizionario intero: nessuna richiesta lo vede a metà."""
        store.records = apply_records(store.base, log.records())
        store.register = {c: record_view(r["campi"]) for c, r in store.records.items() if not r["archiviata"]}
        templates.env.globals["schede"] = store.register
    sync_register()
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
            sync_register()  # vale anche con più processi che scrivono nello stesso database
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
        uploaded = parse_predictions(log.uploads())
        # un file caricato con lo stesso percorso di uno analizzato dalla pipeline lo sostituisce
        paths = {d["file"] for d in uploaded}
        docs = [d for d in store.refresh() if d["file"] not in paths] + uploaded
        return [apply_decision(d, latest.get((d["file"], d["sha256"]))) for d in docs]

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
        by_sector, sector_docs = {}, {}
        for d in docs:
            by_sector.setdefault(sector(d["file"]), Counter())[d["esito"]] += 1
            sector_docs.setdefault(sector(d["file"]), []).append(d)
        return page(request, "cruscotto.html", nav="cruscotto", docs=docs, by_outcome=by_outcome,
                    by_sector=sorted(by_sector.items(), key=lambda s: (not s[0], s[0].lower())),
                    by_deviation=by_deviation, by_record=by_record.most_common(), missing=missing,
                    validated=sum(d["validato"] for d in docs), register=store.register,
                    personal=sum(d["dati_personali"] for d in docs), urgent=queue_of(docs)[:5],
                    sensitive=sum(bool(d["categorie_particolari"]) for d in docs),
                    # grado di conformità: media dei documenti con dati personali, con le decisioni dell'RPD
                    archive_score=average(docs), sector_score={k: average(v) for k, v in sector_docs.items()})

    @app.get("/documenti", response_class=HTMLResponse)
    def inventory(request: Request, esito: str = "", scheda: str = "", scostamento: str = "", settore: str = "",
                  pagina: int = 1):
        all_docs = documents()
        sectors = sorted({sector(d["file"]) for d in all_docs} - {""}, key=str.lower)
        if (esito and esito not in OUTCOMES) or (scostamento and scostamento not in DEVIATIONS) \
                or (scheda and scheda not in store.register) or (settore and settore not in sectors) \
                or not 1 <= pagina <= 10_000:
            raise HTTPException(400, "Filtro non valido.")
        docs = [d for d in all_docs if (not esito or d["esito"] == esito)
                and (not scheda or d["scheda"] == scheda) and (not scostamento or scostamento in d["scostamenti"])
                and (not settore or sector(d["file"]) == settore)]
        pages = max(1, -(-len(docs) // PAGE_SIZE))
        return page(request, "inventario.html", nav="documenti", docs=docs[(pagina - 1) * PAGE_SIZE:pagina * PAGE_SIZE],
                    total=len(docs), pagina=min(pagina, pages), pages=pages, register=store.register, sectors=sectors,
                    filters={"esito": esito, "scheda": scheda, "scostamento": scostamento, "settore": settore})

    @app.get("/documenti/{doc_id}", response_class=HTMLResponse)
    async def detail(request: Request, doc_id: str):
        doc = find(doc_id)
        user = request.state.user
        # testo integrale solo all'RPD (eccezione a T-031, come Prova un file)
        # shortcut: estrazione (e OCR delle scansioni) a ogni apertura, nessuna cache per non conservare il testo;
        # se le scansioni rendono la pagina lenta, caricare il testo a richiesta
        view = await run_in_threadpool(file_view, doc, user) if user["ruolo"] == "rpd" and settings.documents else {}
        history = [d for d in log.all() if d["documento"] == doc["file"]]
        queue = queue_of(documents())
        ids = [d["id"] for d in queue]
        position = ids.index(doc_id) + 1 if doc_id in ids else None
        # il prossimo dopo questo nella coda; per un documento già validato, il primo della coda
        following = ids[position:] if position else ids
        response = page(request, "documento.html", nav="coda" if position else "documenti", doc=doc, history=history,
                        record=store.register.get(doc["scheda"] or ""), register=store.register,
                        can_decide=user["ruolo"] == "rpd", position=position, queue_size=len(ids),
                        next_id=following[0] if following else None,
                        prev_id=ids[position - 2] if position and position > 1 else None,
                        # coda accanto al documento: solo se il documento è da validare
                        queue_docs=queue if position else [], **view)
        if "segments" in view:
            response.headers["Cache-Control"] = "no-store"  # la pagina contiene il testo del documento
        return response

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

    def analysis(rel, text, sha, origin, progress=lambda phase: None):
        """Analisi del testo come nella pipeline: (esito, testo evidenziato, scelta della scheda se manca)."""
        from classifier.categories import find_categories
        from classifier.compliance import check, load_permissions
        from classifier.dates import document_date
        from classifier.drafts import build_drafts
        from classifier.matching import load_register as load_rules
        from classifier.pipeline import analyze

        def outcome(record, categories):
            deviations = check(record, rel, categories, perms, document_date(rel, text))
            return {"esito": "NON_CONFORME" if deviations else "CONFORME", "scostamenti": deviations}

        with tempfile.TemporaryDirectory() as tmp:
            reg = Path(tmp) / "registro.csv"
            reg.write_bytes(export_register().body)  # registro in uso, con le modifiche fatte nella UI
            perms = load_permissions(settings.permissions) if settings.permissions and \
                settings.permissions.exists() else ()
            rules = {r["codice"]: r for r in load_rules(reg)}
            result = analyze(rel, text, list(rules.values()), perms)
            progress(4)  # evidenziazione nel testo e, se manca la scheda, proposte e bozza
            shown = text[:MAX_TEXT_SHOWN]
            spans = [(e["inizio"], e["fine"], "entita", ENTITY_TYPES.get(e["tipo"], e["tipo"]))
                     for e in result["entita"]]
            spans += [(m.start(), m.end(), "chiave", f"parola chiave di {p['scheda']}")
                      for p in result["proposte"] for _, regex, _ in rules[p["scheda"]]["termini"]
                      for m in regex.finditer(shown)]
            spans += [(c["inizio"], c["fine"], "categoria", CATEGORIES.get(c["categoria"], c["categoria"]))
                      for c in find_categories(text)]
            choice = None
            if result["esito"] == "SCHEDA_MANCANTE":
                # esito con ciascuna scheda proposta e con una scheda nuova: firmati, tornano con la scelta
                options = {p["scheda"]: outcome(rules[p["scheda"]], result["categorie_particolari"])
                           for p in result["proposte"]}
                draft = build_drafts([{**result, "file": rel}], {rel: text}, perms)[0]["campi"]
                key = re.findall(r"[A-Z0-9]+", draft["Tipologie documentali tipiche"].upper())
                draft["Codice"] = "NUOVA-" + ("-".join(k[:6] for k in key[:2]) or "DOC")
                draft["Denominazione"] = draft["Denominazione"] or draft["Tipologie documentali tipiche"].capitalize()
                (Path(tmp) / "nuova.csv").write_bytes(_csv(REGISTER_COLUMNS, [[draft[c] for c in REGISTER_COLUMNS]],
                                                           "nuova.csv").body)
                options["NUOVA"] = outcome(load_rules(Path(tmp) / "nuova.csv")[0], result["categorie_particolari"])
                choice = {"predizione": {"file": rel, "sha256": sha, **result}, "opzioni": options, "nuova": draft,
                          "origine": origin}
        return result, highlight(shown, spans), choice

    def file_view(doc, user):
        """Il file del documento riletto dalla cartella analizzata, evidenziato come in Prova un file. Mai salvato."""
        root = settings.documents.resolve()
        path = (root / doc["file"]).resolve()
        # resolve segue anche i link: fuori dalla cartella analizzata non si legge nulla
        if not path.is_relative_to(root) or not path.is_file():
            return {"file_error": "File non disponibile nella cartella analizzata."}
        if path.stat().st_size > MAX_UPLOAD:
            return {"file_error": f"File oltre {MAX_UPLOAD // (1024 * 1024)} MB: non viene mostrato."}
        try:
            from classifier.extract import extract_text
        except ImportError:
            return {"file_error": "Analisi non disponibile: installa le dipendenze del classificatore."}
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        text = extract_text(path)
        result, segments, choice = analysis(doc["file"], text, sha, "dettaglio documento")
        changed = sha != doc["sha256"]
        # la scelta vale per il file analizzato: se è cambiato, o la scheda c'è già, niente card
        if changed or doc["esito"] != "SCHEDA_MANCANTE":
            choice = None
        return {"chars": len(text), "segments": segments, "choice": choice, "file_changed": changed,
                "result": result, "analisi": csrf.sign(user, choice) if choice else ""}

    @app.get("/prova", response_class=HTMLResponse)
    def try_form(request: Request):
        return page(request, "prova.html", nav="prova", result=None, try_phases=TRY_PHASES)

    async def read_upload(request):
        """Controlli del modulo di Prova un file: (nome, percorso relativo, contenuto)."""
        form = await request.form()
        guard(request, form.get("csrf", ""), "analizzare un file")
        file, cartella = form.get("file"), form.get("cartella", "")
        # import qui: il resto della UI funziona anche senza le dipendenze del classificatore (requirements.txt)
        try:
            from classifier.extract import extract_text  # noqa: F401  (lo usa run_analysis)
            from classifier.pipeline import analyze  # noqa: F401  (lo usa analysis(): qui si verifica che ci sia)
        except ImportError:
            raise HTTPException(503, "Analisi non disponibile: installa le dipendenze del classificatore "
                                     "(requirements.txt).")
        name = Path(file.filename or "").name.strip()[:200] if isinstance(file, UploadFile) else ""
        if not name or not isinstance(cartella, str):
            raise HTTPException(400, "Scegli un file da analizzare.")
        folder = cartella.strip().strip("/")[:300]
        if folder and (not FOLDER_RE.match(folder) or ".." in folder.split("/")):
            raise HTTPException(400, "Cartella non valida: usa un percorso come fileserver/Personale/Permessi.")
        data = await file.read(MAX_UPLOAD + 1)
        if len(data) > MAX_UPLOAD:
            raise HTTPException(400, f"File troppo grande: massimo {MAX_UPLOAD // (1024 * 1024)} MB.")
        return name, (f"{folder}/{name}" if folder else name), data

    def run_analysis(name, rel, data, progress=lambda phase: None):
        """Estrazione e analisi, con le fasi di TRY_PHASES. Estrazione e OCR possono durare minuti."""
        from classifier.extract import extract_text
        progress(1)
        with tempfile.TemporaryDirectory() as tmp:
            # il nome sul disco è fisso: dall'utente si prende solo l'estensione, che sceglie l'estrattore
            path = Path(tmp) / ("file" + "".join(c for c in Path(name).suffix if c.isalnum() or c == ".")[:10])
            path.write_bytes(data)
            progress(2)
            text = extract_text(path)
        progress(3)
        return (text, *analysis(rel, text, hashlib.sha256(data).hexdigest(), "Prova un file", progress))

    def try_result(request, rel, text, result, segments, choice):
        user = request.state.user
        response = page(request, "prova.html", nav="prova", result=result, rel=rel, chars=len(text),
                        segments=segments, choice=choice, analisi=csrf.sign(user, choice) if choice else "",
                        try_phases=TRY_PHASES)
        response.headers["Cache-Control"] = "no-store"  # la pagina contiene il testo del documento
        return response

    @app.post("/prova", response_class=HTMLResponse)
    async def try_file(request: Request):
        """Analizza un file caricato e mostra ogni passo (senza JavaScript). Il file resta solo in una cartella temporanea."""
        name, rel, data = await read_upload(request)
        text, result, segments, choice = await run_in_threadpool(run_analysis, name, rel, data)
        return try_result(request, rel, text, result, segments, choice)

    # analisi in background, per la barra di avanzamento: lo stato non contiene il testo; il risultato si legge una volta
    jobs, jobs_lock = {}, threading.Lock()

    def job_of(request, job_id):
        with jobs_lock:
            job = jobs.get(job_id)
        if job is None or job["utente"] != request.state.user["nome"]:
            raise HTTPException(404, "Analisi non trovata o già mostrata.")
        return job

    @app.post("/prova/avvia")
    async def try_start(request: Request):
        name, rel, data = await read_upload(request)
        user = request.state.user["nome"]
        with jobs_lock:
            now = time.monotonic()
            for k in [k for k, j in jobs.items() if now - j["creato"] > JOB_TTL]:
                del jobs[k]  # risultati mai aperti: il testo non resta in memoria
            if sum(j["utente"] == user and not j["fatto"] for j in jobs.values()) >= MAX_JOBS_PER_USER:
                raise HTTPException(429, "Hai già analisi in corso: aspetta che finiscano.")
            job_id = secrets.token_urlsafe(16)
            job = jobs[job_id] = {"utente": user, "creato": now, "fase": 0, "fatto": False, "errore": None,
                                  "rel": rel, "risultato": None}

        def work():
            def progress(phase):
                job["fase"] = phase
            try:
                job["risultato"] = run_analysis(name, rel, data, progress)
                job["fase"] = len(TRY_PHASES)
            except Exception:  # noqa: BLE001  (nessun dettaglio all'utente: potrebbe contenere il testo)
                job["errore"] = "Analisi non riuscita: il file potrebbe essere danneggiato o in un formato non letto."
            job["fatto"] = True

        threading.Thread(target=work, daemon=True).start()
        return JSONResponse({"lavoro": job_id}, headers={"Cache-Control": "no-store"})

    @app.get("/prova/stato/{job_id}")
    def try_status(request: Request, job_id: str):
        job = job_of(request, job_id)
        state = {"fasi": TRY_PHASES, "fase": job["fase"], "fatto": job["fatto"], "errore": job["errore"],
                 "esito": None, "etichetta": None, "grado": None, "livello": None}
        if job["fatto"] and job["risultato"]:
            result = job["risultato"][1]
            grade = compliance_score(result)
            state.update(esito=result["esito"], etichetta=OUTCOMES[result["esito"]][0], grado=grade,
                         livello=level(grade)[0] if grade is not None else None)
        return JSONResponse(state, headers={"Cache-Control": "no-store"})

    @app.get("/prova/risultato/{job_id}", response_class=HTMLResponse)
    def try_job_result(request: Request, job_id: str):
        job = job_of(request, job_id)
        if not job["fatto"]:
            raise HTTPException(400, "Analisi ancora in corso.")
        with jobs_lock:
            jobs.pop(job_id, None)  # una sola lettura: il testo del documento non resta sul server
        if job["errore"]:
            raise HTTPException(400, job["errore"])
        text, result, segments, choice = job["risultato"]
        return try_result(request, job["rel"], text, result, segments, choice)

    @app.post("/prova/salva")
    async def save_try(request: Request):
        """Scheda scelta dall'RPD per un file senza scheda: il documento entra nell'inventario, già validato."""
        form = await request.form()
        user = guard(request, form.get("csrf", ""), "aggiungere documenti all'inventario")
        choice = csrf.unsign(user, form.get("analisi", ""))
        if choice is None:
            raise HTTPException(400, "Analisi non valida o scaduta: carica di nuovo il file.")
        code = form.get("scheda", "")
        if code not in choice["opzioni"] or (code != "NUOVA" and code not in store.register):
            raise HTTPException(400, "Scheda non valida.")
        option = choice["opzioni"][code]
        if code == "NUOVA":
            fields, base = choice["nuova"], choice["nuova"]["Codice"]
            code = next(c for c in [base] + [f"{base}-{i}" for i in range(2, 100)] if c not in store.records)
            log.add_record(user["nome"], code, "CREA", {**fields, "Codice": code})
            sync_register()
        prediction = {**choice["predizione"], "scheda": code, **option}
        log.add_upload(user["nome"], prediction)
        doc = parse_predictions([prediction])[0]
        log.add(user["nome"], doc, "CONFERMA", option["esito"], code,
                f"Scheda scelta da {choice.get('origine', 'Prova un file')} (proposta del sistema: scheda mancante)")
        if form.get("scheda") == "NUOVA":
            return RedirectResponse(f"/schede/{code}?salvata=1", status_code=303)
        return RedirectResponse(f"/documenti/{doc['id']}?registrata=1", status_code=303)

    @app.get("/decisioni", response_class=HTMLResponse)
    def decisions(request: Request):
        ids = {d["file"]: d["id"] for d in documents()}
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
        ids = {d["file"]: d["id"] for d in documents()}
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

    def find_record(code):
        if not RECORD_CODE.fullmatch(code) or code not in store.records:
            raise HTTPException(404, "Scheda non trovata.")
        return store.records[code]

    def record_page(request, code=None, status=200):
        ctx = {"sections": RECORD_SECTIONS, "long": RECORD_LONG, "hints": RECORD_HINTS, "required": RECORD_REQUIRED,
               "columns": REGISTER_COLUMNS, "no_limit": NO_LIMIT, "record_actions": RECORD_ACTIONS,
               "can_decide": request.state.user["ruolo"] == "rpd"}
        if code is None:
            return page(request, "scheda.html", nav="schede", code=None, rec=None,
                        values=dict.fromkeys(REGISTER_COLUMNS, ""), **ctx)
        rec = find_record(code)
        n = sum(d["scheda"] == code for d in documents())
        return page(request, "scheda.html", status=status, nav="schede", code=code, rec=rec, values=rec["campi"],
                    linked=n, **ctx)

    @app.get("/schede", response_class=HTMLResponse)
    def records(request: Request):
        counts = Counter(d["scheda"] for d in documents() if d["scheda"])
        return page(request, "schede.html", nav="schede", records=store.records, counts=counts,
                    can_decide=request.state.user["ruolo"] == "rpd")

    @app.get("/schede/registro.csv")
    def export_register():
        """Registro in uso, con le stesse colonne del CSV del kit: si passa al classificatore."""
        rows = [[r["campi"][c] for c in REGISTER_COLUMNS] for r in store.records.values() if not r["archiviata"]]
        return _csv(REGISTER_COLUMNS, rows, "registro_trattamenti.csv")

    @app.get("/schede/nuova", response_class=HTMLResponse)
    def new_record_form(request: Request):
        return record_page(request)

    @app.post("/schede/nuova")
    async def create_record(request: Request):
        form = await request.form()
        user = guard(request, form.get("csrf", ""), "modificare il registro")
        try:
            fields = clean_record(form)
        except ValueError as e:
            raise HTTPException(400, str(e))
        if fields["Codice"] in store.records:
            raise HTTPException(400, "Esiste già una scheda con questo codice (anche tra le archiviate).")
        log.add_record(user["nome"], fields["Codice"], "CREA", fields)
        sync_register()
        return RedirectResponse(f"/schede/{fields['Codice']}?salvata=1", status_code=303)

    @app.get("/schede/{code}", response_class=HTMLResponse)
    def record_detail(request: Request, code: str):
        return record_page(request, code)

    @app.post("/schede/{code}")
    async def change_record(request: Request, code: str):
        form = await request.form()
        user = guard(request, form.get("csrf", ""), "modificare il registro")
        rec = find_record(code)
        action = form.get("azione")
        if action == "MODIFICA":
            try:
                fields = clean_record({**form, "Codice": code})  # il codice non cambia
            except ValueError as e:
                raise HTTPException(400, str(e))
        elif action == ("RIPRISTINA" if rec["archiviata"] else "ARCHIVIA"):
            fields = rec["campi"]
        else:
            raise HTTPException(400, "Azione non valida.")
        log.add_record(user["nome"], code, action, fields)
        sync_register()
        return RedirectResponse(f"/schede/{code}?salvata=1", status_code=303)

    return app
