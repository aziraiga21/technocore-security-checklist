import json
import re
import sys
from urllib.parse import parse_qsl, urlsplit


_BUDGET_FOOTER = re.compile(
    r"\n# budget: (?:0|[1-9][0-9]*) of [1-9][0-9]* reads left this minute "
    r"\(refills [^;\r\n()]+; a 429 states the wait, and the full limits are "
    r"in /\.well-known/agent\.json\)\Z",
    re.ASCII,
)
_REQUIRED_FIELDS = {"method", "path", "status", "headers", "body"}


class CachePrivacyError(ValueError):
    """A captured read response violates the shared-cache privacy boundary."""


def _read_route(target: str) -> str:
    if not isinstance(target, str) or not target.startswith("/") or any(
        ord(character) < 32 or character == "\\" for character in target
    ):
        raise CachePrivacyError("path is malformed")
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or parts.fragment:
        raise CachePrivacyError("path is malformed")
    segments = parts.path.split("/")[1:]
    if segments == ["rooms"]:
        return "read"
    if len(segments) == 2 and segments[0] == "r" and segments[1]:
        return "read"
    if len(segments) in {2, 3} and segments[0] == "kv" and all(segments[1:]):
        return "read"
    raise CachePrivacyError("route is not a shareable Technocore read lane")


def _is_long_poll(target: str) -> bool:
    parts = urlsplit(target)
    if not parts.path.startswith("/r/"):
        return False
    try:
        pairs = parse_qsl(parts.query, keep_blank_values=True, max_num_fields=100)
    except ValueError as error:
        raise CachePrivacyError("path has too many query parameters") from error
    values = [value for name, value in pairs if name == "wait"]
    try:
        return bool(values) and float(values[-1]) > 0
    except ValueError:
        return False


def _headers(source: object) -> dict[str, str]:
    if not isinstance(source, dict):
        raise CachePrivacyError("headers must be an object")
    headers = {}
    for name, value in source.items():
        if not isinstance(name, str) or not isinstance(value, str):
            raise CachePrivacyError("headers must contain string names and values")
        lowered = name.lower()
        if lowered in headers:
            raise CachePrivacyError(f"duplicate header after case folding: {lowered}")
        if not lowered or any(ord(character) <= 32 or character == ":" for character in name):
            raise CachePrivacyError("header name is malformed")
        if "\r" in value or "\n" in value:
            raise CachePrivacyError("header value is malformed")
        headers[lowered] = value
    return headers


def _cache_directives(value: str) -> dict[str, str | None]:
    directives = {}
    for raw in value.split(","):
        item = raw.strip()
        if not item:
            raise CachePrivacyError("cache-control contains an empty directive")
        name, separator, argument = item.partition("=")
        name = name.lower()
        if not re.fullmatch(r"[a-z][a-z0-9-]*", name) or (separator and not argument):
            raise CachePrivacyError("cache-control contains a malformed directive")
        if name in directives:
            raise CachePrivacyError(f"cache-control repeats {name}")
        directives[name] = argument if separator else None
    return directives


def _validate_shared_directives(directives: dict[str, str | None]) -> None:
    if "s-maxage" not in directives:
        return
    if "no-store" in directives or directives.get("public", "missing") is not None:
        raise CachePrivacyError("cache-control mixes sharing with no-store or omits public")
    if directives.get("max-age") != "0":
        raise CachePrivacyError("cache-control must keep client max-age at zero")
    s_maxage = directives["s-maxage"]
    if s_maxage is None or not s_maxage.isascii() or not s_maxage.isdecimal() or int(s_maxage) < 1:
        raise CachePrivacyError("cache-control s-maxage must be a positive ASCII integer")
    if "stale-while-revalidate" in directives:
        stale = directives["stale-while-revalidate"]
        if stale is None or not stale.isascii() or not stale.isdecimal():
            raise CachePrivacyError(
                "cache-control stale-while-revalidate must be a non-negative ASCII integer"
            )


def validate_read_response(response: dict) -> dict:
    """Validate that caller-specific read metadata cannot enter a shared cache."""
    if not isinstance(response, dict) or set(response) != _REQUIRED_FIELDS:
        raise CachePrivacyError("response must contain exactly method, path, status, headers, and body")
    if response["method"] != "GET":
        raise CachePrivacyError("only GET responses are in scope")
    route = _read_route(response["path"])
    status = response["status"]
    if type(status) is not int or not 100 <= status <= 599:
        raise CachePrivacyError("status must be an integer from 100 through 599")
    headers = _headers(response["headers"])
    body = response["body"]
    if not isinstance(body, str):
        raise CachePrivacyError("body must be a string")
    cache_control = headers.get("cache-control")
    directives = _cache_directives(cache_control) if cache_control is not None else {}
    _validate_shared_directives(directives)
    directive_names = set(directives)
    footer = bool(_BUDGET_FOOTER.search(body))
    long_poll = _is_long_poll(response["path"])
    private = footer or long_poll
    shareable = "s-maxage" in directive_names
    if shareable and status != 200:
        raise CachePrivacyError("only a successful 200 response may be shared")
    if footer and shareable:
        raise CachePrivacyError("caller-specific budget footer is marked shareable")
    if long_poll and shareable:
        raise CachePrivacyError("long-poll response is marked shareable")
    if private and "no-store" not in directive_names:
        raise CachePrivacyError("caller-specific response must be no-store")
    return {
        "ok": True,
        "private": private,
        "route": route,
        "shareable": shareable,
    }


def main() -> int:
    try:
        response = json.load(sys.stdin)
        decision = validate_read_response(response)
        exit_code = 0
    except (CachePrivacyError, json.JSONDecodeError) as error:
        decision = {"findings": [str(error)], "ok": False, "shareable": False}
        exit_code = 1
    print(json.dumps(decision, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
