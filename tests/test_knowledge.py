"""Offline knowledge retrieval and dispatch: no daemon, wallet or live service."""

from dataclasses import replace

import pytest

from verus_agent.agent import VerusBlockchainAgent
from verus_agent.config import VerusConfig
from verus_agent.knowledge import KNOWLEDGE_TOPICS, get_knowledge
from verus_agent.mobile import VerusMobileHelper


@pytest.mark.parametrize("topic", KNOWLEDGE_TOPICS)
def test_bundled_topics_are_readable(topic):
    result = get_knowledge(topic)
    assert result["content"].startswith("# ")
    assert "https://" in result["content"] or topic == "index"


@pytest.mark.parametrize("topic", ["../LOCAL_OPERATOR.md", "mobile/../../config.py", "https://example.invalid", "", None])
def test_reader_rejects_paths_urls_and_unknown_topics(topic):
    with pytest.raises(ValueError, match="Unknown knowledge topic"):
        get_knowledge(topic)


def test_release_channels_are_distinct_and_links_use_current_release():
    helper = VerusMobileHelper()
    release = helper.get_mobile_capabilities()["release"]
    assert release["current"] == release["android_apk"] == "v1.1.1"
    assert release["store_current"] == "v1.1.0-21"
    assert release["android_store_version"] == "1.1.0-21"
    assert release["ios_marketing_version"] == "1.1.0"
    assert release["ios_testflight"] == "v1.1.1"
    assert get_knowledge("mobile")["as_of"] == "2026-11-15"
    store = get_knowledge("mobile_store")
    assert store["as_of"] == "2026-10-15"
    assert store["content"].splitlines()[0] == "# Verus Mobile v1.1.0-21"
    assert helper.get_mobile_capabilities()["knowledge"]["path"] == get_knowledge("mobile")["path"]
    assert helper.generate_generic_request_link("synthetic-payload").data["wallet_release"] == release["current"]


@pytest.mark.asyncio
async def test_knowledge_dispatch_needs_no_wallet_or_daemon_initialization():
    agent = VerusBlockchainAgent(VerusConfig())
    agent._build_capability_handlers()
    result = await agent.process_task({
        "task_id": "synthetic-knowledge-read",
        "capability": "verus.knowledge.get",
        "params": {"topic": "mobile"},
    })
    assert result.success is True
    assert result.result["content"].splitlines()[0] == "# Verus Mobile v1.1.1"


@pytest.mark.asyncio
async def test_knowledge_dispatch_respects_disabled_activation():
    from verus_agent.runtime_policy import ActivationProfile, ActivationStage

    agent = VerusBlockchainAgent(VerusConfig())
    agent.activation_profile = replace(ActivationProfile.safe_default(), stage=ActivationStage.DISABLED)
    agent._build_capability_handlers()
    result = await agent.process_task({
        "task_id": "synthetic-disabled-read",
        "capability": "verus.knowledge.get",
        "params": {"topic": "index"},
    })
    assert result.success is False
