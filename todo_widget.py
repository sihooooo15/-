"""바탕화면 투두 위젯.

실행: python todo_widget.py  (Windows에서는 start_todo.pyw 더블클릭 시 콘솔 창 없이 실행)

- 상단 바를 드래그해서 위치 이동, 오른쪽 아래 ◢ 를 드래그해서 크기 조절
- 엔터로 할 일 추가, ☐ 클릭으로 완료 체크
- 더블클릭으로 수정, 우클릭 메뉴로 내일로 미루기/삭제
- 날짜가 바뀌면 못 한 일은 자동으로 오늘로 이월
"""

import datetime as dt
import sys
import tkinter as tk
import tkinter.font as tkfont

from todo_store import TodoStore, days_between, shift_date, today_str

# ---------- 색상 테마 (어두운 반투명 위젯) ----------
BG = "#1e1f26"
PANEL = "#2a2c36"
HOVER = "#33364a"
FG = "#e8e8ef"
SUB = "#8c8fa3"
ACCENT = "#7aa2f7"
DONE = "#5f6275"
CARRY = "#e0af68"
DANGER = "#f7768e"

WEEKDAYS = "월화수목금토일"
IS_MAC = sys.platform == "darwin"
# 크기 조절 커서 이름이 운영체제마다 다르다
RESIZE_CURSOR = "size_nw_se" if sys.platform == "win32" else "bottom_right_corner"


def pick_font_family(root):
    """운영체제에 설치된 한글 폰트 중 먼저 찾은 것을 사용한다."""
    installed = set(tkfont.families(root))
    for name in ("Malgun Gothic", "맑은 고딕", "Apple SD Gothic Neo",
                 "Noto Sans CJK KR", "NanumGothic", "Noto Sans KR"):
        if name in installed:
            return name
    return "TkDefaultFont"


def format_day(day, today):
    """'10월 8일 (목)' 형식 + 오늘/어제/내일 표시."""
    d = dt.date.fromisoformat(day)
    label = f"{d.month}월 {d.day}일 ({WEEKDAYS[d.weekday()]})"
    diff = days_between(today, day)
    tag = {0: "오늘", -1: "어제", 1: "내일"}.get(diff)
    return label, tag


class TodoWidget:
    MIN_W, MIN_H = 260, 220

    def __init__(self, root, store):
        self.root = root
        self.store = store
        self.today = today_str()
        self.view_day = self.today
        self._drag = None
        self._editing = None  # 현재 수정 중인 할 일 id

        family = pick_font_family(root)
        self.f_title = tkfont.Font(family=family, size=13, weight="bold")
        self.f_body = tkfont.Font(family=family, size=10)
        self.f_done = tkfont.Font(family=family, size=10, overstrike=1)
        self.f_small = tkfont.Font(family=family, size=8)
        self.f_icon = tkfont.Font(family=family, size=12)

        self._setup_window()
        self._build_ui()

        moved = self.store.rollover(self.today)
        self.render()
        if moved:
            self.flash(f"못 한 일 {moved}개를 오늘로 넘겼어요")

        # 30초마다 날짜가 바뀌었는지 확인 (자정 넘어서도 켜 둔 경우 대비)
        self.root.after(30_000, self._tick)

    # ---------- 창 설정 ----------

    def _setup_window(self):
        s = self.store.settings
        r = self.root
        r.title("오늘 할 일")
        r.configure(bg=BG)
        w, h = s.get("w", 320), s.get("h", 440)
        if "x" in s and "y" in s:
            r.geometry(f"{w}x{h}+{s['x']}+{s['y']}")
        else:
            # 처음 실행 시 화면 오른쪽 위에 배치
            x = r.winfo_screenwidth() - w - 40
            r.geometry(f"{w}x{h}+{x}+60")
        r.minsize(self.MIN_W, self.MIN_H)
        # 맥은 테두리 없는 창에서 키보드 입력이 막히는 문제가 있어 일반 창으로 둔다
        if not IS_MAC:
            r.overrideredirect(True)
        r.attributes("-alpha", s.get("alpha", 0.93))
        r.attributes("-topmost", s.get("topmost", False))
        r.protocol("WM_DELETE_WINDOW", self.close)

    def _build_ui(self):
        r = self.root

        # 상단 바: 날짜 + 이동 버튼 + 고정/닫기 (드래그 영역 겸용)
        head = tk.Frame(r, bg=BG)
        head.pack(fill="x", padx=12, pady=(10, 4))
        self._make_draggable(head)

        self.title_lbl = tk.Label(head, bg=BG, fg=FG, font=self.f_title)
        self.title_lbl.pack(side="left")
        self._make_draggable(self.title_lbl)
        self.tag_lbl = tk.Label(head, bg=BG, fg=ACCENT, font=self.f_small)
        self.tag_lbl.pack(side="left", padx=(6, 0), pady=(4, 0))
        self._make_draggable(self.tag_lbl)

        self.close_btn = self._icon_btn(head, "✕", self.close, hover_fg=DANGER)
        self.close_btn.pack(side="right")
        self.pin_btn = self._icon_btn(head, "◆", self.toggle_topmost)
        self.pin_btn.pack(side="right", padx=(0, 6))
        self.next_btn = self._icon_btn(head, "▶", lambda: self.go(1))
        self.next_btn.pack(side="right", padx=(0, 6))
        self.today_btn = self._icon_btn(head, "오늘", self.go_today, font=self.f_small)
        self.prev_btn = self._icon_btn(head, "◀", lambda: self.go(-1))
        self.prev_btn.pack(side="right")

        # 입력창
        entry_box = tk.Frame(r, bg=PANEL)
        entry_box.pack(fill="x", padx=12, pady=(4, 8))
        self.entry = tk.Entry(entry_box, bg=PANEL, fg=FG, insertbackground=FG,
                              relief="flat", font=self.f_body, highlightthickness=0)
        self.entry.pack(side="left", fill="x", expand=True, padx=8, pady=7)
        self.entry.bind("<Return>", lambda e: self.add_task())
        self.entry.bind("<FocusIn>", lambda e: self._placeholder(False))
        self.entry.bind("<FocusOut>", lambda e: self._placeholder(True))
        self.add_btn = self._icon_btn(entry_box, "+", self.add_task, bg=PANEL, fg=ACCENT)
        self.add_btn.pack(side="right", padx=(0, 8))
        self._ph_active = False

        # 할 일 목록 (스크롤 영역)
        body = tk.Frame(r, bg=BG)
        body.pack(fill="both", expand=True, padx=(12, 6))
        self.canvas = tk.Canvas(body, bg=BG, highlightthickness=0, bd=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.list_frame = tk.Frame(self.canvas, bg=BG)
        self._list_win = self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.list_frame.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self._bind_wheel(self.canvas)

        # 하단: 진행률 + 알림 메시지 + 크기 조절 손잡이
        foot = tk.Frame(r, bg=BG)
        foot.pack(fill="x", padx=12, pady=(4, 6))
        self.progress = tk.Canvas(foot, height=4, bg=PANEL, highlightthickness=0, bd=0)
        self.progress.pack(fill="x", pady=(0, 4))
        self.stat_lbl = tk.Label(foot, bg=BG, fg=SUB, font=self.f_small)
        self.stat_lbl.pack(side="left")
        grip = tk.Label(foot, text="◢", bg=BG, fg=SUB, font=self.f_small, cursor=RESIZE_CURSOR)
        grip.pack(side="right")
        grip.bind("<ButtonPress-1>", self._resize_start)
        grip.bind("<B1-Motion>", self._resize_move)
        grip.bind("<ButtonRelease-1>", lambda e: self._save_geometry())
        self.msg_lbl = tk.Label(foot, bg=BG, fg=CARRY, font=self.f_small)
        self.msg_lbl.pack(side="right", padx=(0, 8))

        # 단축키: Ctrl+N 입력창 포커스
        r.bind("<Control-n>", lambda e: self.entry.focus_set())
        self.readonly = False

    def _icon_btn(self, parent, text, cmd, bg=BG, fg=SUB, hover_fg=FG, font=None):
        """평평한 아이콘 버튼 (Label로 만들어 테마 색을 그대로 쓴다)."""
        b = tk.Label(parent, text=text, bg=bg, fg=fg, font=font or self.f_icon, cursor="hand2")
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>", lambda e: b.configure(fg=hover_fg))
        b.bind("<Leave>", lambda e: b.configure(fg=b._base_fg))
        b._base_fg = fg
        return b

    # ---------- 렌더링 ----------

    def render(self):
        label, tag = format_day(self.view_day, self.today)
        self.title_lbl.configure(text=label)
        self.tag_lbl.configure(text=tag or "")

        # 오늘이 아닐 때만 '오늘' 바로가기 버튼 표시
        if self.view_day != self.today:
            self.today_btn.pack(side="right", padx=(0, 6), before=self.next_btn)
        else:
            self.today_btn.pack_forget()

        pinned = self.store.settings.get("topmost", False)
        self.pin_btn._base_fg = ACCENT if pinned else SUB
        self.pin_btn.configure(fg=self.pin_btn._base_fg)

        # 지난 날짜는 기록 보기 전용
        self.readonly = self.view_day < self.today
        self.entry.configure(state="normal", disabledbackground=PANEL)
        self.add_btn._base_fg = PANEL if self.readonly else ACCENT
        self.add_btn.configure(fg=self.add_btn._base_fg)
        self._placeholder(self.root.focus_get() is not self.entry)

        for child in self.list_frame.winfo_children():
            child.destroy()

        tasks = self.store.tasks_for(self.view_day)
        if not tasks:
            msg = "기록이 없어요" if self.readonly else "할 일을 입력하고 Enter ↵"
            tk.Label(self.list_frame, text=msg, bg=BG, fg=SUB, font=self.f_body
                     ).pack(anchor="w", pady=12, padx=4)
        for t in tasks:
            self._render_row(t)

        done = sum(t["done"] for t in tasks)
        self.stat_lbl.configure(text=f"{done} / {len(tasks)} 완료" if tasks else "")
        self._draw_progress(done / len(tasks) if tasks else 0)
        self.canvas.yview_moveto(0)

    def _render_row(self, t):
        row = tk.Frame(self.list_frame, bg=BG)
        row.pack(fill="x", pady=1)

        check = tk.Label(row, text="☑" if t["done"] else "☐", bg=BG,
                         fg=DONE if t["done"] else ACCENT, font=self.f_icon,
                         cursor="arrow" if self.readonly else "hand2")
        check.pack(side="left", anchor="n", padx=(2, 6))

        delete = tk.Label(row, text="✕", bg=BG, fg=BG, font=self.f_small, cursor="hand2")
        delete.pack(side="right", anchor="n", padx=(4, 4), pady=(4, 0))

        mid = tk.Frame(row, bg=BG)
        mid.pack(side="left", fill="x", expand=True)

        if self._editing == t["id"]:
            self._render_editor(mid, t)
        else:
            text = tk.Label(mid, text=t["text"], bg=BG, fg=DONE if t["done"] else FG,
                            font=self.f_done if t["done"] else self.f_body,
                            anchor="w", justify="left", wraplength=self._wrap_width())
            text.pack(fill="x", pady=(2, 0))
            carried = self.store.carried_days(t)
            if carried and not t["done"]:
                tk.Label(mid, text=f"↪ {carried}일째 밀린 일", bg=BG, fg=CARRY,
                         font=self.f_small, anchor="w").pack(fill="x")
            if not self.readonly:
                text.bind("<Double-Button-1>", lambda e, i=t["id"]: self.start_edit(i))

        widgets = [row, check, mid, delete] + list(mid.winfo_children())

        # 마우스를 올리면 줄 배경을 강조하고 삭제 버튼을 보여 준다
        def on_enter(_):
            for w in widgets:
                if w.winfo_exists() and not isinstance(w, tk.Entry):
                    w.configure(bg=HOVER)
            delete.configure(fg=SUB)

        def on_leave(_):
            for w in widgets:
                if w.winfo_exists() and not isinstance(w, tk.Entry):
                    w.configure(bg=BG)
            delete.configure(fg=BG)

        for w in widgets:
            w.bind("<Enter>", on_enter, add="+")
            w.bind("<Leave>", on_leave, add="+")
            self._bind_wheel(w)
            w.bind("<Button-3>", lambda e, i=t["id"]: self._context_menu(e, i))
            if IS_MAC:
                w.bind("<Button-2>", lambda e, i=t["id"]: self._context_menu(e, i))

        if not self.readonly:
            check.bind("<Button-1>", lambda e, i=t["id"]: self.toggle(i))
        delete.bind("<Button-1>", lambda e, i=t["id"]: self.delete(i))
        delete.bind("<Enter>", lambda e: delete.configure(fg=DANGER), add="+")

    def _render_editor(self, parent, t):
        """할 일 내용을 그 자리에서 수정하는 입력창."""
        ed = tk.Entry(parent, bg=PANEL, fg=FG, insertbackground=FG, relief="flat",
                      font=self.f_body, highlightthickness=1,
                      highlightcolor=ACCENT, highlightbackground=ACCENT)
        ed.insert(0, t["text"])
        ed.pack(fill="x", pady=(2, 0), ipady=2)
        ed.focus_set()
        ed.select_range(0, "end")
        ed.bind("<Return>", lambda e: self.finish_edit(t["id"], ed.get()))
        ed.bind("<Escape>", lambda e: self.finish_edit(t["id"], None))
        ed.bind("<FocusOut>", lambda e: self.finish_edit(t["id"], ed.get()))

    def _draw_progress(self, ratio):
        self.progress.delete("all")
        self.progress.update_idletasks()
        w = self.progress.winfo_width()
        if ratio > 0:
            self.progress.create_rectangle(0, 0, w * ratio, 4, fill=ACCENT, width=0)

    def _wrap_width(self):
        return max(120, self.canvas.winfo_width() - 60)

    def _placeholder(self, show):
        """입력창 안내 문구 표시/제거."""
        # 이전 안내 문구는 일단 지운다
        if self._ph_active:
            self.entry.configure(state="normal", fg=FG)
            self.entry.delete(0, "end")
            self._ph_active = False
        if self.readonly:
            self.entry.configure(state="normal")
            self.entry.insert(0, "지난 날짜는 기록만 볼 수 있어요")
            self.entry.configure(state="disabled", disabledforeground=SUB)
            self._ph_active = True
        elif show and not self.entry.get():
            day_word = "오늘" if self.view_day == self.today else format_day(self.view_day, self.today)[0]
            self.entry.insert(0, f"{day_word} 할 일 추가…")
            self.entry.configure(fg=SUB)
            self._ph_active = True

    def flash(self, msg, ms=5000):
        """하단에 잠깐 알림 메시지를 띄운다."""
        self.msg_lbl.configure(text=msg)
        self.root.after(ms, lambda: self.msg_lbl.configure(text=""))

    # ---------- 동작 ----------

    def add_task(self):
        if self.readonly or self._ph_active:
            return
        if self.store.add(self.entry.get(), self.view_day):
            self.entry.delete(0, "end")
            self.render()
            self.entry.focus_set()

    def toggle(self, task_id):
        self.store.toggle(task_id, self.today)
        self.render()

    def delete(self, task_id):
        self.store.delete(task_id)
        self.render()

    def postpone(self, task_id):
        t = self.store.get(task_id)
        # 지난 날짜에 걸려 있는 일이라도 최소한 내일로 보낸다
        target = max(shift_date(t["date"], 1), shift_date(self.today, 1))
        self.store.postpone(task_id, days_between(t["date"], target))
        self.render()
        self.flash("내일로 미뤘어요")

    def start_edit(self, task_id):
        self._editing = task_id
        self.render()

    def finish_edit(self, task_id, text):
        if self._editing != task_id:
            return  # 엔터 후 포커스아웃이 한 번 더 들어오는 경우 무시
        self._editing = None
        if text is not None:
            self.store.edit(task_id, text)
        self.root.after_idle(self.render)

    def _context_menu(self, event, task_id):
        t = self.store.get(task_id)
        m = tk.Menu(self.root, tearoff=0, bg=PANEL, fg=FG, activebackground=ACCENT,
                    activeforeground=BG, font=self.f_body, bd=0)
        if not self.readonly:
            m.add_command(label="완료 취소" if t["done"] else "완료",
                          command=lambda: self.toggle(task_id))
            m.add_command(label="수정", command=lambda: self.start_edit(task_id))
            if not t["done"]:
                m.add_command(label="내일로 미루기", command=lambda: self.postpone(task_id))
            m.add_separator()
        m.add_command(label="삭제", command=lambda: self.delete(task_id))
        m.tk_popup(event.x_root, event.y_root)

    def go(self, days):
        self._editing = None
        self.view_day = shift_date(self.view_day, days)
        self.render()

    def go_today(self):
        self._editing = None
        self.view_day = self.today
        self.render()

    def toggle_topmost(self):
        on = not self.store.settings.get("topmost", False)
        self.store.settings["topmost"] = on
        self.store.save()
        self.root.attributes("-topmost", on)
        self.render()
        self.flash("항상 위에 고정" if on else "고정 해제", 2000)

    def _tick(self):
        """날짜가 바뀌었으면 못 한 일을 이월하고 화면을 오늘로 갱신한다."""
        now = today_str()
        if now != self.today:
            was_today = self.view_day == self.today
            self.today = now
            moved = self.store.rollover(now)
            if was_today:
                self.view_day = now
            self.render()
            if moved:
                self.flash(f"못 한 일 {moved}개를 오늘로 넘겼어요")
        self.root.after(30_000, self._tick)

    # ---------- 창 이동 / 크기 조절 ----------

    def _make_draggable(self, w):
        w.bind("<ButtonPress-1>", self._drag_start)
        w.bind("<B1-Motion>", self._drag_move)
        w.bind("<ButtonRelease-1>", lambda e: self._save_geometry())

    def _drag_start(self, e):
        self._drag = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())

    def _drag_move(self, e):
        if self._drag:
            dx, dy = self._drag
            self.root.geometry(f"+{e.x_root - dx}+{e.y_root - dy}")

    def _resize_start(self, e):
        self._resize = (e.x_root, e.y_root, self.root.winfo_width(), self.root.winfo_height())

    def _resize_move(self, e):
        x0, y0, w0, h0 = self._resize
        w = max(self.MIN_W, w0 + e.x_root - x0)
        h = max(self.MIN_H, h0 + e.y_root - y0)
        self.root.geometry(f"{w}x{h}")

    def _on_canvas_resize(self, e):
        self.canvas.itemconfigure(self._list_win, width=e.width)
        # 폭이 바뀌면 줄바꿈 폭도 맞춰 준다
        for row in self.list_frame.winfo_children():
            for w in row.winfo_children():
                for sub in w.winfo_children():
                    if isinstance(sub, tk.Label) and int(str(sub.cget("wraplength")) or 0):
                        sub.configure(wraplength=self._wrap_width())
        self._draw_progress_later()

    def _draw_progress_later(self):
        tasks = self.store.tasks_for(self.view_day)
        done = sum(t["done"] for t in tasks)
        self.root.after_idle(lambda: self._draw_progress(done / len(tasks) if tasks else 0))

    def _save_geometry(self):
        self._drag = None
        s = self.store.settings
        s.update(x=self.root.winfo_x(), y=self.root.winfo_y(),
                 w=self.root.winfo_width(), h=self.root.winfo_height())
        self.store.save()

    # ---------- 마우스 휠 스크롤 ----------

    def _bind_wheel(self, w):
        w.bind("<MouseWheel>", self._on_wheel, add="+")   # Windows / macOS
        w.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-2, "units"), add="+")  # 리눅스
        w.bind("<Button-5>", lambda e: self.canvas.yview_scroll(2, "units"), add="+")

    def _on_wheel(self, e):
        # 내용이 화면보다 짧으면 스크롤하지 않는다
        if self.list_frame.winfo_height() <= self.canvas.winfo_height():
            return
        step = -e.delta if IS_MAC else -e.delta // 40
        self.canvas.yview_scroll(int(step), "units")

    def close(self):
        self._save_geometry()
        self.root.destroy()


def main():
    root = tk.Tk()
    TodoWidget(root, TodoStore())
    root.mainloop()


if __name__ == "__main__":
    main()
