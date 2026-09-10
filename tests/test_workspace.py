"""Testes da Fase 10 (workspace de código, somente leitura): adapter de sistema
de arquivos (com segurança de caminho), serviço de contexto, roteamento do turno
de código e REST do workspace."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.brain.events import SourcesGathered, TokenGenerated
from backend.main import create_app
from backend.utils.errors import WorkspaceError
from backend.workspace.providers.local_fs import LocalFsWorkspace
from backend.workspace.service import WorkspaceService
from tests.conftest import FakeLLMProvider, build_conversation_service


def _make_project(root: Path) -> None:
    """Cria uma árvore de projeto de exemplo em ``root``."""
    (root / "main.py").write_text("print('oi')\n", encoding="utf-8")
    (root / "sub").mkdir()
    (root / "sub" / "util.py").write_text("def soma(a, b):\n    return a + b\n", encoding="utf-8")
    (root / "node_modules").mkdir()
    (root / "node_modules" / "junk.js").write_text("// ruído\n", encoding="utf-8")


def _ws(root: Path, **over) -> LocalFsWorkspace:
    opts = {
        "ignore_dirs": ["node_modules", ".git"],
        "max_file_kb": 256,
        "max_tree_entries": 2000,
    }
    opts.update(over)
    w = LocalFsWorkspace(**opts)
    return w


# --- Adapter: raiz, árvore, leitura, segurança ------------------------------


async def test_set_root_validates(tmp_path: Path) -> None:
    """set_root aceita diretório existente e recusa inexistente/arquivo."""
    _make_project(tmp_path)
    w = _ws(tmp_path)
    assert await w.set_root(str(tmp_path)) == str(tmp_path.resolve())
    with pytest.raises(WorkspaceError):
        await w.set_root(str(tmp_path / "nao_existe"))
    with pytest.raises(WorkspaceError):
        await w.set_root(str(tmp_path / "main.py"))


async def test_tree_ignores_noise(tmp_path: Path) -> None:
    """A árvore inclui os arquivos do projeto e ignora node_modules."""
    _make_project(tmp_path)
    w = _ws(tmp_path)
    await w.set_root(str(tmp_path))
    paths = {e.path for e in await w.tree()}
    assert "main.py" in paths
    assert "sub/util.py" in paths
    assert not any(p.startswith("node_modules") for p in paths)


async def test_read_file_and_truncation(tmp_path: Path) -> None:
    """Lê texto; arquivo acima do limite volta com truncated=True."""
    _make_project(tmp_path)
    (tmp_path / "grande.txt").write_text("x" * 5000, encoding="utf-8")
    w = _ws(tmp_path, max_file_kb=1)  # 1 KB
    await w.set_root(str(tmp_path))
    fc = await w.read_file("main.py")
    assert "print('oi')" in fc.text and not fc.truncated
    big = await w.read_file("grande.txt")
    assert big.truncated and len(big.text) == 1024


async def test_read_rejects_binary(tmp_path: Path) -> None:
    """Arquivo binário (byte nulo) não é lido como texto."""
    _make_project(tmp_path)
    (tmp_path / "bin.dat").write_bytes(b"abc\x00def")
    w = _ws(tmp_path)
    await w.set_root(str(tmp_path))
    with pytest.raises(WorkspaceError):
        await w.read_file("bin.dat")


async def test_path_escape_is_blocked(tmp_path: Path) -> None:
    """Não é possível ler fora da raiz via '..'."""
    proj = tmp_path / "proj"
    proj.mkdir()
    _make_project(proj)
    (tmp_path / "segredo.txt").write_text("SENHA", encoding="utf-8")
    w = _ws(proj)
    await w.set_root(str(proj))
    with pytest.raises(WorkspaceError):
        await w.read_file("../segredo.txt")


async def test_search_finds_text(tmp_path: Path) -> None:
    """A busca encontra o termo e reporta arquivo + linha."""
    _make_project(tmp_path)
    w = _ws(tmp_path)
    await w.set_root(str(tmp_path))
    hits = await w.search("soma")
    assert any(h.path == "sub/util.py" for h in hits)


# --- Serviço: montagem do contexto ------------------------------------------


async def test_build_context_respects_budget(tmp_path: Path) -> None:
    """build_context_blocks respeita o orçamento e nota o que foi cortado."""
    _make_project(tmp_path)
    (tmp_path / "a.txt").write_text("A" * 400, encoding="utf-8")
    (tmp_path / "b.txt").write_text("B" * 400, encoding="utf-8")
    provider = _ws(tmp_path)
    await provider.set_root(str(tmp_path))
    svc = WorkspaceService(provider, context_char_budget=300)
    blocks = await svc.build_context_blocks(["a.txt", "b.txt"])
    joined = "\n".join(blocks)
    assert "a.txt" in joined
    assert "orçamento" in joined.lower()  # avisou o corte


async def test_build_context_skips_unreadable(tmp_path: Path) -> None:
    """Arquivo inexistente vira nota, sem derrubar o resto."""
    _make_project(tmp_path)
    provider = _ws(tmp_path)
    await provider.set_root(str(tmp_path))
    svc = WorkspaceService(provider, context_char_budget=24000)
    blocks = await svc.build_context_blocks(["main.py", "nao_existe.py"])
    joined = "\n".join(blocks)
    assert "print('oi')" in joined
    assert "não incluído" in joined.lower()


# --- Roteamento do turno de código ------------------------------------------


async def test_coding_turn_uses_code_model_and_skips_rag() -> None:
    """Com context_blocks: usa o modelo de código e não busca na web."""
    llm = FakeLLMProvider(tokens=["resposta"])
    service = build_conversation_service(llm=llm)  # rag_enabled=True
    events = [
        e
        async for e in service.run(
            "como funciona?", context_blocks=["Arquivo do projeto: main.py\n```\nx\n```"]
        )
    ]
    assert not any(isinstance(e, SourcesGathered) for e in events)  # RAG pulado
    assert any(isinstance(e, TokenGenerated) for e in events)
    assert llm.models[-1] == "qwen2.5-coder:7b"  # modelo de código default
    # O bloco do arquivo entrou como mensagem de sistema.
    contents = [m.content for m in llm.calls[-1] if m.role == "system"]
    assert any("main.py" in c for c in contents)


# --- REST do workspace ------------------------------------------------------


def _app_with_workspace(tmp_path: Path):
    app = create_app()
    provider = LocalFsWorkspace(
        ignore_dirs=["node_modules", ".git"], max_file_kb=256, max_tree_entries=2000
    )
    app.state.workspace_service = WorkspaceService(provider, context_char_budget=24000)
    return app


def test_rest_workspace_flow(tmp_path: Path) -> None:
    """Fluxo REST: abrir pasta, listar árvore, ler arquivo e buscar."""
    _make_project(tmp_path)
    client = TestClient(_app_with_workspace(tmp_path))

    r = client.post("/api/workspace/root", json={"path": str(tmp_path)})
    assert r.status_code == 200 and r.json()["root"] == str(tmp_path.resolve())

    tree = client.get("/api/workspace/tree").json()
    assert any(e["path"] == "main.py" for e in tree)

    f = client.get("/api/workspace/file", params={"path": "sub/util.py"})
    assert f.status_code == 200 and "def soma" in f.json()["text"]

    hits = client.get("/api/workspace/search", params={"q": "soma"}).json()
    assert any(h["path"] == "sub/util.py" for h in hits)


def test_rest_file_escape_is_400(tmp_path: Path) -> None:
    """Ler fora da raiz via REST devolve 400."""
    proj = tmp_path / "proj"
    proj.mkdir()
    _make_project(proj)
    (tmp_path / "segredo.txt").write_text("x", encoding="utf-8")
    client = TestClient(_app_with_workspace(tmp_path))
    client.post("/api/workspace/root", json={"path": str(proj)})
    r = client.get("/api/workspace/file", params={"path": "../segredo.txt"})
    assert r.status_code == 400
