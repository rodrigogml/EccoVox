"""Conservative transcript normalization driven by explicit context."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class NormalizationChange:
    """One explicit, auditable transcript normalization."""

    source: str
    target: str
    reason: str


@dataclass(frozen=True)
class NormalizedTranscript:
    """Normalized text and the changes applied to the raw transcript."""

    text: str
    changes: tuple[NormalizationChange, ...] = ()


def normalize_transcript(
    raw_text: str,
    context_terms: tuple[str, ...] = (),
    aliases: tuple[tuple[str, str], ...] = (),
) -> NormalizedTranscript:
    """Normalize whitespace, explicit aliases, and exact contextual term casing."""

    text = " ".join(raw_text.split())
    changes: list[NormalizationChange] = []
    text = _replace_explicit_aliases(text, aliases, changes)
    text = _restore_context_term_casing(text, context_terms, changes)
    return NormalizedTranscript(text=text, changes=tuple(changes))


def _replace_explicit_aliases(
    text: str,
    aliases: tuple[tuple[str, str], ...],
    changes: list[NormalizationChange],
) -> str:
    replacements = _unique_replacements(aliases)
    if not replacements:
        return text
    pattern = _replacement_pattern(tuple(replacements))

    def replace(match: re.Match[str]) -> str:
        source = match.group(0)
        target = replacements[source.casefold()]
        changes.append(NormalizationChange(source=source, target=target, reason="explicit_alias"))
        return target

    return pattern.sub(replace, text)


def _restore_context_term_casing(
    text: str,
    context_terms: tuple[str, ...],
    changes: list[NormalizationChange],
) -> str:
    replacements = _unique_replacements((term, term) for term in context_terms)
    if not replacements:
        return text
    pattern = _replacement_pattern(tuple(replacements))

    def replace(match: re.Match[str]) -> str:
        source = match.group(0)
        target = replacements[source.casefold()]
        if source != target:
            changes.append(NormalizationChange(source=source, target=target, reason="context_casing"))
        return target

    return pattern.sub(replace, text)


def _unique_replacements(items) -> dict[str, str]:
    replacements: dict[str, str] = {}
    for source, target in items:
        source_value = source.strip()
        target_value = target.strip()
        if source_value and target_value:
            replacements.setdefault(source_value.casefold(), target_value)
    return replacements


def _replacement_pattern(keys: tuple[str, ...]) -> re.Pattern[str]:
    alternatives = sorted(keys, key=len, reverse=True)
    expression = "|".join(re.escape(value) for value in alternatives)
    return re.compile(rf"(?<!\w)(?:{expression})(?!\w)", flags=re.IGNORECASE)
