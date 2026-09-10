"""Testes da Fase 10 (workspace de código): adapter de sistema de arquivos (com
segurança de caminho, leitura e escrita confinada com backup), serviço de
contexto, roteamento do turno de código e REST do workspace."""

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


# --- Adapter: escrita (confinada, com backup) -------------------------------


def _wsw(root: Path, backups: Path, **over) -> LocalFsWorkspace:
    """Workspace com escrita habilitada e diretório de backup dedicado."""
    return _ws(root, write_enabled=True, backup_dir=str(backups), **over)


async def test_write_creates_new_file(tmp_path: Path) -> None:
    """Escrever um arquivo inexistente cria (sem backup)."""
    _make_project(tmp_path)
    w = _wsw(tmp_path, tmp_path.parent / "bak")
    await w.set_root(str(tmp_path))
    res = await w.write_file("novo/ola.py", "print('novo')\n")
    assert res.created and res.backup_path is None
    assert (tmp_path / "novo" / "ola.py").read_text(encoding="utf-8") == "print('novo')\n"


async def test_write_overwrites_and_backs_up(tmp_path: Path) -> None:
    """Sobrescrever guarda o conteúdo anterior no backup."""
    _make_project(tmp_path)
    backups = tmp_path.parent / "bak"
    w = _wsw(tmp_path, backups)
    await w.set_root(str(tmp_path))
    res = await w.write_file("main.py", "print('novo conteudo')\n")
    assert not res.created and res.backup_path is not None
    # O arquivo tem o novo conteúdo; o backup, o antigo.
    assert (tmp_path / "main.py").read_text(encoding="utf-8") == "print('novo conteudo')\n"
    assert Path(res.backup_path).read_text(encoding="utf-8") == "print('oi')\n"


async def test_write_disabled_raises(tmp_path: Path) -> None:
    """Com a escrita desativada, write_file falha."""
    _make_project(tmp_path)
    w = _ws(tmp_path)  # write_enabled=False por padrão
    await w.set_root(str(tmp_path))
    with pytest.raises(WorkspaceError):
        await w.write_file("main.py", "x")


async def test_write_escape_is_blocked(tmp_path: Path) -> None:
    """Não é possível escrever fora da raiz via '..'."""
    proj = tmp_path / "proj"
    proj.mkdir()
    _make_project(proj)
    w = _wsw(proj, tmp_path / "bak")
    await w.set_root(str(proj))
    with pytest.raises(WorkspaceError):
        await w.write_file("../evil.txt", "hack")
    assert not (tmp_path / "evil.txt").exists()


async def test_write_refuses_ignored_dir(tmp_path: Path) -> None:
    """Escrever dentro de diretório ignorado (.git, node_modules) é recusado."""
    _make_project(tmp_path)
    w = _wsw(tmp_path, tmp_path.parent / "bak")
    await w.set_root(str(tmp_path))
    with pytest.raises(WorkspaceError):
        await w.write_file("node_modules/x.js", "// no")


async def test_write_refuses_binary_suffix(tmp_path: Path) -> None:
    """Sufixo não-texto (ex.: .png) não é editável como texto."""
    _make_project(tmp_path)
    w = _wsw(tmp_path, tmp_path.parent / "bak")
    await w.set_root(str(tmp_path))
    with pytest.raises(WorkspaceError):
        await w.write_file("img.png", "not really an image")


async def test_write_refuses_directory(tmp_path: Path) -> None:
    """Escrever sobre um caminho que é pasta é recusado."""
    _make_project(tmp_path)
    w = _wsw(tmp_path, tmp_path.parent / "bak")
    await w.set_root(str(tmp_path))
    with pytest.raises(WorkspaceError):
        await w.write_file("sub", "x")


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


def _app_with_workspace(tmp_path: Path, *, write_enabled: bool = False):
    app = create_app()
    provider = LocalFsWorkspace(
        ignore_dirs=["node_modules", ".git"],
        max_file_kb=256,
        max_tree_entries=2000,
        write_enabled=write_enabled,
        backup_dir=str(tmp_path.parent / "bak"),
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


def test_rest_write_flow(tmp_path: Path) -> None:
    """POST /workspace/file cria e depois sobrescreve (com backup)."""
    _make_project(tmp_path)
    client = TestClient(_app_with_workspace(tmp_path, write_enabled=True))
    client.post("/api/workspace/root", json={"path": str(tmp_path)})

    # Cria um arquivo novo.
    r = client.post("/api/workspace/file", json={"path": "novo.py", "text": "a = 1\n"})
    assert r.status_code == 200
    body = r.json()
    assert body["created"] is True and body["backup_path"] is None
    assert (tmp_path / "novo.py").read_text(encoding="utf-8") == "a = 1\n"

    # Sobrescreve um existente: created=False e backup presente.
    r2 = client.post("/api/workspace/file", json={"path": "main.py", "text": "b = 2\n"})
    assert r2.status_code == 200 and r2.json()["created"] is False
    assert r2.json()["backup_path"]


def test_rest_write_escape_is_400(tmp_path: Path) -> None:
    """Escrever fora da raiz via REST devolve 400 e não cria nada."""
    proj = tmp_path / "proj"
    proj.mkdir()
    _make_project(proj)
    client = TestClient(_app_with_workspace(tmp_path, write_enabled=True))
    client.post("/api/workspace/root", json={"path": str(proj)})
    r = client.post("/api/workspace/file", json={"path": "../evil.txt", "text": "x"})
    assert r.status_code == 400
    assert not (tmp_path / "evil.txt").exists()


def test_rest_write_disabled_is_400(tmp_path: Path) -> None:
    """Com a escrita desativada, o POST devolve 400."""
    _make_project(tmp_path)
    client = TestClient(_app_with_workspace(tmp_path, write_enabled=False))
    client.post("/api/workspace/root", json={"path": str(tmp_path)})
    r = client.post("/api/workspace/file", json={"path": "main.py", "text": "x"})
    assert r.status_code == 400
