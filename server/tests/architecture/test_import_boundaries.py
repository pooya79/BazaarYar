from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SERVER = ROOT / "server"


def _iter_python_files(base: Path) -> list[Path]:
    return sorted(
        file
        for file in base.rglob("*.py")
        if "__pycache__" not in file.parts and ".venv" not in file.parts
    )


def _imports_for(file_path: Path) -> list[tuple[str, int]]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    imports: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level > 0:
                module = f"{'.' * node.level}{module}"
            imports.append((module, node.lineno))
    return imports


def test_feature_service_and_repo_do_not_import_api_modules() -> None:
    violations: list[str] = []
    for file_path in _iter_python_files(SERVER / "features"):
        if file_path.name not in {"service.py", "repo.py"}:
            continue
        for module, lineno in _imports_for(file_path):
            if module.startswith("server.") and "api" in module.split("server.", 1)[1].split("."):
                violations.append(f"{file_path}:{lineno} imports '{module}'")
            if module.startswith(".api"):
                violations.append(f"{file_path}:{lineno} imports '{module}'")
    assert not violations, "Service/repo modules cannot import API modules:\n" + "\n".join(violations)


def test_chat_and_tables_features_do_not_import_agent_runtime() -> None:
    violations: list[str] = []
    for feature_name in ("chat", "tables"):
        for file_path in _iter_python_files(SERVER / "features" / feature_name):
            for module, lineno in _imports_for(file_path):
                if module.startswith("server.agents"):
                    violations.append(f"{file_path}:{lineno} imports '{module}'")
                if module.startswith("server.features.agent"):
                    violations.append(f"{file_path}:{lineno} imports '{module}'")
    assert not violations, "Chat/tables modules cannot import agent runtime modules:\n" + "\n".join(violations)


def test_business_modules_do_not_import_legacy_agents_attachments() -> None:
    forbidden_prefixes = (
        "server.agents.attachments",
        "server.domain",
        "server.api.agents.router",
        "server.api.conversations.router",
        "server.api.tables.router",
    )
    violations: list[str] = []
    for file_path in _iter_python_files(SERVER / "features"):
        for module, lineno in _imports_for(file_path):
            if any(module == prefix or module.startswith(f"{prefix}.") for prefix in forbidden_prefixes):
                violations.append(f"{file_path}:{lineno} imports '{module}'")
    assert not violations, "Feature modules cannot import removed legacy paths:\n" + "\n".join(violations)
