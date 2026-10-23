"""Offline checks: no MCP package download, daemon or wallet access."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from verus_agent.mcp_client import (
    MCPServerConnection, MCPServerName, _require_patched_node,
)


def version_process(version, returncode=0):
    process = MagicMock()
    process.returncode = returncode
    process.communicate = AsyncMock(return_value=(version, b""))
    process.wait = AsyncMock(return_value=returncode)
    return process


@pytest.mark.asyncio
@pytest.mark.parametrize("version", [b"v22.23.4\n", b"v22.24.0", b"v24.22.1", b"v26.12.1"])
async def test_patched_release_lines_are_accepted(version):
    env = {"PATH": "synthetic-runtime-path"}
    with patch("verus_agent.mcp_client.shutil.which", return_value="node") as which, patch(
        "verus_agent.mcp_client.asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=version_process(version)),
    ) as spawn:
        await _require_patched_node(env)
    which.assert_called_once_with("node", path=env["PATH"])
    assert spawn.call_args.args == ("node", "--version")
    assert spawn.call_args.kwargs["env"] == env


@pytest.mark.asyncio
@pytest.mark.parametrize("version", [
    b"v18.20.8", b"v20.19.5", b"v22.23.3", b"v24.22.0", b"v26.12.0",
    b"v25.0.0", b"v27.0.0", b"v24.22.1-rc.1", b"unexpected output",
])
async def test_unpatched_or_unverified_runtime_blocks_mcp_start(version):
    connection = MCPServerConnection(MCPServerName.CHAIN, env={"PATH": "synthetic-runtime-path"})
    with patch("verus_agent.mcp_client.shutil.which", side_effect=lambda name, **kwargs: name), patch(
        "verus_agent.mcp_client.asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=version_process(version)),
    ) as spawn:
        with pytest.raises(RuntimeError, match="MCP requires Node.js"):
            await connection.start()
    # Only the version probe ran; npx never downloaded or launched a server.
    assert spawn.call_count == 1
    assert spawn.call_args.args == ("node", "--version")
    assert connection._process is None


@pytest.mark.asyncio
async def test_missing_node_blocks_before_process_creation():
    with patch("verus_agent.mcp_client.shutil.which", return_value=None), patch(
        "verus_agent.mcp_client.asyncio.create_subprocess_exec", new=AsyncMock(),
    ) as spawn:
        with pytest.raises(RuntimeError, match="MCP requires Node.js"):
            await _require_patched_node({"PATH": "synthetic-runtime-path"})
    spawn.assert_not_called()


@pytest.mark.asyncio
async def test_failed_version_probe_is_rejected():
    with patch("verus_agent.mcp_client.shutil.which", return_value="node"), patch(
        "verus_agent.mcp_client.asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=version_process(b"v24.22.1", returncode=1)),
    ):
        with pytest.raises(RuntimeError, match="MCP requires Node.js"):
            await _require_patched_node({"PATH": "synthetic-runtime-path"})


@pytest.mark.asyncio
async def test_version_probe_timeout_cleans_up_process():
    process = version_process(b"", returncode=None)
    process.communicate.side_effect = asyncio.TimeoutError
    with patch("verus_agent.mcp_client.shutil.which", return_value="node"), patch(
        "verus_agent.mcp_client.asyncio.create_subprocess_exec", new=AsyncMock(return_value=process),
    ):
        with pytest.raises(RuntimeError, match="timed out"):
            await _require_patched_node({"PATH": "synthetic-runtime-path"})
    process.kill.assert_called_once()
    process.wait.assert_awaited_once()
