"""Error family shared by every server. API failures are tool execution errors (``isError``),
never protocol errors, as the MCP tools specification requires.

``classify`` maps a failed platform answer (an HTTP error status, or a failure reported inside a
200 envelope) to one kind. The TypeScript runtime's errors.ts implements the same table."""

import re


class PlatformError(Exception):
    kind = "upstream_error"

    def __init__(self, message: str, *, retry_after: float | None = None, status: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after
        self.status = status

    def payload(self) -> dict:
        out = {"error": self.kind, "message": str(self)}
        if self.retry_after is not None:
            out["retry_after_seconds"] = self.retry_after
        if self.status is not None:
            out["http_status"] = self.status
        return out


class AuthError(PlatformError):
    kind = "auth_error"


class RateLimited(PlatformError):
    kind = "rate_limited"


class NotSupported(PlatformError):
    kind = "not_supported"


class InvalidInput(PlatformError):
    kind = "invalid_input"


class NotFound(PlatformError):
    kind = "not_found"


class Conflict(PlatformError):
    kind = "conflict"


KINDS = {c.kind: c for c in (PlatformError, AuthError, RateLimited, InvalidInput, NotFound, Conflict)}

# wording that decides a 400/422 body (and a 200 envelope failure for the first two); case-insensitive
RATE_WORDS = re.compile(r"ratelimit|rate_limit|rate limit|call limit|too many|limit (?:your )?requests")
AUTH_WORDS = re.compile(r"api[ _-]?key|access[ _-]?token|unauthori[sz]ed|unauthenticated|credential|signature|not authori[sz]ed|forbidden|permission denied|invalid[ _-]token|expired[ _-]token")
NOT_FOUND_WORDS = re.compile(r"not found|does not exist|doesn't exist|not exist|no such")
VALIDATION_WORDS = re.compile(
    r"invalid|required|missing|must|malformed|validat|not (?:a |an )?valid|unknown (?:param|field|symbol|option|argument|value|key|currency|pair|market)|unsupported|unrecognized|\bexpected|incorrect|wrong|"
    r"bad request|out of range|not allowed|illegal|cannot be|should be|parameter|\bparam|field|format|parse|syntax|exceed|too (?:long|short|large|small|big)")


def _rule_matches(rule: dict, status: int, text: str) -> bool:
    want = rule.get("status")
    if want is not None and status not in (want if isinstance(want, list) else [want]):
        return False
    match = rule.get("match")
    return not match or str(match).lower() in text.lower()


def classify(status: int, text: str, *, method: str = "GET", rules: list | None = None, envelope: bool = False) -> type[PlatformError]:
    """The error kind for a failed answer. ``rules`` is the entry's ``adapter.error_kinds``
    ([{status, match, kind}], first match wins) for vendors that misuse codes; a rule without
    ``status`` matches any failure, ``status: 200`` matches failures reported inside a 200 envelope.

    Default table: 429 rate_limited; 401/403 auth_error; 404 (and 410) on a GET not_found, on a
    write invalid_input; 409 conflict; 400/422 by their body: rate-limit wording rate_limited,
    credential wording auth_error, 'not found' wording on a GET not_found, 422 or validation
    wording invalid_input, anything else upstream_error; other statuses upstream_error.
    Envelope failures: rate-limit wording rate_limited, auth wording auth_error, else upstream_error."""
    for rule in rules or []:
        if isinstance(rule, dict) and _rule_matches(rule, status, text) and rule.get("kind") in KINDS:
            return KINDS[rule["kind"]]
    low = (text or "").lower()
    read = method.upper() in ("GET", "HEAD")
    if envelope:
        if RATE_WORDS.search(low):
            return RateLimited
        if any(k in low for k in ("auth", "token", "unauthorized", "not_allowed", "forbidden")):
            return AuthError
        return PlatformError
    if status == 429:
        return RateLimited
    if status in (401, 403):
        # GitHub answers its primary rate limit with 403 'API rate limit exceeded': time, not the credentials
        return RateLimited if RATE_WORDS.search(low) else AuthError
    if status in (404, 410):
        return NotFound if read else InvalidInput
    if status == 409:
        return Conflict
    if status in (400, 422):
        if RATE_WORDS.search(low):
            return RateLimited
        if AUTH_WORDS.search(low):
            return AuthError
        if read and NOT_FOUND_WORDS.search(low):
            return NotFound
        if status == 422 or VALIDATION_WORDS.search(low):
            return InvalidInput
    return PlatformError


def message_for(kind: type[PlatformError], status: int, text: str) -> str:
    """The (unscrubbed) message for an HTTP failure: which party the model should act on."""
    body = (text or "").strip()
    if re.match(r"(?:<\?xml[^>]*>\s*)?<(?:!doctype\s+html|html[\s>])", body[:300], re.I):
        # an HTML error page: its title, not 300 characters of markup (CTFtime's 404, BCB's 'Requisição inválida!')
        t = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
        body = "HTML page" + (": " + " ".join(t.group(1).split())[:200] if t and t.group(1).strip() else "")
    body = body[:300]
    if kind is InvalidInput:
        return f"the platform rejected the request as invalid ({status}): {body}".rstrip(": ")
    if kind is NotFound:
        return f"not found ({status})" + (f": {body}" if body else "")
    if kind is Conflict:
        return f"conflict with the platform's current state ({status}): {body}".rstrip(": ")
    if kind is AuthError:
        return f"platform refused the credentials ({status}): {body[:200]}".rstrip(": ")
    return f"platform error {status}: {body}".rstrip(": ")
