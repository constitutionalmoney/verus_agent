"""Validate local knowledge links; optionally inspect an isolated wheel build.

No dependencies are installed. Wheel validation uses the existing setuptools
backend and only public tracked source plus the named new knowledge files.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlparse
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", action="store_true")
    args = parser.parse_args()
    documents = [ROOT / "README.md", ROOT / "verus-mobile-integration.md"]
    documents += sorted((ROOT / "knowledge").glob("*.md"))
    for document in documents:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            if urlparse(target).scheme or target.startswith("#"):
                continue
            relative = unquote(target.split("#", 1)[0])
            if not (document.parent / relative).is_file():
                raise SystemExit(f"Missing local link: {document.name}: {target}")
    print(f"Local Markdown links passed ({len(documents)} documents).")

    if not args.wheel:
        return 0
    import setuptools

    print(f"Existing wheel backend: setuptools {setuptools.__version__}; no installation.")
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    public_files = {p for p in tracked if p}
    public_files.update({"knowledge.py", "scripts/check_knowledge.py", "tests/test_knowledge.py"})
    public_files.update(p.relative_to(ROOT).as_posix() for p in (ROOT / "knowledge").glob("*.md"))
    public_files = {
        p for p in public_files
        if Path(p).name != "LOCAL_OPERATOR.md"
        and not p.endswith((".local.json", ".approval.json"))
    }
    # The temporary directory is uniquely allocated and resolved before cleanup.
    with tempfile.TemporaryDirectory(prefix="verus-knowledge-wheel-") as temporary:
        stage = Path(temporary).resolve()
        assert stage.parent == Path(tempfile.gettempdir()).resolve()
        for relative in sorted(public_files):
            source = ROOT / relative
            if not source.resolve().is_relative_to(ROOT.resolve()):
                raise SystemExit("Refusing source outside repository")
            destination = stage / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        # Synthetic local-only files verify exclusion without accessing real files.
        excluded = ["LOCAL_OPERATOR.md", "operator-approval.local.json", "synthetic.approval.json"]
        for filename in excluded:
            (stage / filename).write_text("SYNTHETIC EXCLUSION FIXTURE", encoding="utf-8")
        build = subprocess.run(
            [sys.executable, "-c", "from setuptools.build_meta import build_wheel; build_wheel('dist')"],
            cwd=stage, capture_output=True, text=True,
        )
        if build.returncode:
            print(build.stdout)
            print(build.stderr, file=sys.stderr)
            return build.returncode
        wheel, = (stage / "dist").glob("*.whl")
        with zipfile.ZipFile(wheel) as archive:
            names = set(archive.namelist())
            expected = {"verus_agent/knowledge.py"}
            expected.update("verus_agent/" + p for p in public_files if p.startswith("knowledge/"))
            assert expected <= names, "Knowledge content missing from wheel"
            assert not any(name.rsplit("/", 1)[-1] in excluded for name in names), "Local-only file leaked"
            # Inspect retrieval from the zipped package, outside the source checkout.
            environment = dict(os.environ, PYTHONPATH=str(wheel))
            smoke = subprocess.run(
                [sys.executable, "-c", "import verus_agent; assert '.whl' in verus_agent.__file__; "
                 "from verus_agent.knowledge import KNOWLEDGE_TOPICS, get_knowledge; "
                 "[get_knowledge(t) for t in KNOWLEDGE_TOPICS]; print('All 6 wheel topics readable offline.')"],
                cwd=stage.parent, env=environment, capture_output=True, text=True,
            )
            if smoke.returncode:
                print(smoke.stderr, file=sys.stderr)
                return smoke.returncode
            print(smoke.stdout.strip())
        print("Wheel contents and local-only exclusions passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
