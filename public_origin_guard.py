import argparse
import ipaddress
import json
import re


class OriginError(ValueError):
    """An untrusted public origin is not safe to publish."""


_DNS_RE = re.compile(
    r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?",
    re.ASCII,
)


def _port_suffix(port: str | None) -> str:
    if port is None:
        return ""
    if not port.isascii() or not port.isdecimal() or str(int(port)) != port:
        raise OriginError("authority port must be canonical decimal")
    if not 1 <= int(port) <= 65535:
        raise OriginError("authority port must be between 1 and 65535")
    return f":{port}"


def _canonical_authority(authority: str) -> str:
    if authority.startswith("["):
        close = authority.find("]")
        if close < 0:
            raise OriginError("authority has an unterminated IPv6 address")
        literal = authority[1:close]
        remainder = authority[close + 1 :]
        port = None
        if remainder:
            if not remainder.startswith(":"):
                raise OriginError("authority contains data after IPv6 address")
            port = remainder[1:]
        try:
            address = ipaddress.IPv6Address(literal)
        except ValueError as error:
            raise OriginError("authority contains an invalid IPv6 address") from error
        return f"[{address.compressed}]{_port_suffix(port)}"

    if authority.count(":") > 1:
        raise OriginError("authority IPv6 addresses must be bracketed")
    host, separator, port = authority.rpartition(":")
    if not separator:
        host, port = authority, None
    if not host:
        raise OriginError("authority host is empty")

    lowered = host.lower()
    try:
        canonical_host = str(ipaddress.IPv4Address(lowered))
    except ValueError:
        if "." in lowered and all(character.isdigit() or character == "." for character in lowered):
            raise OriginError("authority contains an invalid IPv4 address")
        if not _DNS_RE.fullmatch(lowered):
            raise OriginError("authority must contain a valid DNS host or IP address")
        canonical_host = lowered
    return canonical_host + _port_suffix(port)


def validate_public_origin(scheme: str, authority: str) -> str:
    canonical_scheme = scheme.lower()
    if canonical_scheme not in {"http", "https"}:
        raise OriginError("scheme must be http or https")
    canonical_authority = _canonical_authority(authority)
    return f"{canonical_scheme}://{canonical_authority}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate an untrusted authority before publishing absolute URLs."
    )
    parser.add_argument("scheme")
    parser.add_argument("authority")
    arguments = parser.parse_args()

    try:
        result = {"ok": True, "origin": validate_public_origin(arguments.scheme, arguments.authority)}
        exit_code = 0
    except OriginError as error:
        result = {"findings": [str(error)], "ok": False}
        exit_code = 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
