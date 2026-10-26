#!/usr/bin/env python3
"""
opsq -- the one entry point to the tooling library.

    python cli.py list                       what exists, and what state it is in
    python cli.py verify                     does every tool still meet the standard
    python cli.py run <tool> [--provider]    run a tool over its input file
    python cli.py score <tool>               grade a run against the answer key
    python cli.py audit [--tail N]           what ran, by whom, with which prompt

`verify` is the one to put in CI. It is what stops the library decaying back
into a folder of loose prompts that used to work.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import audit, contract, prompt as prompt_lib, provider as provider_lib
from lib import registry, runner, score

ROOT = Path(__file__).resolve().parent
TICK, CROSS, DOT = "OK  ", "FAIL", " - "


def cmd_list(args):
    tools = registry.all_tools()
    if not tools:
        print("no tools found under tools/")
        return 0
    width = max(len(t.id) for t in tools)
    print(f"{'TOOL'.ljust(width)}  VER      STATUS   OWNER          NAME")
    for t in tools:
        owner = str(t.meta["owner"])[:13]
        print(f"{t.id.ljust(width)}  {t.version:<7}  {t.meta['status']:<7}  "
              f"{owner:<13}  {t.meta['name']}")
    print(f"\n{len(tools)} tool(s). Contract validator: {contract.backend()}.")
    return 0


def _verify_tool(t):
    problems = []
    for name in registry.REQUIRED_FILES:
        if not (t.path / name).exists():
            problems.append(f"missing {name}")
    if not (t.path / "fixtures").is_dir():
        problems.append("missing fixtures/")

    for key in registry.REQUIRED_META:
        if key not in t.meta:
            problems.append(f"TOOL.md front matter missing `{key}`")
    if t.meta.get("id") != t.path.name:
        problems.append(f"id `{t.meta.get('id')}` does not match folder `{t.path.name}`")
    if t.meta.get("status") not in registry.STATUSES:
        problems.append(f"status `{t.meta.get('status')}` not one of {registry.STATUSES}")
    if not t.system.strip():
        problems.append("prompt.md has no `system:` in its front matter")
    if (t.path / "RUNBOOK.md").exists():
        if not (t.path / "RUNBOOK.md").read_text(encoding="utf-8").strip():
            problems.append("RUNBOOK.md is empty -- nobody can run this without you")

    unsupported = contract.unsupported_keywords(t.schema)
    if unsupported and contract.backend() == "builtin-subset":
        problems.append(f"schema uses keywords the offline validator cannot check: {unsupported}")

    for required in ("needs_human_review", "review_reasons"):
        if required not in t.schema.get("properties", {}):
            problems.append(f"schema has no `{required}` -- every tool must be able to escalate")

    # A published escalation policy that the model is never shown is not a
    # policy. This check exists because that is exactly what happened: three
    # escalations went missing in evaluation run 3 because the rules lived only
    # in TOOL.md.
    if "## Escalation policy" not in t.doc:
        problems.append("TOOL.md has no `## Escalation policy` section")
    elif "escalation_policy" not in prompt_lib.placeholders(t.system + t.template):
        problems.append(
            "TOOL.md publishes an escalation policy but the prompt never "
            "includes `{{escalation_policy}}` -- the model would not see it")

    input_path = ROOT / str(t.meta.get("input", ""))
    placeholders = prompt_lib.placeholders(t.template) - registry.HARNESS_PLACEHOLDERS
    if input_path.is_file():
        header = set(runner.load_rows(input_path)[0].keys())
        missing = placeholders - header
        if missing:
            problems.append(f"prompt needs {sorted(missing)}, not columns in {input_path.name}")
        if t.meta["id_field"] not in header:
            problems.append(f"id_field `{t.meta['id_field']}` is not a column in {input_path.name}")
    elif t.meta.get("status") == "live":
        problems.append(f"input file not found: {t.meta.get('input')}")

    fixtures = sorted((t.path / "fixtures").glob("*.json")) if (t.path / "fixtures").is_dir() else []
    if t.meta.get("status") == "live" and not fixtures:
        problems.append("no fixtures -- a live tool needs an answer key")
    for fx in fixtures:
        try:
            payload = json.loads(fx.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"fixtures/{fx.name}: not valid JSON ({exc})")
            continue
        for err in contract.validate(payload, t.schema):
            problems.append(f"fixtures/{fx.name}: {err}")
    return problems


def cmd_verify(args):
    tools = registry.all_tools()
    total = 0
    for t in tools:
        problems = _verify_tool(t)
        total += len(problems)
        head = TICK if not problems else CROSS
        print(f"{head} {t.id} v{t.version} ({t.meta['status']}) "
              f"prompt:{t.prompt_sha} schema:{t.schema_sha}")
        for p in problems:
            print(f"     {DOT}{p}")
    print()
    if total:
        print(f"{total} problem(s) across {len(tools)} tool(s).")
        return 1
    print(f"{len(tools)} tool(s) meet the standard. Validator: {contract.backend()}.")
    return 0


def cmd_run(args):
    tool = registry.load(args.tool)
    rows = runner.load_rows(ROOT / (args.input or tool.meta["input"]))
    prov = provider_lib.get(args.provider, args.model)

    run_id, results = runner.run(tool, rows, prov, args.limit)
    out_dir = ROOT / "runs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "output.jsonl").open("w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps({"input_id": r.input_id, **r.payload}, ensure_ascii=False) + "\n")

    flagged = [r for r in results if r.needs_review]
    print(f"\n{tool.meta['name']}  v{tool.version}  prompt:{tool.prompt_sha}  provider:{prov.name}")
    print(f"run {run_id}\n")
    for r in results:
        mark = "REVIEW" if r.needs_review else "  auto"
        summary = str(r.payload.get("summary", ""))[:56]
        print(f"  {mark}  {r.input_id:<12} {summary}")
        for reason in r.reasons:
            print(f"          {DOT}{reason}")

    cleared = len(results) - len(flagged)
    print(f"\n{len(results)} processed, {len(flagged)} routed to a human, {cleared} cleared automatically.")
    print(f"output: runs/{run_id}/output.jsonl    audit: runs/audit.jsonl")
    if args.provider == "replay":
        print("\nnote: replay serves the committed reference outputs -- it proves the harness,")
        print("      not the model. Use --provider claude, then `score`, to measure the model.")
    return 0


def cmd_score(args):
    tool = registry.load(args.tool)
    if args.run:
        run_dir = ROOT / "runs" / args.run
    else:
        # The most recent run of *this* tool, not the most recent run. Grading
        # one tool's output against another tool's answer key produces confident
        # nonsense, which is the worst kind.
        mine = {e["run_id"] for e in audit.read() if e.get("tool") == tool.id}
        candidates = sorted(p for p in (ROOT / "runs").glob("*/output.jsonl")
                            if p.parent.name in mine)
        if not candidates:
            print(f"no runs of {tool.id} found -- run it first")
            return 1
        run_dir = candidates[-1].parent

    lines = (run_dir / "output.jsonl").read_text(encoding="utf-8").splitlines()
    rows = [json.loads(l) for l in lines if l.strip()]
    results = [
        runner.Result(
            input_id=r["input_id"],
            payload=r,
            needs_review=bool(r.get("needs_human_review")),
            reasons=r.get("review_reasons", []),
        )
        for r in rows
    ]

    providers = {e.get("provider") for e in audit.read() if e.get("run_id") == run_dir.name}
    if providers == {"replay"}:
        print("\n  This run used --provider replay, which serves the answer key itself.")
        print("  Scoring it against the answer key measures nothing. The numbers below")
        print("  will be 100% and they mean only that the harness moved the data intact.")
        print("  Re-run with --provider claude to get a score that says something.")

    report = score.grade(tool, results)
    print(f"\n{tool.meta['name']} -- run {run_dir.name}")
    line = f"scored {report['scored']} against the answer key"
    if report["skipped_no_reference"]:
        line += f", {report['skipped_no_reference']} had no reference"
    print(line)

    print("\nfield accuracy")
    for f, pct in report["fields"].items():
        shown = "n/a" if pct is None else f"{pct}%"
        print(f"  {f:<28} {shown}")

    rv = report["review"]
    print("\nhuman review queue")
    print(f"  caught {rv['caught']}   missed {rv['missed']}   over-flagged {rv['over_flagged']}")
    print(f"  recall    {rv['recall_pct']}%  <- decides whether this is safe to use")
    print(f"  precision {rv['precision_pct']}%  <- decides whether anyone will tolerate it")

    if report["mismatches"]:
        print("\nmismatches")
        for input_id, f, want, got in report["mismatches"][:20]:
            print(f"  {input_id:<12} {f:<24} expected {want!r}, got {got!r}")
    print()
    return 0


def cmd_doctor(args):
    """Self-diagnosis, so 'it doesn't work' has an answer that does not need
    whoever built it. Never prints the credential, only its shape."""
    import os
    import platform

    ok = True

    def row(label, good, detail=""):
        nonlocal ok
        ok = ok and good
        print(f"{TICK if good else CROSS} {label:<28} {detail}")

    print("\nenvironment")
    v = sys.version_info
    row("python", v >= (3, 10), f"{v.major}.{v.minor}.{v.micro} on {platform.system()}")

    try:
        import anthropic
        row("anthropic SDK", True, f"{anthropic.__version__} (needed for --provider claude)")
        sdk = True
    except ImportError:
        row("anthropic SDK", False, "not installed -- pip install anthropic")
        sdk = False

    print("\ncredentials (values are never printed)")
    key = os.environ.get("ANTHROPIC_API_KEY")
    token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
    if not key and not token:
        row("credential", False, "neither ANTHROPIC_API_KEY nor ANTHROPIC_AUTH_TOKEN is set")
        print("     - offline mode still works: python cli.py run <tool>")
    else:
        name = "ANTHROPIC_API_KEY" if key else "ANTHROPIC_AUTH_TOKEN"
        value = key or token
        row("credential", True, f"{name} is set, {len(value)} chars")
        stripped = value.strip().strip('"').strip("'")
        if stripped != value:
            row("  no stray whitespace/quotes", False,
                "the value has quotes or whitespace around it -- re-set it without them")
        if key and not stripped.startswith("sk-ant-"):
            row("  looks like an API key", False,
                f"starts {stripped[:7]!r}, expected 'sk-ant-'")
        if "\n" in value or "\r" in value:
            row("  single line", False, "the value contains a line break -- it was pasted wrapped")

    base = os.environ.get("ANTHROPIC_BASE_URL")
    if base:
        from urllib.parse import urlparse
        host = urlparse(base).hostname
        row("base URL", host == "api.anthropic.com", f"{host} (from ANTHROPIC_BASE_URL)")

    print("\nlibrary")
    row("contract validator", True, contract.backend())
    try:
        tools = registry.all_tools()
        broken = sum(1 for t in tools if _verify_tool(t))
        row("tools", not broken,
            f"{len(tools)} found, {len(tools) - broken} meeting the standard")
    except Exception as exc:
        row("tools", False, f"{type(exc).__name__}: {exc}")

    if sdk and (key or token):
        print("\nready for: python cli.py run <tool> --provider claude")
    else:
        print("\nready for offline runs only: python cli.py run <tool>")
    print()
    return 0 if ok else 1


def cmd_audit(args):
    rows = audit.read(args.tail)
    if not rows:
        print("no runs recorded yet")
        return 0
    for r in rows:
        flag = "REVIEW" if r.get("needs_human_review") else "  auto"
        red = ",".join(f"{k}:{v}" for k, v in (r.get("redactions") or {}).items()) or "none"
        print(f"{r['ts']}  {flag}  {r['tool']}@{r['tool_version']}  prompt:{r['prompt_sha']}  "
              f"{r['provider']}  in:{r['input_sha']}  redacted[{red}]  by:{r['operator']}")
    print(f"\n{len(rows)} entr(ies) from runs/audit.jsonl")
    return 0


def main():
    # A Windows console on a legacy code page cannot print "£" and the run would
    # die halfway through the table. Print what it can and substitute the rest.
    sys.stdout.reconfigure(errors="replace")
    p = argparse.ArgumentParser(
        prog="opsq",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="show the tool library").set_defaults(fn=cmd_list)
    sub.add_parser("doctor", help="diagnose the setup before blaming the tool").set_defaults(fn=cmd_doctor)
    sub.add_parser("verify", help="check every tool meets the standard").set_defaults(fn=cmd_verify)

    r = sub.add_parser("run", help="run a tool")
    r.add_argument("tool")
    r.add_argument("--input", help="override the input file declared in TOOL.md")
    r.add_argument("--provider", default="replay", choices=["replay", "claude"])
    r.add_argument("--model", help="override the model declared in TOOL.md")
    r.add_argument("--limit", type=int)
    r.set_defaults(fn=cmd_run)

    s = sub.add_parser("score", help="grade a run against the answer key")
    s.add_argument("tool")
    s.add_argument("--run", help="run id (default: most recent)")
    s.set_defaults(fn=cmd_score)

    a = sub.add_parser("audit", help="show the run log")
    a.add_argument("--tail", type=int, default=20)
    a.set_defaults(fn=cmd_audit)

    args = p.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
