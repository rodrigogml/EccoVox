from eccovox.core.normalization import normalize_transcript


def test_normalizeTranscript_shouldApplyOnlyExplicitAliasesAndContextCasing() -> None:
    result = normalize_transcript(
        "  Faça o becapi e consulte o tudo isso.  ",
        context_terms=("backup", "Todoist"),
        aliases=(("becapi", "backup"), ("tudo isso", "Todoist")),
    )

    assert result.text == "Faça o backup e consulte o Todoist."
    assert [change.reason for change in result.changes] == ["explicit_alias", "explicit_alias"]


def test_normalizeTranscript_shouldNotGuessUnknownPhoneticReplacement() -> None:
    result = normalize_transcript("Faça o becapi.", context_terms=("backup",))

    assert result.text == "Faça o becapi."
    assert result.changes == ()


def test_normalizeTranscript_shouldRestoreExactContextTermCasing() -> None:
    result = normalize_transcript("Abra o todoist.", context_terms=("Todoist",))

    assert result.text == "Abra o Todoist."
    assert result.changes[0].reason == "context_casing"
