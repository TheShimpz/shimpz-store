"""Static delivery contracts for the Store production image."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UV_IMAGE = "ghcr.io/astral-sh/uv:0.11.25@sha256:1e3808aa9023d0980e7c15b1fa7c1ac16ff35925780cf5c459858b2d693f01a9"


def _runtime_import_closure() -> set[str]:
    source = ROOT / "backend" / "app"
    pending = ["main"]
    modules = {"__init__"}
    while pending:
        module = pending.pop()
        if module in modules:
            continue
        modules.add(module)
        tree = ast.parse((source / f"{module}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module or not node.module.startswith("app."):
                continue
            imported = node.module.removeprefix("app.").split(".", 1)[0]
            if (source / f"{imported}.py").is_file():
                pending.append(imported)
    return {f"backend/app/{module}.py" for module in modules}


def test_static_runtime_packages_the_exact_application_import_closure():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    logical_lines = re.sub(r"\\\n\s*", " ", dockerfile).splitlines()
    runtime_copy = next(
        (line for line in logical_lines if line.startswith("COPY ") and "backend/app/main.py" in line),
        "",
    )
    packaged = set(re.findall(r"\bbackend/app/(?:__init__|[a-z][a-z0-9_]*)[.]py\b", runtime_copy))

    assert packaged == _runtime_import_closure()


def test_static_runtime_has_a_bounded_health_probe():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=20" in dockerfile


def test_static_runtime_copies_only_builder_resolved_dependencies():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    runtime = dockerfile.split(" AS serve\n", 1)[1]

    assert f"FROM {UV_IMAGE} AS uv" in dockerfile
    assert "COPY --from=uv /uv /usr/local/bin/uv" in dockerfile
    assert "COPY --from=dependencies /opt/venv /opt/venv" in runtime
    assert "uv-install.sh" not in dockerfile
    assert "apt-get" not in runtime
    assert "curl" not in runtime
    assert "/usr/local/bin/uv" not in runtime


def test_static_build_context_excludes_dependencies_caches_and_secrets():
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()

    assert {
        ".git",
        ".env",
        ".env.*",
        "**/.env",
        "**/.env.*",
        ".pnpm-store",
        ".venv",
        "backend/.venv",
        "frontend/.pnpm-store",
        "frontend/.svelte-kit",
        "frontend/build",
        "frontend/node_modules",
    } <= set(dockerignore)
