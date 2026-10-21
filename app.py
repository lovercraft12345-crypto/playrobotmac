"""Backend de prueba para cuentas y suscripciones Premium de PlayRobot.

El Access Token de Mercado Pago vive solamente en este proceso servidor.
La aplicación de escritorio nunca debe recibirlo.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from functools import wraps
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash
from account_client import FREE_MISSIONS

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024
configured_secret = os.getenv("APP_SECRET_KEY", "").strip()
if len(configured_secret) < 32 or configured_secret.startswith("cambia-"):
    configured_secret = secrets.token_urlsafe(48)
app.config["SECRET_KEY"] = configured_secret
DB_PATH = Path(os.getenv("DATABASE_PATH", str(ROOT / "playrobot.db")))
MP_API = "https://api.mercadopago.com"
TOKEN_MAX_AGE = 7 * 24 * 60 * 60


def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with db_connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                mp_id TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL,
                payer_email TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_subscriptions_user
                ON subscriptions(user_id, updated_at DESC);
            """
        )


init_db()
serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="playrobot-session-v1")
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["120 per hour"],
    storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
)


def api_error(message: str, status: int):
    return jsonify({"error": message}), status


def normalize_email(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    email = value.strip().lower()
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        return None
    return email


def token_for(user_id: int) -> str:
    return serializer.dumps({"uid": user_id})


def current_user_id() -> int | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        data = serializer.loads(auth[7:].strip(), max_age=TOKEN_MAX_AGE)
        return int(data["uid"])
    except (BadSignature, SignatureExpired, KeyError, TypeError, ValueError):
        return None


def authenticated(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        user_id = current_user_id()
        if user_id is None:
            return api_error("Inicia sesión para continuar.", 401)
        request.user_id = user_id  # type: ignore[attr-defined]
        return fn(*args, **kwargs)

    return wrapped


def mp_request(method: str, path: str, payload: dict | None = None) -> dict:
    access_token = os.getenv("MP_ACCESS_TOKEN", "").strip()
    if not access_token:
        raise RuntimeError("Falta MP_ACCESS_TOKEN en el archivo .env del servidor.")
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(
        MP_API + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Idempotency-Key": hashlib.sha256(
                f"{method}:{path}:{time.time_ns()}".encode()
            ).hexdigest(),
        },
    )
    try:
        with urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise ValueError(f"Mercado Pago respondió HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError) as exc:
        raise ValueError("No se pudo conectar con Mercado Pago.") from exc


def public_base_url() -> str:
    value = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if not value.startswith("https://"):
        raise RuntimeError("PUBLIC_BASE_URL debe ser una dirección HTTPS pública.")
    return value


def subscription_is_active(user_id: int) -> bool:
    with db_connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM subscriptions WHERE user_id = ? AND status = 'authorized' LIMIT 1",
            (user_id,),
        ).fetchone()
    return row is not None


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "PlayRobot Suscripciones", "mode": "test"})


@app.post("/api/auth/register")
@limiter.limit("5 per hour")
def register():
    body = request.get_json(silent=True) or {}
    email = normalize_email(body.get("email"))
    password = body.get("password")
    if not email:
        return api_error("Escribe un correo válido del padre, madre o tutor.", 400)
    if not isinstance(password, str) or len(password) < 12:
        return api_error("La contraseña debe tener al menos 12 caracteres.", 400)
    try:
        with db_connect() as conn:
            cur = conn.execute(
                "INSERT INTO users(email, password_hash) VALUES (?, ?)",
                (email, generate_password_hash(password, method="scrypt")),
            )
            user_id = int(cur.lastrowid)
    except sqlite3.IntegrityError:
        return api_error("Ya existe una cuenta con ese correo.", 409)
    return jsonify({"token": token_for(user_id), "email": email, "free_levels": 6}), 201


@app.post("/api/auth/login")
@limiter.limit("10 per minute")
def login():
    body = request.get_json(silent=True) or {}
    email = normalize_email(body.get("email"))
    password = body.get("password")
    if not email or not isinstance(password, str):
        return api_error("Correo o contraseña incorrectos.", 401)
    with db_connect() as conn:
        row = conn.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,)).fetchone()
    if row is None or not check_password_hash(row["password_hash"], password):
        return api_error("Correo o contraseña incorrectos.", 401)
    return jsonify({"token": token_for(int(row["id"])), "email": email})


def account_summary(user_id: int) -> dict | None:
    with db_connect() as conn:
        user = conn.execute("SELECT email FROM users WHERE id = ?", (user_id,)).fetchone()
        sub = conn.execute(
            "SELECT status FROM subscriptions WHERE user_id = ? "
            "ORDER BY (status = 'authorized') DESC, updated_at DESC, id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    if user is None:
        return None
    return {
        "email": user["email"], "premium": subscription_is_active(user_id),
        "free_levels": 6, "premium_levels": "7+", "free_missions": sorted(FREE_MISSIONS),
        "subscription_status": sub["status"] if sub else "none",
        "premium_monthly_price_mxn": os.getenv("PREMIUM_MONTHLY_PRICE_MXN", "99"),
        "billing_mode": os.getenv("BILLING_MODE", "test"),
    }


@app.get("/api/me")
@authenticated
def me():
    info = account_summary(request.user_id)
    return jsonify(info) if info is not None else api_error("La cuenta ya no existe.", 401)


@app.post("/api/access")
@limiter.limit("360 per hour", override_defaults=True)
@authenticated
def mission_access():
    body = request.get_json(silent=True) or {}
    mission = body.get("mission")
    known = FREE_MISSIONS | {"drive", "obstacle", "free", "parking", "final"}
    if not isinstance(mission, str) or mission not in known:
        return api_error("Misión desconocida.", 400)
    info = account_summary(request.user_id)
    if info is None:
        return api_error("La cuenta ya no existe.", 401)
    free = mission in FREE_MISSIONS and body.get("challenge", False) is False
    return jsonify({"allowed": free or info["premium"], "premium": info["premium"], "mission": mission})


@app.post("/api/billing/sync")
@limiter.limit("12 per minute", override_defaults=True)
@authenticated
def sync_subscription():
    """Recupera actualizaciones perdidas consultando registros del usuario autenticado."""
    user_id = request.user_id
    with db_connect() as conn:
        rows = conn.execute(
            "SELECT mp_id FROM subscriptions WHERE user_id = ? "
            "AND status IN ('pending', 'authorized', 'paused') ORDER BY id DESC",
            (user_id,),
        ).fetchall()
    updates = []
    try:
        for row in rows:
            data = mp_request("GET", f"/preapproval/{row['mp_id']}")
            if (str(data.get("id")) != row["mp_id"]
                    or data.get("external_reference") != f"playrobot-user-{user_id}"):
                raise ValueError("La suscripción no coincide con la cuenta.")
            status = data.get("status")
            if status not in ("pending", "authorized", "paused", "cancelled"):
                raise ValueError("Estado de suscripción no reconocido.")
            updates.append((status, row["mp_id"], user_id))
        with db_connect() as conn:
            conn.executemany(
                "UPDATE subscriptions SET status=?, updated_at=CURRENT_TIMESTAMP WHERE mp_id=? AND user_id=?",
                updates,
            )
        info = account_summary(user_id)
        return jsonify(info) if info is not None else api_error("La cuenta ya no existe.", 401)
    except (RuntimeError, ValueError, KeyError) as exc:
        app.logger.warning("No se pudo sincronizar la cuenta: %s", exc)
        return api_error("No se pudo verificar la suscripción en Mercado Pago. Intenta de nuevo.", 502)


@app.post("/api/billing/checkout")
@limiter.limit("5 per hour")
@authenticated
def checkout():
    body = request.get_json(silent=True) or {}
    with db_connect() as conn:
        user = conn.execute("SELECT email FROM users WHERE id = ?", (request.user_id,)).fetchone()
    if user is None:
        return api_error("La cuenta ya no existe.", 401)
    if subscription_is_active(request.user_id):
        return api_error("Tu cuenta ya tiene Premium activo.", 409)
    payer_email = normalize_email(body.get("payer_email") or user["email"])
    if not payer_email:
        return api_error("Revisa el correo de pago de Mercado Pago.", 400)
    try:
        base_url = public_base_url()
        amount = float(os.getenv("PREMIUM_MONTHLY_PRICE_MXN", "99"))
        if not (0 < amount <= 100000):
            raise RuntimeError("PREMIUM_MONTHLY_PRICE_MXN debe ser mayor a cero.")
        result = mp_request("POST", "/preapproval", {
            "reason": "PlayRobot Premium",
            "external_reference": f"playrobot-user-{request.user_id}",
            "payer_email": payer_email,
            "auto_recurring": {
                "frequency": 1,
                "frequency_type": "months",
                "transaction_amount": amount,
                "currency_id": os.getenv("CURRENCY_ID", "MXN").strip() or "MXN",
            },
            "back_url": f"{base_url}/billing/return",
            "notification_url": f"{base_url}/webhooks/mercadopago",
            "status": "pending",
        })
        mp_id = str(result["id"])
        status = str(result.get("status", "pending"))
        with db_connect() as conn:
            conn.execute(
                "INSERT INTO subscriptions(user_id, mp_id, status, payer_email) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(mp_id) DO UPDATE SET status=excluded.status, payer_email=excluded.payer_email, "
                "updated_at=CURRENT_TIMESTAMP",
                (request.user_id, mp_id, status, payer_email),
            )
        checkout_url = result.get("init_point") or result.get("sandbox_init_point")
        if not checkout_url:
            return api_error("Mercado Pago no devolvió el enlace de autorización.", 502)
        return jsonify({"checkout_url": checkout_url, "status": status}), 201
    except (RuntimeError, ValueError, KeyError) as exc:
        app.logger.warning("No se pudo iniciar checkout: %s", exc)
        return api_error(str(exc), 503 if isinstance(exc, RuntimeError) else 502)


def verify_webhook_signature(data_id: str, signature: str, request_id: str, secret: str) -> bool:
    values = {}
    for item in signature.split(","):
        if "=" in item:
            key, value = item.strip().split("=", 1)
            values[key] = value
    timestamp, received = values.get("ts"), values.get("v1")
    if not timestamp or not received or not data_id or not request_id or not secret:
        return False
    manifest = f"id:{data_id.lower()};request-id:{request_id};ts:{timestamp};"
    expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received)


@app.post("/webhooks/mercadopago")
def mercadopago_webhook():
    secret = os.getenv("MP_WEBHOOK_SECRET", "").strip()
    if not secret:
        return api_error("Webhook aún no configurado.", 503)
    body = request.get_json(silent=True) or {}
    data_id = request.args.get("data.id") or str((body.get("data") or {}).get("id", ""))
    signature = request.headers.get("x-signature", "")
    request_id = request.headers.get("x-request-id", "")
    if not verify_webhook_signature(data_id, signature, request_id, secret):
        return api_error("Firma de notificación inválida.", 401)
    event_type = body.get("type") or request.args.get("type")
    app.logger.warning(
        "Webhook recibido: tipo_cuerpo=%s tipo_url=%s data_id=%s",
        body.get("type"),
        request.args.get("type"),
        data_id,
    )
    if event_type not in ("subscription_preapproval", "preapproval"):
        return jsonify({"received": True, "ignored": True})
    try:
        subscription = mp_request("GET", f"/preapproval/{data_id}")
        external_ref = str(subscription.get("external_reference", ""))
        match = re.fullmatch(r"playrobot-user-(\d+)", external_ref)
        if not match:
            return jsonify({"received": True, "ignored": True})
        user_id = int(match.group(1))
        mp_id = str(subscription["id"])
        status = str(subscription.get("status", "unknown"))
        payer_email = normalize_email(subscription.get("payer_email")) or ""
        with db_connect() as conn:
            conn.execute(
                "INSERT INTO subscriptions(user_id, mp_id, status, payer_email) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(mp_id) DO UPDATE SET status=excluded.status, payer_email=excluded.payer_email, "
                "updated_at=CURRENT_TIMESTAMP",
                (user_id, mp_id, status, payer_email),
            )
        return jsonify({"received": True})
    except (RuntimeError, ValueError, KeyError) as exc:
        app.logger.warning("No se pudo actualizar suscripción: %s", exc)
        return api_error("No se pudo consultar la suscripción en Mercado Pago.", 502)


@app.post("/api/billing/cancel")
@limiter.limit("5 per hour")
@authenticated
def cancel_subscription():
    user_id = request.user_id  # type: ignore[attr-defined]
    with db_connect() as conn:
        row = conn.execute(
            "SELECT mp_id FROM subscriptions WHERE user_id = ? AND status IN ('authorized', 'pending') "
            "ORDER BY updated_at DESC, id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    if row is None:
        return api_error("No hay una suscripción activa para cancelar.", 404)
    try:
        mp_request("PUT", f"/preapproval/{row['mp_id']}", {"status": "cancelled"})
        with db_connect() as conn:
            conn.execute(
                "UPDATE subscriptions SET status='cancelled', updated_at=CURRENT_TIMESTAMP "
                "WHERE mp_id=? AND user_id=?",
                (row["mp_id"], user_id),
            )
        return jsonify({"cancelled": True, "premium": subscription_is_active(user_id)})
    except (RuntimeError, ValueError) as exc:
        app.logger.warning("No se pudo cancelar suscripción: %s", exc)
        return api_error("No se pudo cancelar en Mercado Pago.", 502)


@app.get("/billing/return")
def billing_return():
    return (
        "<!doctype html><html lang='es'><meta charset='utf-8'><title>PlayRobot</title>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<body style='font:18px system-ui;max-width:600px;margin:12vh auto;padding:24px;color:#17212b'>"
        "<h1>¡Gracias!</h1><p>Mercado Pago recibió tu solicitud. Regresa a PlayRobot y vuelve a iniciar sesión; "
        "pulsa Mi cuenta → Ya pagué · Actualizar Premium para verificar el estado.</p></body></html>",
        200,
        {"Content-Type": "text/html; charset=utf-8"},
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8001"))
    # Local testing only. Production hosting must use a WSGI server and HTTPS.
    app.run(host="127.0.0.1", port=port, debug=False)
