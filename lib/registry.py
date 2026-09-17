"""
Tool discovery.

A tool is a directory under tools/ containing exactly five things. The shape is
the standard -- `opsq verify` refuses anything that does not have all five, which
is what stops the library drifting back into a folder of loose prompts:

    TOOL.md              what it does, who owns it, when to escalate
    prompt.md            the versioned prompt
    schema.output.json   the output contract
    RUNBOOK.md           how a non-technical operator runs it
    fixtures/            reference outputs = the answer key
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import frontmatter, prompt as prompt_lib

SYSTEM_MARKER = "## SYSTEM"
USER_MARKER = "## USER"

ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT / "tools"

REQUIRED_FILES = ["TOOL.md", "prompt.md", "schema.output.json", "RUNBOOK.md"]
# Placeholders the harness supplies rather than the input file. Keeping them in
# one named set is what lets `verify` tell "the prompt asks for a column that
# does not exist" apart from "the prompt asks for something we inject".
HARNESS_PLACEHOLDERS = {"escalation_policy"}
REQUIRED_META = ["id", "name", "version", "owner", "status", "id_field", "model", "effort"]
STATUSES = ("live", "pilot", "planned")


@dataclass
class Tool:
    path: Path
    meta: dict
    doc: str
    system: str
    template: str
    schema: dict

    @property
    def id(self) -> str:
        return self.meta["id"]

    @property
    def version(self) -> str:
        return str(self.meta["version"])

    @property
    def escalation_policy(self) -> str:
        """The `## Escalation policy` section of TOOL.md, verbatim.

        This is injected into the prompt at `{{escalation_policy}}` rather than
        restated there. A rule that lives only in the documentation is not a
        rule: the first three evaluation runs of `case-intake` were carried by a
        policy the model was never shown, and the moment the prompt stopped
        inviting it to infer one, three escalations disappeared.

        One text, read by the governance reviewer and by the model. They cannot
        drift because they are the same characters.
        """
        if "## Escalation policy" not in self.doc:
            return ""
        section = self.doc.split("## Escalation policy", 1)[1]
        return section.split("\n## ", 1)[0].strip()

    @property
    def prompt_sha(self) -> str:
        # The policy is part of the prompt the model receives, so it is part of
        # the version. Editing the TOOL.md table changes this hash, and the
        # audit trail cannot attribute new decisions to the old policy.
        return prompt_lib.sha(
            self.system + "\n---\n" + self.template + "\n---\n" + self.escalation_policy
        )

    @property
    def schema_sha(self) -> str:
        return prompt_lib.sha(json.dumps(self.schema, sort_keys=True))

    def field_list(self, key: str) -> list[str]:
        value = self.meta.get(key) or []
        return [value] if isinstance(value, str) else list(value)

    def fixture(self, input_id: str) -> Path:
        return self.path / "fixtures" / f"{input_id}.json"


def split_prompt(text: str) -> tuple[str, str]:
    """prompt.md holds both halves of the prompt, split by two headings:

        ## SYSTEM     standing instructions -- role, vocabulary, escalation policy
        ## USER       the per-case template, with {{placeholders}}

    One file rather than two, because a system prompt and the template it governs
    drift apart the moment you let them live separately -- and the version hash
    covers both, so a change to either is a new prompt version.
    """
    lines = text.splitlines()
    bounds = {}
    for i, line in enumerate(lines):
        if line.strip() == SYSTEM_MARKER:
            bounds["system"] = i
        elif line.strip() == USER_MARKER:
            bounds["user"] = i
    if "system" not in bounds or "user" not in bounds:
        raise ValueError("prompt.md must contain both `## SYSTEM` and `## USER` headings")
    if bounds["user"] < bounds["system"]:
        raise ValueError("prompt.md: `## SYSTEM` must come before `## USER`")
    system = "\n".join(lines[bounds["system"] + 1:bounds["user"]]).strip()
    user = "\n".join(lines[bounds["user"] + 1:]).strip()
    return system, user


def load(tool_id: str) -> Tool:
    path = TOOLS_DIR / tool_id
    if not path.is_dir():
        raise FileNotFoundError(f"no such tool: {tool_id}")
    meta, doc = frontmatter.split((path / "TOOL.md").read_text(encoding="utf-8"))
    system, template = split_prompt((path / "prompt.md").read_text(encoding="utf-8"))
    schema = json.loads((path / "schema.output.json").read_text(encoding="utf-8"))
    return Tool(
        path=path,
        meta=meta,
        doc=doc,
        system=system,
        template=template,
        schema=schema,
    )


def all_tools() -> list[Tool]:
    out = []
    for path in sorted(TOOLS_DIR.iterdir()):
        if path.is_dir() and (path / "TOOL.md").exists():
            out.append(load(path.name))
    return out
