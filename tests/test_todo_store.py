"""todo_store 단위 테스트 (python -m unittest 로 실행)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from todo_store import TodoStore  # noqa: E402


class TodoStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "todos.json"
        self.store = TodoStore(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_빈_내용은_추가하지_않는다(self):
        self.assertIsNone(self.store.add("   ", "2026-10-08"))
        self.assertEqual(self.store.tasks, [])

    def test_추가하면_파일에_저장되고_다시_불러온다(self):
        self.store.add("보고서 쓰기", "2026-10-08")
        reloaded = TodoStore(self.path)
        self.assertEqual([t["text"] for t in reloaded.tasks], ["보고서 쓰기"])

    def test_미완료만_오늘로_이월된다(self):
        a = self.store.add("못 한 일", "2026-10-06")
        b = self.store.add("한 일", "2026-10-06")
        self.store.toggle(b["id"], "2026-10-06")

        moved = self.store.rollover("2026-10-08")

        self.assertEqual(moved, 1)
        self.assertEqual(self.store.get(a["id"])["date"], "2026-10-08")
        self.assertEqual(self.store.get(b["id"])["date"], "2026-10-06")
        self.assertEqual(self.store.carried_days(self.store.get(a["id"])), 2)

    def test_미래_할일은_이월되지_않는다(self):
        t = self.store.add("내일 할 일", "2026-10-09")
        self.assertEqual(self.store.rollover("2026-10-08"), 0)
        self.assertEqual(self.store.get(t["id"])["date"], "2026-10-09")

    def test_정렬은_미완료가_먼저(self):
        a = self.store.add("A", "2026-10-08")
        self.store.add("B", "2026-10-08")
        self.store.toggle(a["id"], "2026-10-08")
        self.assertEqual([t["text"] for t in self.store.tasks_for("2026-10-08")], ["B", "A"])

    def test_미루기와_수정과_삭제(self):
        t = self.store.add("운동", "2026-10-08")
        self.store.postpone(t["id"])
        self.assertEqual(self.store.get(t["id"])["date"], "2026-10-09")
        self.store.edit(t["id"], "운동 30분")
        self.assertEqual(self.store.get(t["id"])["text"], "운동 30분")
        self.store.delete(t["id"])
        self.assertEqual(self.store.tasks, [])

    def test_깨진_파일은_백업하고_빈_상태로_시작(self):
        self.path.write_text("{깨진 json", encoding="utf-8")
        store = TodoStore(self.path)
        self.assertEqual(store.tasks, [])
        self.assertTrue(self.path.with_suffix(".broken.json").exists())

    def test_저장_파일은_한글이_그대로_보인다(self):
        self.store.add("장보기", "2026-10-08")
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(raw["tasks"][0]["text"], "장보기")


if __name__ == "__main__":
    unittest.main()
