from pathlib import Path
import json
import os
import base64
import zlib
import hmac
import hashlib
import secrets

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"


app = FastAPI(title="PRD++ (pre_prod)")

# Serve project-root assets (e.g., global.css) under /assets
app.mount("/assets", StaticFiles(directory=str(BASE_DIR)), name="assets")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    default_packs = {"pack_core": "on", "pack_opinionated": None, "pack_strict": None}
    default_result = compute_continuity(
        SCRIPT_DEFAULT,
        RULES_DEFAULT,
        SCENES_DEFAULT,
        SHOTS_DEFAULT,
        default_packs,
    )
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "page_title": "SpecStudio",
            "tab": "script",
            "script_text": SCRIPT_DEFAULT,
            "rules_text": RULES_DEFAULT,
            "scenes_json": json.dumps(SCENES_DEFAULT),
            "shots_json": json.dumps(SHOTS_DEFAULT),
            "packs": default_packs,
            "result": default_result,
        },
    )


# Defaults for editor content
SCRIPT_DEFAULT = (
    "## Product Overview\n"
    "One-liner: Ship a task manager MVP fast with FastAPI + HTMX + SQLite.\n"
    "Audience: Indie hackers who want working CRUD + auth quickly.\n"
    "KPIs: TTFA <= 5 min; p95 /export < 200ms; coverage >= 70%.\n\n"
    "## Purpose\n"
    "Solve context-switch + boilerplate fatigue. Provide a minimal, shippable core.\n\n"
    "## Target Audience\n"
    "Solo builders, very small teams; non-enterprise constraints.\n\n"
    "## Expected Outcomes\n"
    "- Generate four artifacts for Cursor: PRD.md, rules, epics.json, tickets.json.\n"
    "- Clear AC drives codegen; zero SPA overhead; simple deploy.\n\n"
    "## Design Details\n"
    "### Architectural Overview\n"
    "FastAPI + server-rendered HTMX; SQLite; DaisyUI.\n\n"
    "### Data Structures & Algorithms\n"
    "Scene: {id,title,goal,risk} ; Shot: {id,epic_id,title,status,priority}.\n\n"
    "### System Interfaces\n"
    "GET /, POST /panel, POST /export.\n\n"
    "### User Interfaces\n"
    "Tabs: Script, Rules, Scenes, Shots. Export button.\n\n"
    "## Testing Plan\n"
    "- pytest; golden tests for artifacts; basic route tests.\n\n"
    "## Constraints\n"
    "- Stack: FastAPI + HTMX + SQLite. No paid services. Single VPS deploy.\n\n"
    "## Acceptance Criteria\n"
    "- CRUD endpoints return correct status; validations enforced.\n"
    "- Auth (later): signup/login/logout; reset via token (15 min).\n"
    "- /export returns artifacts; performance meets KPI.\n"
)

RULES_DEFAULT = (
    "# Cursor Rules\n"
    "- Use Python 3.12, FastAPI, HTMX, SQLite.\n"
    "- Prefer server-side HTML over heavy SPA JS.\n"
    "- Follow PEP8; type hints required.\n"
    "- Use `sqlite3.Row` row_factory.\n"
    "- Write tests with pytest + httpx TestClient.\n"
    "- Never commit secrets; use .env.example.\n"
)

SCENES_DEFAULT = [
    {"id": "E1", "title": "Core CRUD", "goal": "Ship item CRUD end-to-end", "risk": "data loss"},
]

SHOTS_DEFAULT = [
    {
        "id": "T1",
        "epic_id": "E1",
        "title": "Build items table",
        "status": "todo",  # todo | doing | done
        "priority": "P1",  # P1 | P2 | P3
        "description": "Design schema and create initial migrations.",
        "checklist": [
            {"text": "Create table with constraints", "tag": "positive"},
            {"text": "Handle NULL edge cases", "tag": "negative"},
            {"text": "Detect unique constraint errors", "tag": "error"},
        ],
    },
    {
        "id": "T2",
        "epic_id": "E1",
        "title": "CRUD handlers",
        "status": "doing",
        "priority": "P1",
        "description": "Implement FastAPI handlers for CRUD.",
        "checklist": [
            {"text": "Create endpoints", "tag": "positive"},
            {"text": "Validate bad inputs", "tag": "negative"},
            {"text": "Return 4xx/5xx properly", "tag": "error"},
        ],
    },
]


@app.post("/panel", response_class=HTMLResponse)
async def panel(request: Request) -> HTMLResponse:
    query_tab = request.query_params.get("tab", "script")
    form = await request.form()
    script_text = form.get("script_text", SCRIPT_DEFAULT)
    rules_text = form.get("rules_text", RULES_DEFAULT)
    scenes_json = form.get("scenes_json", json.dumps(SCENES_DEFAULT))
    shots_json = form.get("shots_json", json.dumps(SHOTS_DEFAULT))
    try:
        scenes_data = json.loads(scenes_json) if scenes_json else []
    except json.JSONDecodeError:
        scenes_data = list(SCENES_DEFAULT)
        scenes_json = json.dumps(scenes_data)
    try:
        shots_data = json.loads(shots_json) if shots_json else []
    except json.JSONDecodeError:
        shots_data = list(SHOTS_DEFAULT)
        shots_json = json.dumps(shots_data)

    # Handle scenes operations
    if query_tab == "scenes":
        op = request.query_params.get("op")
        editing_scene = None
        if op == "add":
            next_index = 1
            if scenes_data:
                try:
                    next_index = max(int(s["id"].lstrip("E")) for s in scenes_data) + 1
                except Exception:
                    next_index = len(scenes_data) + 1
            new_scene = {
                "id": f"E{next_index}",
                "title": "New Scene",
                "goal": "Describe the goal",
                "risk": "tbd",
            }
            scenes_data.append(new_scene)
            editing_scene = new_scene
        elif op == "edit":
            scene_id = request.query_params.get("id")
            editing_scene = next((s for s in scenes_data if s.get("id") == scene_id), None)
        elif op == "save":
            original_id = form.get("original_id") or form.get("edit_id")
            scene_id = form.get("edit_id")
            title = form.get("edit_title") or "Untitled"
            goal = form.get("edit_goal") or ""
            updated = False
            for s in scenes_data:
                if s.get("id") == original_id:
                    s["id"] = scene_id
                    s["title"] = title
                    s["goal"] = goal
                    updated = True
                    break
            if not updated:
                scenes_data.append({"id": scene_id, "title": title, "goal": goal})
        elif op == "delete":
            scene_id = request.query_params.get("id")
            scenes_data = [s for s in scenes_data if s.get("id") != scene_id]
        scenes_json = json.dumps(scenes_data)
    else:
        editing_scene = None

    # Handle shots operations
    editing_shot = None
    if query_tab == "shots":
        op = request.query_params.get("op")
        if op == "add":
            next_index = 1
            if shots_data:
                try:
                    next_index = max(int(s["id"].lstrip("T")) for s in shots_data) + 1
                except Exception:
                    next_index = len(shots_data) + 1
            new_shot = {
                "id": f"T{next_index}",
                "epic_id": "E1",
                "title": "New Shot",
                "status": "todo",
                "priority": "P2",
                "description": "",
                "checklist": [],
            }
            shots_data.append(new_shot)
            editing_shot = new_shot
        elif op == "edit":
            shot_id = request.query_params.get("id")
            editing_shot = next((s for s in shots_data if s.get("id") == shot_id), None)
        elif op == "add_check":
            # Build an editing_shot from current form values and append an empty checklist row
            target_id = request.query_params.get("id")
            # pull current values (not yet saved) from the form
            base = {
                "id": form.get("shot_id") or target_id or "",
                "epic_id": form.get("shot_epic_id") or "E1",
                "title": form.get("shot_title") or "Untitled",
                "status": form.get("shot_status") or "todo",
                "priority": form.get("shot_priority") or "P2",
                "description": form.get("shot_description") or "",
            }
            texts = form.getlist("shot_check_text") if hasattr(form, "getlist") else []
            tags = form.getlist("shot_check_tag") if hasattr(form, "getlist") else []
            checklist = []
            for i in range(max(len(texts), len(tags))):
                text = texts[i] if i < len(texts) else ""
                tag = tags[i] if i < len(tags) else "positive"
                checklist.append({"text": text, "tag": tag})
            checklist.append({"text": "", "tag": "positive"})
            base["checklist"] = checklist
            editing_shot = base
        elif op == "remove_check":
            target_id = request.query_params.get("id")
            idx_str = request.query_params.get("idx")
            try:
                idx = int(idx_str)
            except Exception:
                idx = -1
            base = {
                "id": form.get("shot_id") or target_id or "",
                "epic_id": form.get("shot_epic_id") or "E1",
                "title": form.get("shot_title") or "Untitled",
                "status": form.get("shot_status") or "todo",
                "priority": form.get("shot_priority") or "P2",
                "description": form.get("shot_description") or "",
            }
            texts = form.getlist("shot_check_text") if hasattr(form, "getlist") else []
            tags = form.getlist("shot_check_tag") if hasattr(form, "getlist") else []
            checklist = []
            for i in range(max(len(texts), len(tags))):
                if i == idx:
                    continue
                text = texts[i] if i < len(texts) else ""
                tag = tags[i] if i < len(tags) else "positive"
                checklist.append({"text": text, "tag": tag})
            base["checklist"] = checklist
            editing_shot = base
        elif op == "save":
            original_id = form.get("shot_original_id") or form.get("shot_id")
            shot_id = form.get("shot_id")
            epic_id = form.get("shot_epic_id") or "E1"
            title = form.get("shot_title") or "Untitled"
            status = (form.get("shot_status") or "todo").lower()
            if status not in {"todo", "doing", "done"}:
                status = "todo"
            priority = form.get("shot_priority") or "P2"
            if priority not in {"P1", "P2", "P3"}:
                priority = "P2"
            description = form.get("shot_description") or ""
            texts = form.getlist("shot_check_text") if hasattr(form, "getlist") else []
            tags = form.getlist("shot_check_tag") if hasattr(form, "getlist") else []
            checklist = []
            for i in range(max(len(texts), len(tags))):
                text = texts[i] if i < len(texts) else ""
                tag = tags[i] if i < len(tags) else "positive"
                if not text and not tag:
                    continue
                if tag not in {"positive", "negative", "error"}:
                    tag = "positive"
                checklist.append({"text": text, "tag": tag})
            updated = False
            for s in shots_data:
                if s.get("id") == original_id:
                    s.update({
                        "id": shot_id,
                        "epic_id": epic_id,
                        "title": title,
                        "status": status,
                        "priority": priority,
                        "description": description,
                        "checklist": checklist,
                    })
                    updated = True
                    break
            if not updated:
                shots_data.append({
                    "id": shot_id,
                    "epic_id": epic_id,
                    "title": title,
                    "status": status,
                    "priority": priority,
                    "description": description,
                    "checklist": checklist,
                })
        elif op == "update_status":
            shot_id = request.query_params.get("id")
            new_status = (form.get("status") or "todo").lower()
            if new_status not in {"todo", "doing", "done"}:
                new_status = "todo"
            for s in shots_data:
                if s.get("id") == shot_id:
                    s["status"] = new_status
                    break
        elif op == "delete":
            shot_id = request.query_params.get("id")
            shots_data = [s for s in shots_data if s.get("id") != shot_id]
        shots_json = json.dumps(shots_data)
    # Render both the panel and an OOB tabs update, then concatenate.
    packs = {
        "pack_core": form.get("pack_core") or "on",
        "pack_opinionated": form.get("pack_opinionated"),
        "pack_strict": form.get("pack_strict"),
    }
    continuity_result = compute_continuity(script_text, rules_text, scenes_data, shots_data, packs)

    panel_html = templates.env.get_template("partials/panel.html").render(
        {
            "request": request,
            "tab": query_tab,
            "script_text": script_text,
            "rules_text": rules_text,
            "scenes_json": scenes_json,
            "scenes_data": scenes_data,
            "editing_scene": editing_scene,
            "shots_json": shots_json,
            "shots_data": shots_data,
            "editing_shot": editing_shot,
            "packs": packs,
            "result": continuity_result,
        }
    )
    tabs_html = templates.env.get_template("partials/tabs.html").render(
        {"request": request, "tab": query_tab, "oob": True}
    )
    return HTMLResponse(content=panel_html + tabs_html)
def compute_continuity(*args, **kwargs):
    return {"readiness": 100, "issues": []}


# continuity endpoint removed


@app.post("/export")
async def export(request: Request) -> StreamingResponse:
    form = await request.form()
    script_text = form.get("script_text", SCRIPT_DEFAULT)
    rules_text = form.get("rules_text", RULES_DEFAULT)
    scenes_json = form.get("scenes_json", json.dumps(SCENES_DEFAULT))
    shots_json = form.get("shots_json", json.dumps(SHOTS_DEFAULT))

    # Compose files per PRD: PRD.md, instructions.mdc, epics.json, tickets.json
    files = {
        "PRD.md": script_text,
        ".cursor/rules/instructions.mdc": rules_text,
        "epics.json": scenes_json,
        "tickets.json": shots_json,
    }

    import io, zipfile, time

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path, content in files.items():
            zf.writestr(path, content)
    buf.seek(0)
    timestamp = int(time.time())
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=artifacts_{timestamp}.zip",
        },
    )


# --- Share link utilities and endpoints (no DB) ---

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data_str: str) -> bytes:
    padding = "=" * (-len(data_str) % 4)
    return base64.urlsafe_b64decode(data_str + padding)


def _get_share_secret() -> bytes:
    # Prefer a stable secret if provided; otherwise generate ephemeral per-process
    secret = os.getenv("SHARE_SECRET")
    if secret:
        return secret.encode("utf-8")
    # Ephemeral fallback is fine for pre-prod/local usage
    if not hasattr(_get_share_secret, "_cached"):
        setattr(_get_share_secret, "_cached", secrets.token_urlsafe(32).encode("utf-8"))
    return getattr(_get_share_secret, "_cached")


def _serialize_project(script_text: str, rules_text: str, scenes_json: str, shots_json: str, packs: dict) -> str:
    # Store as a single JSON string; scenes/shots are passed as JSON strings from the form
    try:
        scenes = json.loads(scenes_json) if scenes_json else []
    except Exception:
        scenes = []
    try:
        shots = json.loads(shots_json) if shots_json else []
    except Exception:
        shots = []
    data = {
        "script_text": script_text,
        "rules_text": rules_text,
        "scenes": scenes,
        "shots": shots,
        "packs": packs,
        # Version for future compatibility
        "_v": 1,
    }
    return json.dumps(data, separators=(",", ":"))


@app.post("/api/share")
async def api_share(request: Request) -> JSONResponse:
    form = await request.form()
    script_text = form.get("script_text", SCRIPT_DEFAULT)
    rules_text = form.get("rules_text", RULES_DEFAULT)
    scenes_json = form.get("scenes_json", json.dumps(SCENES_DEFAULT))
    shots_json = form.get("shots_json", json.dumps(SHOTS_DEFAULT))
    packs = {
        "pack_core": form.get("pack_core") or "on",
        "pack_opinionated": form.get("pack_opinionated"),
        "pack_strict": form.get("pack_strict"),
    }

    payload_json = _serialize_project(script_text, rules_text, scenes_json, shots_json, packs)
    compressed = zlib.compress(payload_json.encode("utf-8"), level=9)
    payload = _b64url_encode(compressed)

    secret = _get_share_secret()
    sig_bytes = hmac.new(secret, payload.encode("ascii"), hashlib.sha256).digest()
    sig = _b64url_encode(sig_bytes)
    short_id = hashlib.sha256(compressed).hexdigest()[:8]

    base = str(request.base_url).rstrip("/")
    url = f"{base}/#p={short_id}.{payload}.{sig}"
    return JSONResponse({"id": short_id, "url": url, "payload": payload, "sig": sig})


@app.get("/api/decode")
async def api_decode(data: str) -> JSONResponse:
    # data format: <id>.<payload>.<sig>
    try:
        parts = data.split(".", 2)
        if len(parts) != 3:
            raise ValueError("invalid format")
        _id, payload, sig = parts
        secret = _get_share_secret()
        expected_sig = _b64url_encode(hmac.new(secret, payload.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected_sig):
            raise ValueError("bad signature")
        decompressed = zlib.decompress(_b64url_decode(payload))
        obj = json.loads(decompressed)
        return JSONResponse(obj)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid share data: {exc}")


# --- Healthcheck and error pages ---

@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    # Render a basic HTML error page for typical HTTP errors (e.g., 404)
    try:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "page_title": f"Error {exc.status_code}",
                "status_code": exc.status_code,
                "detail": getattr(exc, "detail", "") or "",
                "path": str(request.url.path),
            },
            status_code=exc.status_code,
        )
    except Exception:
        # Fallback to JSON if template fails for any reason
        return JSONResponse({"error": str(exc.detail) if hasattr(exc, "detail") else str(exc)}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    try:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "page_title": "Server Error",
                "status_code": 500,
                "detail": "An unexpected error occurred.",
                "path": str(request.url.path),
            },
            status_code=500,
        )
    except Exception:
        return JSONResponse({"error": "internal server error"}, status_code=500)

