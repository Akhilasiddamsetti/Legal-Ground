import pytest

import legal_ground.assistant.llm as llm_module
from legal_ground.assistant.llm import LLM, BedrockLLM, StubLLM


def test_stub_llm_invokes_responder_with_system_and_user():
    seen = {}

    def responder(system, user):
        seen["system"] = system
        seen["user"] = user
        return "stub answer"

    stub: LLM = StubLLM(responder)
    out = stub.complete("SYS", "USER")
    assert out == "stub answer"
    assert seen == {"system": "SYS", "user": "USER"}


def test_bedrock_llm_resolves_config_and_forwards_request(monkeypatch):
    calls = {}

    class FakeMessages:
        def create(self, **kwargs):
            calls["request"] = kwargs
            return type(
                "Resp",
                (),
                {"content": [type("Block", (), {"type": "text", "text": "bedrock answer"})()]},
            )()

    class FakeAnthropicBedrock:
        def __init__(self, aws_region=None, aws_profile=None):
            calls["client_init"] = {"aws_region": aws_region, "aws_profile": aws_profile}
            self.messages = FakeMessages()

    monkeypatch.setattr(llm_module, "AnthropicBedrock", FakeAnthropicBedrock, raising=False)
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    monkeypatch.setenv("AWS_PROFILE", "demo-profile")
    monkeypatch.setenv("BEDROCK_MODEL", "env-model")

    bedrock = BedrockLLM(max_tokens=321)
    out = bedrock.complete("SYS", "USER")

    assert out == "bedrock answer"
    assert calls["client_init"] == {"aws_region": "us-west-2", "aws_profile": "demo-profile"}
    assert calls["request"] == {
        "model": "env-model",
        "max_tokens": 321,
        "system": "SYS",
        "messages": [{"role": "user", "content": "USER"}],
    }


def test_bedrock_llm_requires_region(monkeypatch):
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    with pytest.raises(ValueError, match="AWS region is required for Bedrock"):
        BedrockLLM()
