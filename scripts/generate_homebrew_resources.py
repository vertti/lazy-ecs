#!/usr/bin/env python3
"""Print Homebrew resource blocks for lazy-ecs runtime dependencies, pinned to uv.lock."""

import subprocess
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def render_resources(export: str, lock: dict[str, Any]) -> str:
    packages = {p["name"]: p for p in lock["package"]}
    blocks = []
    for line in export.splitlines():
        requirement = line.split(";")[0].strip()
        if not requirement:
            continue
        name = requirement.split("==")[0]
        sdist = packages[name]["sdist"]
        sha256 = sdist["hash"].removeprefix("sha256:")
        blocks.append(f'  resource "{name}" do\n    url "{sdist["url"]}"\n    sha256 "{sha256}"\n  end')
    return "\n\n".join(blocks)


def main() -> None:
    export = subprocess.run(
        [  # noqa: S607
            "uv",
            "export",
            "--frozen",
            "--no-dev",
            "--no-emit-project",
            "--no-hashes",
            "--no-header",
            "--no-annotate",
            "--quiet",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    print(render_resources(export, lock))


if __name__ == "__main__":
    main()
