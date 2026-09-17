#!/usr/bin/env python3
"""
Tests for the properties the library claims about itself.

Run:  python -m unittest discover -s tests -v

These are not tests of the model. They are tests of the promises made in
GOVERNANCE.md and CONTRIBUTING.md — that identifiers do not leave, that the
harness can only escalate, that the audit log is not a second copy of the case
data, and that the same input produces the same output. A promise in a markdown
file that nothing checks is a promise that quietly stops being true.

Stdlib only, and no model calls, so this runs in CI with no credentials.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import audit, contract, provider as provider_lib, registry, runner  # noqa: E402
from lib.redact import Redactor  # noqa: E402


class TestRedaction(unittest.TestCase):
    def test_direct_identifiers_do_not_survive(self):
        text = ("Peter Alderton, peter.alderton@example.co.uk, 07700 900412, "
                "NI QQ 12 34 56 C, SK4 3TG, born 04/11/1988.")
        r = Redactor(extra_names=["Peter Alderton"])
        out = r.scrub(text)
        for leak in ["Alderton", "@example.co.uk", "900412", "QQ 12 34 56 C", "SK4 3TG", "04/11/1988"]:
            self.assertNotIn(leak, out, f"{leak!r} survived redaction")

    def test_round_trip_is_lossless(self):
        text = "Contact Ivy Castellanos at ivy@example.org about SK4 3TG."
        r = Redactor(extra_names=["Ivy Castellanos"])
        self.assertEqual(r.restore(r.scrub(text)), text)

    def test_one_person_one_token(self):
        r = Redactor(extra_names=["Jane Fairweather"])
        out = r.scrub("Jane Fairweather rang. Jane was upset. Fairweather is on file.")
        self.assertEqual(out.count("[PERSON_1]"), 3)

    def test_two_people_stay_apart(self):
        r = Redactor(extra_names=["Jane Fairweather", "Jane Okonkwo"])
        out = r.scrub("Jane Fairweather met Jane Okonkwo.")
        self.assertIn("[PERSON_1]", out)
        self.assertIn("[PERSON_2]", out)

    def test_ambiguous_name_is_masked_not_guessed(self):
        r = Redactor(extra_names=["Jane Fairweather", "Jane Okonkwo"])
        out = r.scrub("Jane said the assessment was booked.")
        self.assertNotIn("Jane ", out)
        self.assertIn("[PERSON_?]", out)
        self.assertEqual(r.ambiguous_hits, 1)

    def test_word_boundaries_respected(self):
        r = Redactor(extra_names=["Jane Fairweather"])
        self.assertIn("Janet", r.scrub("Janet was not involved."))


class TestContracts(unittest.TestCase):
    def test_every_fixture_matches_its_schema(self):
        for tool in registry.all_tools():
            for fixture in sorted((tool.path / "fixtures").glob("*.json")):
                payload = json.loads(fixture.read_text(encoding="utf-8"))
                errors = contract.validate(payload, tool.schema)
                self.assertEqual(errors, [], f"{tool.id}/{fixture.name}: {errors}")

    def test_every_tool_can_escalate(self):
        for tool in registry.all_tools():
            props = tool.schema.get("properties", {})
            self.assertIn("needs_human_review", props, tool.id)
            self.assertIn("review_reasons", props, tool.id)

    def test_a_broken_payload_is_rejected(self):
        tool = registry.load("case-intake")
        payload = json.loads((tool.path / "fixtures" / "CASE-0001.json").read_text(encoding="utf-8"))
        payload["priority"] = "P9"
        self.assertTrue(contract.validate(payload, tool.schema))

    def test_extra_fields_are_rejected(self):
        tool = registry.load("case-intake")
        payload = json.loads((tool.path / "fixtures" / "CASE-0001.json").read_text(encoding="utf-8"))
        payload["decided_outcome"] = "approved"
        self.assertTrue(contract.validate(payload, tool.schema),
                        "a field nobody agreed to must not pass silently")


class TestApiSchema(unittest.TestCase):
    """Structured outputs accept a subset of JSON Schema. Sending a keyword it
    does not support is a 400 on every case in the run, which is an expensive
    way to find out. Caught here instead, for free."""

    def test_no_unsupported_keywords_reach_the_api(self):
        from lib.provider import ClaudeProvider

        def walk(node, path="$"):
            found = []
            if isinstance(node, dict):
                for key, value in node.items():
                    if key in ClaudeProvider.API_UNSUPPORTED:
                        found.append(f"{path}.{key}")
                    found += walk(value, f"{path}.{key}")
            elif isinstance(node, list):
                for i, value in enumerate(node):
                    found += walk(value, f"{path}[{i}]")
            return found

        for tool in registry.all_tools():
            sent = ClaudeProvider._api_schema(tool.schema)
            self.assertEqual(walk(sent), [], f"{tool.id}: would be rejected by the API")

    def test_the_load_bearing_parts_survive(self):
        from lib.provider import ClaudeProvider

        for tool in registry.all_tools():
            sent = ClaudeProvider._api_schema(tool.schema)
            self.assertIs(sent["additionalProperties"], False, tool.id)
            self.assertEqual(sorted(sent["required"]), sorted(tool.schema["required"]), tool.id)
            self.assertEqual(sorted(sent["properties"]), sorted(tool.schema["properties"]), tool.id)
            for name, prop in tool.schema["properties"].items():
                if "enum" in prop:
                    self.assertEqual(sent["properties"][name]["enum"], prop["enum"],
                                     f"{tool.id}.{name}: enums must reach the model")

    def test_the_on_disk_contract_is_not_weakened(self):
        """Stripping happens on the wire only. The local check still enforces
        every limit the API cannot."""
        from lib.provider import ClaudeProvider

        tool = registry.load("case-intake")
        ClaudeProvider._api_schema(tool.schema)
        payload = json.loads((tool.path / "fixtures" / "CASE-0001.json").read_text(encoding="utf-8"))
        payload["summary"] = "x" * 400
        self.assertTrue(contract.validate(payload, tool.schema),
                        "maxLength must still be enforced locally")


class TestEscalationPolicyReachesTheModel(unittest.TestCase):
    """A rule that lives only in the documentation is not a rule.

    Evaluation run 3 lost three escalations because `case-intake`'s policy was
    published in TOOL.md and never shown to the model. These tests exist so that
    cannot happen quietly again.
    """

    def test_every_tool_publishes_a_policy(self):
        for tool in registry.all_tools():
            self.assertTrue(tool.escalation_policy.strip(),
                            f"{tool.id}: TOOL.md has no escalation policy")

    def test_the_published_policy_is_what_the_model_is_given(self):
        from lib import prompt as prompt_lib

        for tool in registry.all_tools():
            rendered = prompt_lib.render(
                tool.system, {"escalation_policy": tool.escalation_policy}
            )
            self.assertIn(tool.escalation_policy, rendered,
                          f"{tool.id}: the policy is not in the system prompt verbatim")
            self.assertNotIn("{{", rendered, f"{tool.id}: unrendered placeholder left in")

    def test_editing_the_policy_changes_the_prompt_version(self):
        """Otherwise the audit trail would attribute decisions made under a new
        policy to the hash of the old one."""
        tool = registry.load("case-intake")
        before = tool.prompt_sha
        tool.doc = tool.doc.replace(
            "| content not in English |", "| content not in Welsh |"
        )
        self.assertNotEqual(tool.prompt_sha, before)


class TestEscalateOnly(unittest.TestCase):
    """The harness may raise a hand. Nothing may lower one."""

    def setUp(self):
        self.tool = registry.load("case-intake")
        self.rows = {r["case_id"]: r for r in runner.load_rows(ROOT / self.tool.meta["input"])}

    def test_schema_violation_forces_review(self):
        class BadProvider:
            name = "test"

            def complete(self, tool, input_id, system, user_prompt):
                return {"case_id": input_id, "case_type": "not_a_valid_type",
                        "priority": "P3", "client_ref_present": True,
                        "stated_deadline": None, "routing_queue": "intake_team",
                        "missing_information": [], "needs_human_review": False,
                        "review_reasons": [], "summary": "looks fine"}, \
                       {"provider": "test", "model": None, "latency_ms": 0,
                        "usage": None, "refused": False}

        result = runner.run_one(self.tool, self.rows["CASE-0001"], BadProvider(), "test-run")
        self.assertTrue(result.needs_review, "invalid output must never clear")
        self.assertIn("schema_violation", result.reasons)

    def test_refusal_forces_review(self):
        class RefusingProvider:
            name = "test"

            def complete(self, tool, input_id, system, user_prompt):
                return {}, {"provider": "test", "model": None, "latency_ms": 0,
                            "usage": None, "refused": True}

        result = runner.run_one(self.tool, self.rows["CASE-0001"], RefusingProvider(), "test-run")
        self.assertTrue(result.needs_review)
        self.assertIn("model_refusal", result.reasons)

    def test_provider_error_forces_review(self):
        class ExplodingProvider:
            name = "test"

            def complete(self, tool, input_id, system, user_prompt):
                raise RuntimeError("connection reset")

        result = runner.run_one(self.tool, self.rows["CASE-0001"], ExplodingProvider(), "test-run")
        self.assertTrue(result.needs_review, "a failed run must not look like a clean one")
        self.assertIn("provider_error", result.reasons)

    def test_ambiguous_name_forces_review(self):
        result = runner.run_one(self.tool, self.rows["CASE-0008"],
                                provider_lib.get("replay"), "test-run")
        self.assertTrue(result.needs_review)
        self.assertIn("ambiguous_person_reference", result.reasons)


class TestAuditLog(unittest.TestCase):
    def test_log_holds_no_case_text(self):
        """GOVERNANCE.md says the audit log is not a second copy of the case
        data. This is that claim, enforced."""
        tool = registry.load("case-intake")
        rows = runner.load_rows(ROOT / tool.meta["input"])
        before = len(audit.read())
        runner.run(tool, rows, provider_lib.get("replay"))
        entries = audit.read()[before:]
        self.assertTrue(entries)

        bodies = [r["body"] for r in rows] + [r["claimant_name"] for r in rows]
        blob = json.dumps(entries, ensure_ascii=False)
        for value in bodies:
            for fragment in [value[:40], value[-40:]]:
                if len(fragment) > 12:
                    self.assertNotIn(fragment, blob,
                                     "case text leaked into the audit log")

    def test_log_identifies_the_prompt_that_decided(self):
        tool = registry.load("case-intake")
        rows = runner.load_rows(ROOT / tool.meta["input"])[:1]
        before = len(audit.read())
        runner.run(tool, rows, provider_lib.get("replay"))
        entry = audit.read()[before:][0]
        self.assertEqual(entry["prompt_sha"], tool.prompt_sha)
        self.assertEqual(entry["tool_version"], tool.version)
        self.assertIsNotNone(entry["operator"])


class TestRepeatability(unittest.TestCase):
    def test_same_input_same_output(self):
        tool = registry.load("case-intake")
        rows = runner.load_rows(ROOT / tool.meta["input"])
        prov = provider_lib.get("replay")
        _, first = runner.run(tool, rows, prov)
        _, second = runner.run(tool, rows, prov)
        self.assertEqual([r.payload for r in first], [r.payload for r in second])

    def test_prompt_hash_changes_when_the_prompt_changes(self):
        tool = registry.load("case-intake")
        original = tool.prompt_sha
        tool.template += "\nAlso mention the weather."
        self.assertNotEqual(tool.prompt_sha, original,
                            "an edited prompt must not keep its old version")

    def test_replay_refuses_inputs_it_has_no_answer_for(self):
        tool = registry.load("case-intake")
        with self.assertRaises(provider_lib.ProviderError):
            provider_lib.get("replay").complete(tool, "CASE-9999", "sys", "irrelevant")


if __name__ == "__main__":
    unittest.main(verbosity=2)
