import argparse
import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_LIMIT = re.compile(r"[0-9]{1,9}\Z", re.ASCII)


class CacheKeyError(ValueError):
    """A request cannot safely share a cached `/rooms` response."""


def canonical_rooms_key(url: str, *, max_limit: int = 200, method: str = "GET") -> str:
    """Return the canonical GET key for a safely shareable `/rooms` request."""
    if method != "GET":
        raise CacheKeyError("only a GET request is shareable")
    if type(max_limit) is not int or max_limit < 1:
        raise CacheKeyError("max_limit must be a positive integer")
    if not isinstance(url, str) or not url:
        raise CacheKeyError("URL must be an absolute HTTP(S) URL")

    try:
        parts = urlsplit(url)
        hostname = parts.hostname
        port = parts.port
    except ValueError as error:
        raise CacheKeyError("URL is malformed") from error
    if parts.scheme not in {"http", "https"} or not parts.netloc or hostname is None:
        raise CacheKeyError("URL must be an absolute HTTP(S) URL")
    if parts.username is not None or parts.password is not None:
        raise CacheKeyError("userinfo is not shareable")
    if parts.fragment:
        raise CacheKeyError("fragment is not shareable")
    if parts.path != "/rooms":
        raise CacheKeyError("path must be exactly /rooms")
    if any(ord(character) < 33 or character == "\\" for character in url):
        raise CacheKeyError("URL is malformed")

    try:
        pairs = parse_qsl(parts.query, keep_blank_values=True, strict_parsing=False, max_num_fields=100)
    except ValueError as error:
        raise CacheKeyError("too many query parameters") from error
    relevant = {"format": [], "limit": []}
    for name, value in pairs:
        if name in relevant:
            relevant[name].append(value)
    for name, values in relevant.items():
        if len(values) > 1:
            raise CacheKeyError(f"duplicate {name} parameter is ambiguous")

    query = {}
    if relevant["format"] == ["json"]:
        query["format"] = "json"
    if relevant["limit"]:
        raw = relevant["limit"][0]
        if not _LIMIT.fullmatch(raw):
            raise CacheKeyError("limit must contain 1-9 ASCII digits")
        query["limit"] = str(min(int(raw) or 1, max_limit))

    host = hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    default_port = (parts.scheme.lower() == "http" and port == 80) or (
        parts.scheme.lower() == "https" and port == 443
    )
    authority = host if port is None or default_port else f"{host}:{port}"
    return urlunsplit((parts.scheme.lower(), authority, "/rooms", urlencode(sorted(query.items())), ""))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Derive a safe shared-cache key for one Technocore /rooms GET request."
    )
    parser.add_argument("url")
    parser.add_argument("--max-limit", type=int, default=200)
    parser.add_argument("--method", default="GET")
    arguments = parser.parse_args()

    try:
        key = canonical_rooms_key(
            arguments.url, max_limit=arguments.max_limit, method=arguments.method
        )
        result = {"cache_key": key, "ok": True, "shareable": True}
        exit_code = 0
    except CacheKeyError as error:
        result = {"findings": [str(error)], "ok": False, "shareable": False}
        exit_code = 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
