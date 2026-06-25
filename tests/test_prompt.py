from learning_curve.assistant.prompt import ABSTAIN_SENTINEL, build_system_prompt, build_user_prompt

EVIDENCE = [
    {
        "citation": {"display_text": "Exhibit 12 Inspection Report, Page 1"},
        "text": "Lot AX-447 failed inspection and should be held.",
    },
    {
        "citation": {"display_text": "Daniel Price Deposition, Page 13, Lines 1-17"},
        "text": "I glanced at Exhibit 12 before the truck left.",
    },
]


def test_system_prompt_states_the_contract():
    system_prompt = build_system_prompt()
    for clause in ["only", "cite", ABSTAIN_SENTINEL, "evidence"]:
        assert clause.lower() in system_prompt.lower()
    assert "instruction" in system_prompt.lower()


def test_user_prompt_numbers_and_delimits_evidence():
    user_prompt = build_user_prompt("What did the report say?", EVIDENCE)
    assert '<evidence id="1"' in user_prompt
    assert '<evidence id="2"' in user_prompt
    assert "Exhibit 12 Inspection Report, Page 1" in user_prompt
    assert "What did the report say?" in user_prompt
