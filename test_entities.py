"""Tests for provider-aware entity extraction."""

from unittest.mock import patch

import entities


def test_extract_entities_uses_configured_provider():
    parsed = {
        "frontmatter": {"podcast": "Pod", "episode": "Episode"},
        "sections": {"Summary": "Summary"},
    }
    captured = {}

    def fake_generate(model, prompt, **kwargs):
        captured["model"] = model
        captured.update(kwargs)
        return '{"books": [], "tools": [], "people": [], "companies": [], "frameworks": []}'

    with patch("entities.metrics_mod.generate_text", fake_generate):
        result = entities.extract_entities(
            parsed, "gemma", provider="omlx", base_url="http://omlx/v1",
            api_key="secret",
        )

    assert result == {kind: [] for kind in entities.KINDS}
    assert captured["model"] == "gemma"
    assert captured["provider"] == "omlx"
    assert captured["base_url"] == "http://omlx/v1"
    assert captured["api_key"] == "secret"
