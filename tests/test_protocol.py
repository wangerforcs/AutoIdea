"""Tests for zotero_arxiv_daily.protocol: Paper idea generation helpers and affiliations."""

import pytest

from tests.canned_responses import make_sample_corpus, make_sample_paper, make_stub_openai_client
from zotero_arxiv_daily.protocol import _get_idea_mode_guidance, generate_daily_summary


@pytest.fixture()
def llm_params():
    return {
        "language": "English",
        "tldr_style": "short_summary",
        "generation_kwargs": {"model": "gpt-4o-mini", "max_tokens": 16384},
    }


@pytest.fixture()
def idea_config():
    return {
        "enabled": True,
        "mode": "balanced",
        "max_num": 3,
        "daily_summary_num": 3,
        "context_paper_num": 2,
        "show_per_paper": False,
        "focus": "Focus on workflow improvements and follow-up experiments.",
    }


# ---------------------------------------------------------------------------
# generate_tldr
# ---------------------------------------------------------------------------


def test_tldr_returns_response(llm_params):
    client = make_stub_openai_client()
    paper = make_sample_paper()
    result = paper.generate_tldr(client, llm_params)
    assert result == "Hello! How can I assist you today?"
    assert paper.tldr == result


def test_tldr_without_abstract_or_fulltext(llm_params):
    client = make_stub_openai_client()
    paper = make_sample_paper(abstract="", full_text=None)
    result = paper.generate_tldr(client, llm_params)
    assert "Failed to generate TLDR" in result


def test_tldr_falls_back_to_abstract_on_error(llm_params):
    paper = make_sample_paper()

    # Client whose create() raises
    from types import SimpleNamespace

    broken_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kw: (_ for _ in ()).throw(RuntimeError("API down")))
        )
    )
    result = paper.generate_tldr(broken_client, llm_params)
    assert result == paper.abstract


def test_tldr_truncates_long_prompt(llm_params):
    client = make_stub_openai_client()
    paper = make_sample_paper(full_text="word " * 10000)
    result = paper.generate_tldr(client, llm_params)
    assert result is not None


def test_tldr_accepts_detailed_style(llm_params):
    client = make_stub_openai_client()
    paper = make_sample_paper()
    llm_params["tldr_style"] = "detailed_summary"
    result = paper.generate_tldr(client, llm_params)
    assert result is not None


# ---------------------------------------------------------------------------
# idea outline / generate_ideas
# ---------------------------------------------------------------------------


def test_idea_mode_guidance_research():
    guidance = _get_idea_mode_guidance("research")
    assert "research-facing ideas" in guidance


def test_idea_mode_guidance_engineering():
    guidance = _get_idea_mode_guidance("engineering")
    assert "engineering-facing ideas" in guidance


def test_generate_idea_outline_returns_response(llm_params):
    client = make_stub_openai_client()
    paper = make_sample_paper(tldr="Useful summary")
    result = paper.generate_idea_outline(client, llm_params)
    assert result["problem"] == "Current workflows are slow."
    assert result["method"] == "The paper proposes a compact method."
    assert paper.idea_outline == result


def test_generate_ideas_returns_response(llm_params, idea_config):
    client = make_stub_openai_client()
    paper = make_sample_paper(tldr="Useful summary")
    paper.generate_idea_outline(client, llm_params)
    result = paper.generate_ideas(client, llm_params, idea_config, make_sample_corpus())
    assert len(result) == 3
    assert result[0] == "Try the method on your current benchmark."
    assert paper.ideas == result


def test_generate_ideas_without_abstract_or_fulltext(llm_params, idea_config):
    client = make_stub_openai_client()
    paper = make_sample_paper(abstract="", full_text=None)
    result = paper.generate_ideas(client, llm_params, idea_config, make_sample_corpus())
    assert result == []


def test_generate_ideas_error_returns_empty_list(llm_params, idea_config):
    from types import SimpleNamespace

    broken_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kw: (_ for _ in ()).throw(RuntimeError("boom")))
        )
    )
    paper = make_sample_paper()
    result = paper.generate_ideas(broken_client, llm_params, idea_config, make_sample_corpus())
    assert result == []
    assert paper.ideas == []


def test_generate_daily_summary_returns_response(llm_params, idea_config):
    client = make_stub_openai_client()
    paper = make_sample_paper(
        tldr="Useful summary",
        idea_outline={
            "problem": "Current workflows are slow.",
            "method": "The paper proposes a compact method.",
            "finding": "It improves efficiency.",
            "limitation": "It lacks broader validation.",
        },
        ideas=["Try the method on your current benchmark."],
    )
    summary = generate_daily_summary([paper], client, llm_params, idea_config)
    assert len(summary) == 3
    assert summary[0]["idea"] == "Test the strongest method on your current benchmark this week."
    assert "compact method" in summary[0]["innovation"]
    assert summary[0]["evidence"]


# ---------------------------------------------------------------------------
# generate_affiliations
# ---------------------------------------------------------------------------


def test_affiliations_returns_parsed_list(llm_params):
    client = make_stub_openai_client()
    paper = make_sample_paper()
    result = paper.generate_affiliations(client, llm_params)
    assert isinstance(result, list)
    assert "TsingHua University" in result
    assert "Peking University" in result


def test_affiliations_none_without_fulltext(llm_params):
    client = make_stub_openai_client()
    paper = make_sample_paper(full_text=None)
    result = paper.generate_affiliations(client, llm_params)
    assert result is None


def test_affiliations_deduplicates(llm_params):
    """The stub returns two distinct affiliations, so no dedup needed.
    But confirm the set() dedup in the code doesn't break anything.
    """
    client = make_stub_openai_client()
    paper = make_sample_paper()
    result = paper.generate_affiliations(client, llm_params)
    assert len(result) == len(set(result))


def test_affiliations_malformed_llm_output(llm_params):
    """LLM returns affiliations without JSON brackets. Should fall back gracefully."""
    from types import SimpleNamespace

    def create_no_brackets(**kwargs):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="TsingHua University, Peking University"),
                )
            ]
        )

    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=create_no_brackets)
        )
    )
    paper = make_sample_paper()
    result = paper.generate_affiliations(client, llm_params)
    # re.search for [...] will fail -> AttributeError -> caught -> returns None
    assert result is None


def test_affiliations_error_returns_none(llm_params):
    from types import SimpleNamespace

    broken_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kw: (_ for _ in ()).throw(RuntimeError("boom")))
        )
    )
    paper = make_sample_paper()
    result = paper.generate_affiliations(broken_client, llm_params)
    assert result is None
    assert paper.affiliations is None
