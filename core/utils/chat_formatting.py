import discord
from typing import Iterator, Sequence, Union

def box(text: str, lang: str = "") -> str:
    """Returns text enclosed in a code block."""
    return f"```{lang}\n{text}\n```"

def inline(text: str) -> str:
    """Returns text enclosed in inline code."""
    return f"`{text}`"

def pagify(
    text: str,
    delims: Sequence[str] = ("\n", " "),
    *,
    priority: bool = False,
    escape_mass_mentions: bool = True,
    shorten_by: int = 8,
    page_length: int = 2000,
) -> Iterator[str]:
    """Generates paginated pages of text to fit within Discord 2000 char limit.
    
    Simplified version of Red-DiscordBot's pagify.
    """
    in_text = text
    page_length -= shorten_by
    while len(in_text) > page_length:
        closest_delim = -1
        for delim in delims:
            idx = in_text.rfind(delim, 0, page_length)
            if idx != -1:
                closest_delim = idx
                break
        
        if closest_delim == -1:
            closest_delim = page_length
        
        to_send = in_text[:closest_delim]
        if escape_mass_mentions:
            to_send = to_send.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
        
        yield to_send
        in_text = in_text[closest_delim:]

    if in_text:
        if escape_mass_mentions:
            in_text = in_text.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
        yield in_text

def humanize_number(val: Union[int, float]) -> str:
    """Formats a number with commas (e.g. 1,000,000)."""
    if isinstance(val, (int, float)):
        return f"{val:,}"
    return str(val)

def humanize_list(items: Sequence[str]) -> str:
    """Formats a list of strings into a human-readable list (Like 'a, b, and c')."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return f"{', '.join(items[:-1])} và {items[-1]}"
