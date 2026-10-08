"""할 일 데이터 저장소.

GUI와 분리된 순수 로직 모듈이라 단독으로 테스트할 수 있다.
데이터는 JSON 파일 하나에 저장된다.

할 일 항목 구조:
    id      : 고유 ID
    text    : 내용
    date    : 이 할 일이 배정된 날짜 (YYYY-MM-DD)
    origin  : 처음 등록된 날짜 (이월 일수 계산용)
    done    : 완료 여부
    done_at : 완료한 날짜 (미완료면 None)
"""

import datetime as dt
import json
import os
import uuid
from pathlib import Path

# 기본 저장 위치: 사용자 홈 폴더 아래 .desktop_todo/todos.json
DEFAULT_PATH = Path.home() / ".desktop_todo" / "todos.json"


def today_str(now=None):
    """오늘 날짜를 'YYYY-MM-DD' 문자열로 반환한다."""
    return (now or dt.date.today()).isoformat()


def shift_date(day, days):
    """'YYYY-MM-DD' 문자열 날짜를 days만큼 이동한다."""
    return (dt.date.fromisoformat(day) + dt.timedelta(days=days)).isoformat()


def days_between(start, end):
    """두 날짜 문자열 사이의 일수 (end - start)."""
    return (dt.date.fromisoformat(end) - dt.date.fromisoformat(start)).days


class TodoStore:
    def __init__(self, path=DEFAULT_PATH):
        self.path = Path(path)
        self.tasks = []
        self.settings = {}
        self.load()

    # ---------- 파일 입출력 ----------

    def load(self):
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            # 파일이 깨졌으면 지우지 않고 백업해 둔 뒤 빈 상태로 시작한다
            self.path.replace(self.path.with_suffix(".broken.json"))
            return
        self.tasks = data.get("tasks", [])
        self.settings = data.get("settings", {})

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps({"tasks": self.tasks, "settings": self.settings},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        # 임시 파일에 다 쓴 뒤 교체해서, 저장 도중 꺼져도 기존 데이터가 안 깨지게 한다
        os.replace(tmp, self.path)

    # ---------- 조회 ----------

    def get(self, task_id):
        for t in self.tasks:
            if t["id"] == task_id:
                return t
        raise KeyError(task_id)

    def tasks_for(self, day):
        """해당 날짜의 할 일 목록. 미완료가 위, 완료가 아래 (각각 등록 순서 유지)."""
        items = [t for t in self.tasks if t["date"] == day]
        return sorted(items, key=lambda t: t["done"])

    def day_counts(self):
        """날짜별 (전체 개수, 완료 개수). 달력에 할 일 표시용."""
        counts = {}
        for t in self.tasks:
            total, done = counts.get(t["date"], (0, 0))
            counts[t["date"]] = (total + 1, done + t["done"])
        return counts

    def carried_days(self, task):
        """처음 등록일로부터 며칠째 밀려 있는지 (0이면 이월 아님)."""
        return max(0, days_between(task["origin"], task["date"]))

    # ---------- 변경 ----------

    def add(self, text, day):
        text = text.strip()
        if not text:
            return None
        task = {
            "id": uuid.uuid4().hex,
            "text": text,
            "date": day,
            "origin": day,
            "done": False,
            "done_at": None,
        }
        self.tasks.append(task)
        self.save()
        return task

    def toggle(self, task_id, today):
        t = self.get(task_id)
        t["done"] = not t["done"]
        t["done_at"] = today if t["done"] else None
        self.save()
        return t

    def edit(self, task_id, text):
        text = text.strip()
        if text:
            self.get(task_id)["text"] = text
            self.save()

    def delete(self, task_id):
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        self.save()

    def postpone(self, task_id, days=1):
        """할 일을 지정한 일수만큼 뒤로 미룬다 (기본: 다음 날)."""
        t = self.get(task_id)
        t["date"] = shift_date(t["date"], days)
        self.save()

    def rollover(self, today):
        """오늘 이전 날짜에 남은 미완료 할 일을 모두 오늘로 옮긴다.

        옮긴 개수를 반환한다. 완료된 할 일은 그 날짜에 기록으로 남는다.
        """
        moved = 0
        for t in self.tasks:
            if not t["done"] and t["date"] < today:
                t["date"] = today
                moved += 1
        if moved:
            self.save()
        return moved
