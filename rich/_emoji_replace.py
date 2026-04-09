from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

if TYPE_CHECKING:
    from typing import Match

_ReStringMatch = "Match[str]"  # regex match object
_ReSubCallable = "Callable[[_ReStringMatch], str]"  # Callable invoked by re.sub
_EmojiSubMethod = "Callable[[_ReSubCallable, str], str]"  # Sub method of a compiled re

_EMOJI = None
_EMOJI_SUB = None
_VARIANTS = {"text": "\uFE0E", "emoji": "\uFE0F"}


def _get_emoji() -> Dict[str, str]:
    """Lazy-load the emoji codes dict on first use."""
    global _EMOJI
    if _EMOJI is None:
        from ._emoji_codes import EMOJI

        _EMOJI = EMOJI
    return _EMOJI


def __getattr__(name: str) -> Any:
    if name == "EMOJI":
        return _get_emoji()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _emoji_replace(
    text: str,
    default_variant: Optional[str] = None,
) -> str:
    """Replace emoji code in text."""
    global _EMOJI, _EMOJI_SUB
    if _EMOJI is None:
        from ._emoji_codes import EMOJI

        _EMOJI = EMOJI
    if _EMOJI_SUB is None:
        import re

        _EMOJI_SUB = re.compile(r"(:(\S*?)(?:(?:\-)(emoji|text))?:)").sub
    get_emoji = _EMOJI.__getitem__
    get_variant = _VARIANTS.get
    default_variant_code = _VARIANTS.get(default_variant, "") if default_variant else ""

    def do_replace(match: Match[str]) -> str:
        emoji_code, emoji_name, variant = match.groups()
        try:
            return get_emoji(emoji_name.lower()) + get_variant(
                variant, default_variant_code
            )
        except KeyError:
            return emoji_code

    return _EMOJI_SUB(do_replace, text)
