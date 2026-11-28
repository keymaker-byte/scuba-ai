"""tool-config.jsonc, read once for every tool: its top-level settings shared by all of them, and one
section per tool, named after the script.

The file is JSON with comments: a `//` outside a string runs to the end of the line, so each parameter
carries its own explanation beside it. A missing file gives every tool its built-in defaults; a file that
does not parse stops the run, since a typo would otherwise put every limit silently back to its default."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PATH = os.path.join(ROOT, "tool-config.jsonc")
_doc = None


def strip_comments(text):
    """The text with every `//` comment outside a string removed, line breaks kept."""
    out, i, n, in_str = [], 0, len(text), False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            out.append(c)
        elif text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
            continue
        else:
            out.append(c)
        i += 1
    return "".join(out)


def load():
    global _doc
    if _doc is None:
        try:
            with open(PATH) as f:
                text = f.read()
        except OSError:
            _doc = {}
            return _doc
        try:
            _doc = json.loads(strip_comments(text))
        except ValueError as e:
            sys.exit(f"tool-config.jsonc does not parse: {e}")
    return _doc


def get(section, key, default=None):
    """A tool's own setting: tool-config.jsonc's `section.key`, or the default."""
    return load().get(section, {}).get(key, default)


def user_agent_email():
    """The top-level contact address sent to services that ask automated clients for one; None unset."""
    email = load().get("user_agent_email")
    return None if not email or email.startswith("<") else email


def user_agent():
    email = user_agent_email()
    return f"dive-planning ({email})" if email else "dive-planning"
