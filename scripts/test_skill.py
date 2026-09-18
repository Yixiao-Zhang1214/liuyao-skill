#!/usr/bin/env python3
"""Observable invariants; synthetic reading acknowledgements stay in temp tests."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from hexagram import cast_counts, cast_tosses, catalog, resolve
from source_reader import SOURCE, fresh_page_text, pdf_library, prepare_reading, required_pages, verify_reading, verify_source

ROOT = Path(__file__).resolve().parents[1]


class CastingTests(unittest.TestCase):
    def test_project_example_and_two_moving_priority(self):
        result = cast_tosses("三正、一正二反、两正一反、两反一正、两正一反、三正")
        self.assertEqual(result["main"]["title"], "风火家人")
        self.assertEqual(result["changed"]["title"], "水山蹇")
        self.assertEqual(result["moving"], [1, 6])
        self.assertEqual(result["selection"]["primary"]["position"], 6)
        self.assertEqual(result["selection"]["secondary"][0]["position"], 1)

    def test_single_moving_examples(self):
        self.assertEqual(resolve("风火家人", [3])["changed"]["title"], "风雷益")
        self.assertEqual(resolve("風山漸", [2])["changed"]["title"], "巽为风")
        self.assertEqual(resolve("家人", changed="益")["moving"], [3])

    def test_yin_yang_not_surface_labels(self):
        counts = [3, 1, 2, 1, 2, 3]
        result = cast_counts(counts)
        self.assertEqual([x["state"] for x in result["lines_bottom_to_top"]],
                         ["老阳", "少阴", "少阳", "少阴", "少阳", "老阳"])
        inverse = cast_tosses("三正、一正二反、两正一反、两反一正、两正一反、三正", positive="yin")
        self.assertEqual(inverse["main"]["line_code_bottom_to_top"], "010100")
        self.assertEqual(result["main"]["line_code_bottom_to_top"], "101011")
        self.assertEqual(result["lines_bottom_to_top"][1]["drawing"], "━━　━━")
        self.assertEqual(result["lines_bottom_to_top"][2]["drawing"], "━━━━━━")

    def test_missing_information_is_not_zero_moving(self):
        result = resolve("家人")
        self.assertIsNone(result["moving"])
        self.assertIsNone(result["changed"])
        self.assertEqual(result["mode"], "guaci-only")
        self.assertEqual(resolve("家人", [])["moving"], [])

    def test_invalid_inputs(self):
        for counts in ([3]*5, [3]*7, [4]*6, [True]*6, [1.0]*6):
            with self.subTest(counts=counts), self.assertRaises(ValueError):
                cast_counts(counts)
        for moving in ([1, 1], [0], [7], [True], [1.0]):
            with self.subTest(moving=moving), self.assertRaises(ValueError):
                resolve("家人", moving)
        for text in ("三正，三正", "正反，三正，三正，三正，三正，三正", "零正三反，三正，三正，三正，三正，三正"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                cast_tosses(text)
        with self.assertRaises(ValueError):
            resolve("家人", [3], "蹇")
        with self.assertRaises(ValueError):
            resolve("不存在的卦")

    def test_all_4096_changes_and_selection(self):
        rows = catalog()["chapters"]
        self.assertEqual(len(rows), 64)
        self.assertEqual(len({x["line_code_bottom_to_top"] for x in rows}), 64)
        for row in rows:
            for mask in range(64):
                moving = [i+1 for i in range(6) if mask & (1 << i)]
                result = resolve(row["title"], moving)
                changed = result["changed"]
                back = resolve(changed["title"], moving)
                self.assertEqual(back["changed"]["title"], row["title"])
                for i, (a, b) in enumerate(zip(row["line_code_bottom_to_top"], changed["line_code_bottom_to_top"]), 1):
                    self.assertEqual(a != b, i in moving)
                choice = result["selection"]
                n = len(moving)
                if n in (1, 2):
                    self.assertEqual(choice["primary"]["position"], max(moving))
                    self.assertEqual(choice["primary"]["hexagram"], row["title"])
                    self.assertEqual(sorted(x["position"] for x in [choice["primary"]]+choice["secondary"]), moving)
                if n in (4, 5):
                    unchanged = [i for i in range(1, 7) if i not in moving]
                    self.assertEqual(choice["primary"]["position"], min(unchanged))
                    self.assertEqual(choice["primary"]["hexagram"], changed["title"])
                    self.assertEqual(sorted(x["position"] for x in [choice["primary"]]+choice["secondary"]), unchanged)
                if n == 3:
                    self.assertIsNone(choice["primary"])
                    self.assertEqual([x["hexagram"] for x in choice["paired"]], [row["title"], changed["title"]])
                if n == 6:
                    expected = {"乾为天": "用九", "坤为地": "用六"}.get(row["title"], "卦辞")
                    self.assertEqual(choice["primary"]["kind"], expected)
                if n == 0:
                    self.assertEqual(choice["primary"]["kind"], "卦辞")
                    self.assertEqual(choice["primary"]["hexagram"], row["title"])


class SourceTests(unittest.TestCase):
    def test_index_covers_the_entire_book(self):
        index = catalog()
        self.assertEqual(index["pdf_pages"], 146)
        self.assertEqual([x["pdf_page"] for x in index["page_audit"]], list(range(1, 147)))
        pages = [p for row in index["chapters"] for p in range(row["pdf_pages"][0], row["pdf_pages"][1]+1)]
        self.assertEqual(pages, list(range(11, 147)))
        self.assertEqual(required_pages(resolve("家人", [3])), list(range(1, 11))+[91, 92, 101, 102])
        self.assertEqual(required_pages(resolve("家人", [])), list(range(1, 11))+[91, 92])
        self.assertIn(95, required_pages(resolve("家人", [3]), ["蹇"]))

    def test_tampered_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            fake = Path(folder)/"source.pdf"
            fake.write_bytes(b"not the user's book")
            with self.assertRaises(ValueError):
                verify_source(fake)

    def test_actual_double_column_boundary(self):
        with pdf_library().open(SOURCE) as pdf:
            text, _ = fresh_page_text(pdf.pages[91], 92)
        left = text.split("## 左半栏候选")[1].split("## 右半栏候选")[0]
        right = text.split("## 右半栏候选")[1]
        self.assertIn("九三：家人嗃嗃", left)
        self.assertNotIn("象曰：", left)
        self.assertIn("象曰：家人嗃嗃", right)

    def test_known_ambiguity_must_be_reviewed_and_disclosed(self):
        with tempfile.TemporaryDirectory() as folder:
            packet = Path(folder)/"reading"
            prepare_reading(resolve("乾", []), packet)
            ack_path = packet/"reading-log.json"
            log = json.loads(ack_path.read_text())
            self.assertEqual([a["pdf_page"] for a in log["ambiguities"]], [12])
            # Synthetic test fixture, never a real reading acknowledgement.
            for page in log["pages"]:
                page.update(text_read=True, image_viewed=True, layout_verified=True)
            ack_path.write_text(json.dumps(log))
            with self.assertRaises(ValueError):
                verify_reading(packet)
            for item in log["ambiguities"]:
                item.update(status="preserved-unresolved", note="测试夹具：模拟保留非关键疑点", blocks_conclusion=False)
            ack_path.write_text(json.dumps(log))
            result = verify_reading(packet)
            self.assertEqual(result["unresolved_must_disclose"][0]["pdf_page"], 12)

    def test_actual_packet_and_coverage_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            packet = Path(folder)/"reading"
            prepare_reading(resolve("家人", [3]), packet, question="去哪工作")
            manifest = json.loads((packet/"manifest.json").read_text())
            expected = list(range(1, 11))+[91, 92, 101, 102]
            self.assertEqual(manifest["required_pdf_pages"], expected)
            self.assertEqual(len(manifest["pages"]), 14)
            for page in manifest["pages"]:
                self.assertTrue((packet/page["text_file"]).is_file())
                self.assertTrue((packet/page["image_file"]).is_file())
                from PIL import Image
                with Image.open(packet/page["image_file"]) as rendered:
                    self.assertGreater(rendered.width, 900)
                    self.assertGreater(rendered.height, 1200)
                    rendered.verify()
            self.assertIn("家人", (packet/"pages/pdf-091.md").read_text())
            with self.assertRaises(ValueError):
                verify_reading(packet)
            ack_path = packet/"reading-log.json"
            original = json.loads(ack_path.read_text())
            synthetic = copy.deepcopy(original)
            # Test fixture only. This is NOT a real assistant's reading record.
            for item in synthetic["pages"]:
                item.update(text_read=True, image_viewed=True, layout_verified=True)
            ack_path.write_text(json.dumps(synthetic))
            passed = verify_reading(packet)
            self.assertTrue(passed["coverage_complete"])
            self.assertFalse(passed["semantic_understanding_proven"])
            missing_page = copy.deepcopy(synthetic)
            missing_page["pages"].pop()
            ack_path.write_text(json.dumps(missing_page))
            with self.assertRaises(ValueError):
                verify_reading(packet)
            synthetic["additional_unknowns"] = [{"pdf_page": 92, "text": "测试疑字", "note": "关键辞句无法确认", "blocks_conclusion": True}]
            ack_path.write_text(json.dumps(synthetic))
            with self.assertRaises(ValueError):
                verify_reading(packet)
            ack_path.write_text(json.dumps(original))
            page_file = packet/manifest["pages"][-1]["text_file"]
            page_file.write_text("changed")
            with self.assertRaises(ValueError):
                verify_reading(packet)


if __name__ == "__main__":
    unittest.main(verbosity=2)
