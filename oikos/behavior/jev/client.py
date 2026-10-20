"""Client for Jev (TypeSafe) through the OpenRouter Decisions API.

    POST https://openrouter.ai/api/alpha/decisions
    {"model": ..., "state": {...}, "questions": {...}}

The API key is read only from the environment variable OPENROUTER_API_KEY.
It is placed in the Authorization header of the outgoing request and in
nothing else: not in the returned records, not in exceptions, not in logs.

Every call returns a CallRecord, also when it fails. Failures are never
turned into a default decision here; the caller decides what an error means
and the record says exactly what went wrong.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Callable, Protocol

DEFAULT_ENDPOINT = "https://openrouter.ai/api/alpha/decisions"
KEY_ENV = "OPENROUTER_API_KEY"

# transport(url, body_bytes, headers, timeout) -> (http_status, response_bytes)
Transport = Callable[[str, bytes, dict, float], tuple[int, bytes]]


class JevError(RuntimeError):
    """Base class; `kind` is the short error type written to logs."""

    kind = "error"


class MissingKeyError(JevError):
    kind = "missing_key"


class TransportError(JevError):
    kind = "connection"


class HTTPStatusError(JevError):
    kind = "http_status"


class ResponseFormatError(JevError):
    kind = "response_format"


class InvalidActionError(JevError):
    kind = "invalid_action"


class ReplayMissError(JevError):
    kind = "replay_miss"


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _ordered(obj, keep_order: bool = False):
    """Sort all object keys, except the options of a question ("criteria"),
    whose order is part of the question as shown to the model."""
    if isinstance(obj, dict):
        items = obj.items() if keep_order else sorted(obj.items())
        return {k: _ordered(v, keep_order=(k == "criteria")) for k, v in items}
    if isinstance(obj, list):
        return [_ordered(v) for v in obj]
    return obj


def wire(body: dict) -> bytes:
    """Exact bytes sent to the API. Identical to `canonical` whenever the
    options are listed in sorted order (as in all requests before
    the order tests), so earlier logs and hashes stay valid."""
    return json.dumps(_ordered(body), separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def request_hash(body: dict) -> str:
    return hashlib.sha256(wire(body)).hexdigest()


@dataclass
class CallRecord:
    request_sha256: str
    request: dict
    status: str                       # "ok" | "error"
    http_status: int | None = None
    response: dict | None = None
    error_kind: str | None = None
    error: str | None = None
    model_requested: str | None = None
    model_served: str | None = None   # dated snapshot reported by the API
    provider: str | None = None
    generation_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    latency_s: float | None = None
    attempts: int = 0
    replayed: bool = False
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def urllib_transport(url: str, body: bytes, headers: dict, timeout: float) -> tuple[int, bytes]:
    req = urllib.request.Request(url, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:  # a response with an error status is still a response
        return e.code, e.read()


class DecisionClient(Protocol):
    def decide(self, body: dict) -> CallRecord: ...


class JevClient:
    """Live client. Retries only on connection errors, 429 and 5xx."""

    RETRY_STATUS = {429, 500, 502, 503, 504, 524, 529}

    def __init__(self, endpoint: str = DEFAULT_ENDPOINT, timeout: float = 30.0, retries: int = 2,
                 transport: Transport | None = None, api_key: str | None = None, sleep=time.sleep):
        key = api_key if api_key is not None else os.environ.get(KEY_ENV, "")
        if not key.strip():
            raise MissingKeyError(f"environment variable {KEY_ENV} is not set")
        self._key = key.strip()
        self.endpoint = endpoint
        self.timeout = timeout
        self.retries = retries
        self.transport = transport or urllib_transport
        self.sleep = sleep

    def __repr__(self) -> str:  # never show the key
        return f"JevClient(endpoint={self.endpoint!r})"

    def _redact(self, text: str) -> str:
        return text.replace(self._key, "[REDACTED]")

    def decide(self, body: dict) -> CallRecord:
        rec = CallRecord(request_sha256=request_hash(body), request=body, status="error",
                         model_requested=body.get("model"))
        headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json",
                   "X-Title": "OIKOS"}
        data = wire(body)
        t0 = time.perf_counter()
        for attempt in range(self.retries + 1):
            rec.attempts = attempt + 1
            try:
                status, raw = self.transport(self.endpoint, data, headers, self.timeout)
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                rec.error_kind, rec.error = TransportError.kind, self._redact(f"{type(e).__name__}: {e}")[:300]
                if attempt < self.retries:
                    self.sleep(2 ** attempt)
                    continue
                break
            rec.http_status = status
            try:
                payload = json.loads(raw.decode("utf-8")) if raw else None
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = None
            if status != 200:
                msg = (payload or {}).get("error", {}).get("message") if isinstance(payload, dict) else None
                rec.error_kind = HTTPStatusError.kind
                rec.error = self._redact(f"HTTP {status}: {msg or raw[:200]!r}")[:300]
                if status in self.RETRY_STATUS and attempt < self.retries:
                    self.sleep(2 ** attempt)
                    continue
                break
            if not isinstance(payload, dict):
                rec.error_kind, rec.error = ResponseFormatError.kind, "response is not a JSON object"
                break
            rec.response = payload
            rec.status, rec.error_kind, rec.error = "ok", None, None
            break
        rec.latency_s = round(time.perf_counter() - t0, 4)
        if rec.response is not None:
            fill_metadata(rec)
        return rec


def fill_metadata(rec: CallRecord) -> None:
    r = rec.response or {}
    usage = r.get("usage") if isinstance(r.get("usage"), dict) else {}
    rec.model_served = r.get("model")
    rec.provider = r.get("provider")
    rec.generation_id = r.get("id")
    rec.input_tokens = usage.get("input_tokens")
    rec.output_tokens = usage.get("output_tokens")
    rec.cost_usd = usage.get("cost")


class ReplayClient:
    """Answers from a previous log by request hash; never touches the network.

    Identical requests (e.g. deliberate repeats) receive their recorded
    answers in the original order. A request that is not in the log, or asked
    more often than recorded, is an error, not a silent fallback."""

    def __init__(self, log_path: str | os.PathLike | None = None):
        self.records: dict[str, list[dict]] = {}
        if log_path is not None:
            self.load(log_path)

    def load(self, log_path: str | os.PathLike) -> None:
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                if d.get("type") == "call":
                    self.records.setdefault(d["request_sha256"], []).append(d)

    def decide(self, body: dict) -> CallRecord:
        h = request_hash(body)
        queue = self.records.get(h)
        if not queue:
            return CallRecord(request_sha256=h, request=body, status="error", model_requested=body.get("model"),
                              error_kind=ReplayMissError.kind, error="request not found in replay log", replayed=True)
        d = queue.pop(0)
        fields = {k: d[k] for k in CallRecord.__dataclass_fields__ if k in d}
        rec = CallRecord(**fields)
        rec.replayed = True
        return rec
