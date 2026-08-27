"""Reject high-confidence private material from the public repository.

This is intentionally conservative: loopback/bind addresses and documentation
placeholders are allowed, while non-loopback IPv4 literals, private-key blocks,
credential-bearing URLs, and wallet artifacts fail the check.
"""

from __future__ import annotations

import ipaddress
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".dockerignore",
    ".gitignore",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yml",
    ".yaml",
}
FORBIDDEN_NAMES = {"wallet.dat", "LOCAL_OPERATOR.md"}
SECRET_PATTERNS = {
    "private key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "credential-bearing URL": re.compile(r"https?://[^\s/:]+:[^\s/@]+@", re.IGNORECASE),
    "unencrypted WIF assignment": re.compile(
        r"(?:WIF|private[_-]?key|seed[_-]?phrase)\s*[:=]\s*[KL5][1-9A-HJ-NP-Za-km-z]{40,}",
        re.IGNORECASE,
    ),
}
IPV4 = re.compile(r"(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])")


def tracked_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
    ).decode("utf-8", errors="strict")
    return [ROOT / value for value in output.split("\0") if value]


def main() -> int:
    failures: list[str] = []
    for path in tracked_files():
        relative = path.relative_to(ROOT).as_posix()
        if path.name in FORBIDDEN_NAMES or path.name.endswith((".sqlite", ".sqlite-wal", ".sqlite-shm")):
            failures.append(f"{relative}: forbidden local/runtime file")
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                failures.append(f"{relative}: {label}")
        for match in IPV4.finditer(text):
            try:
                address = ipaddress.ip_address(match.group(0))
            except ValueError:
                continue
            if not (address.is_loopback or address.is_unspecified):
                failures.append(f"{relative}: non-loopback IPv4 literal")

    if failures:
        print("Public-content check failed:", file=sys.stderr)
        for failure in sorted(set(failures)):
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("Public-content check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
