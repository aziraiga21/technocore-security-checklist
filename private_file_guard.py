"""Fail-closed local permission audit for Technocore private files."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path


def audit_private_file(
    path: str | os.PathLike[str],
    *,
    expected_uid: int | None = None,
    platform: str | None = None,
) -> dict[str, object]:
    """Return a machine-readable audit of one local private file."""
    target = Path(path)
    metadata = target.stat(follow_symlinks=False)
    active_platform = sys.platform if platform is None else platform
    if active_platform == "win32":
        return {
            "path": str(target),
            "ok": False,
            "mode": None,
            "findings": [
                "Windows ACL not verified; POSIX mode bits are not a security boundary"
            ],
        }

    mode = stat.S_IMODE(metadata.st_mode)
    findings: list[str] = []
    is_regular = stat.S_ISREG(metadata.st_mode)
    if not is_regular:
        findings.append("path is not a regular file")
    exposed_bits = mode & 0o077
    if exposed_bits:
        findings.append(f"group/other permission bits are {exposed_bits:04o}")
    owner_uid = os.getuid() if expected_uid is None else expected_uid
    if metadata.st_uid != owner_uid:
        findings.append(
            f"owner uid {metadata.st_uid} does not match expected uid {owner_uid}"
        )
    return {
        "path": str(target),
        "ok": is_regular and mode == 0o600 and metadata.st_uid == owner_uid,
        "mode": f"{mode:04o}",
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed permission audit for a Technocore private file."
    )
    parser.add_argument("path")
    args = parser.parse_args(argv)
    try:
        result = audit_private_file(args.path)
    except OSError as error:
        result = {
            "path": args.path,
            "ok": False,
            "mode": None,
            "findings": [f"cannot inspect path: {error.strerror or error}"],
        }
        print(json.dumps(result, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
