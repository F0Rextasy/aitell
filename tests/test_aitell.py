"""Contract tests for aitell. Run: python -m unittest discover -s tests -v

Every test drives the real CLI against fixture text (or temp files) and
asserts observable exit codes, bands, and measured values -- never
internals. The confusion-matrix test recomputes precision/recall over the
committed labeled corpus and fails if overall accuracy drops below the
number published in README.md (16/16).
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "aitell")
AI_DIR = os.path.join(ROOT, "examples", "corpus", "ai")
HUMAN_DIR = os.path.join(ROOT, "examples", "corpus", "human")

PUBLISHED_ACCURACY = 1.00
PUBLISHED_CORRECT = 16
PUBLISHED_TOTAL = 16


def run_cli(*args):
    proc = subprocess.run([sys.executable, SCRIPT, *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=ROOT)
    return proc.returncode, proc.stdout, proc.stderr


def scan(*paths):
    code, out, _ = run_cli(*paths, "--format", "json", "--no-color")
    return code, json.loads(out)


def write_temp(text, suffix=".md"):
    handle = tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False,
                                         encoding="utf-8")
    handle.write(text)
    handle.close()
    return handle.name


class AitellCorpus(unittest.TestCase):
    def test_every_ai_sample_is_flagged_ai_tells(self):
        code, data = scan(AI_DIR)
        self.assertEqual(code, 1)  # default --fail-over ai-tells
        self.assertEqual(len(data["files"]), 8)
        for entry in data["files"]:
            self.assertEqual(entry["verdict"], "ai-tells", entry["file"])
            self.assertGreaterEqual(entry["score"], 8)

    def test_every_human_sample_is_clean(self):
        code, data = scan(HUMAN_DIR)
        self.assertEqual(code, 0)
        self.assertEqual(len(data["files"]), 8)
        for entry in data["files"]:
            self.assertEqual(entry["verdict"], "clean", entry["file"])
            self.assertEqual(entry["score"], 0)

    def test_confusion_matrix_matches_published_numbers(self):
        _, ai_data = scan(AI_DIR)
        _, human_data = scan(HUMAN_DIR)
        ai_files = {os.path.basename(f["file"]): f
                    for f in ai_data["files"]}
        human_files = {os.path.basename(f["file"]): f
                       for f in human_data["files"]}
        self.assertEqual(len(ai_files) + len(human_files), PUBLISHED_TOTAL)

        rule_ids = list(ai_data["files"][0]["hits"].keys())
        self.assertEqual(len(rule_ids), 11)
        for rid in rule_ids:
            tp = sum(1 for f in ai_files.values() if f["hits"][rid]["fired"])
            fp = sum(1 for f in human_files.values()
                     if f["hits"][rid]["fired"])
            fn = len(ai_files) - tp
            precision = tp / (tp + fp) if (tp + fp) else 1.0
            recall = tp / (tp + fn) if (tp + fn) else 1.0
            self.assertEqual((precision, recall), (1.0, 1.0), rid)

        correct = (sum(1 for f in ai_files.values()
                       if f["verdict"] == "ai-tells")
                   + sum(1 for f in human_files.values()
                         if f["verdict"] == "clean"))
        accuracy = correct / PUBLISHED_TOTAL
        self.assertEqual(correct, PUBLISHED_CORRECT)
        self.assertGreaterEqual(accuracy, PUBLISHED_ACCURACY)


class AitellRules(unittest.TestCase):
    def check_rule(self, text, rule, measured):
        path = write_temp(text)
        try:
            _, data = scan(path)
            hit = data["files"][0]["hits"][rule]
        finally:
            os.unlink(path)
        self.assertTrue(hit["fired"], rule)
        self.assertEqual(hit["measured"], measured)

    def test_delve(self):
        self.check_rule(
            "We need to delve deeper into the cache logic before Friday.\n",
            "delve", "1 occurrence(s)")

    def test_conclusion(self):
        self.check_rule(
            "In conclusion, the tests pass on this machine today.\n",
            "conclusion", "1 occurrence(s)")

    def test_moreover_opener(self):
        self.check_rule(
            "Moreover, the retry loop needs a backoff cap.\n",
            "moreover-opener",
            "1 paragraph(s) open with moreover/furthermore")

    def test_emdash_density(self):
        self.check_rule(
            "The cache \u2014 which nobody owns \u2014 expired at midnight.\n",
            "emdash-density", "25.00 per 100 words (2 in 8 words)")

    def test_triplet(self):
        self.check_rule(
            "It is fast, reliable, and secure for small, busy, and growing "
            "teams.\n",
            "triplet", "2 triplet(s)")

    def test_notjust(self):
        self.check_rule(
            "It's not just fast, it's correct.\n",
            "notjust", "1 occurrence(s)")

    def test_divein(self):
        self.check_rule(
            "Let's dive in and check the logs.\n",
            "divein", "1 occurrence(s)")

    def test_boldheaders(self):
        self.check_rule(
            "**First rule: capture each idea the moment it appears.**\n"
            "**Second rule: review the inbox before the day begins.**\n",
            "boldheaders", "2 fully-bold line(s)")

    def test_verb_cluster(self):
        self.check_rule(
            "We unlock caches, harness retries, and leverage flags daily.\n",
            "verb-cluster", "3 occurrence(s)")

    def test_emoji_bullets(self):
        self.check_rule(
            "- \U0001F680 Ship it\n- \u2705 Test it\n- write the notes\n",
            "emoji-bullets", "2/3 bullets carry emoji (67%)")

    def test_sentence_uniformity(self):
        self.check_rule(
            "The cat sat. The dog ran. The bird flew. "
            "The fish swam. The cow stood. The pig slept.\n",
            "sentence-uniformity", "stdev 0.00 words over 6 sentences")


class AitellBehavior(unittest.TestCase):
    def test_verdict_bands_follow_score_floors(self):
        single = write_temp("We need to delve deeper into the cache.\n")
        double = write_temp("Let's dive in. We need to delve deeper.\n")
        try:
            _, one = scan(single)
            _, two = scan(double)
        finally:
            os.unlink(single)
            os.unlink(double)
        self.assertEqual(one["files"][0]["verdict"], "likely-human")  # 3
        self.assertEqual(two["files"][0]["verdict"], "likely-ai")  # 3 + 3

    def test_fail_over_gate_for_ci(self):
        code, _, _ = run_cli(HUMAN_DIR, "--fail-over", "likely-human",
                             "--no-color")
        self.assertEqual(code, 0)  # all human samples score 0: clean
        code, _, _ = run_cli(AI_DIR, "--fail-over", "likely-ai",
                             "--no-color")
        self.assertEqual(code, 1)

    def test_code_blocks_are_not_prose(self):
        path = write_temp("```\nLet's dive in and delve into unlock harness.\n"
                          "In conclusion moreover furthermore.\n```\n")
        try:
            code, data = scan(path)
        finally:
            os.unlink(path)
        self.assertEqual(code, 0)
        self.assertEqual(data["files"][0]["verdict"], "clean")

    def test_missing_path_is_usage_error(self):
        code, _, err = run_cli(os.path.join("nope", "missing.md"))
        self.assertEqual(code, 2)
        self.assertIn("cannot read", err)


if __name__ == "__main__":
    unittest.main()
