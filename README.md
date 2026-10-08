# 바탕화면 투두 위젯

바탕화면 한쪽에 띄워 두고 쓰는 **오늘 할 일** 위젯입니다.
못 끝낸 일은 다음 날 자동으로 오늘로 넘어옵니다.

## 주요 기능

- **오늘 할 일 입력**: 입력창에 쓰고 `Enter`
- **완료 체크**: ☐ 클릭 → ☑ (완료한 일은 취소선 + 아래로 정렬)
- **자동 이월**: 날짜가 바뀌면 못 한 일이 오늘로 넘어오고 `↪ 2일째 밀린 일`처럼 표시
  - 켜 둔 채로 자정을 넘겨도 30초 안에 자동 반영
- **내일로 미루기**: 할 일 우클릭 → `내일로 미루기`
- **수정 / 삭제**: 더블클릭으로 바로 수정, 마우스를 올리면 나오는 `✕`로 삭제
- **날짜 이동**: `◀ ▶`로 지난 기록(보기 전용)과 미래 날짜(미리 등록 가능) 확인
- **창 고정**: `◆` 클릭 시 항상 위에 표시 (다시 누르면 해제)
- **위치·크기 기억**: 상단 바를 드래그해서 이동, 오른쪽 아래 `◢`로 크기 조절

## 실행 방법

### 파이썬 없이 실행 (Windows)

[DesktopTodo.exe 다운로드](https://github.com/sihooooo15/-/releases/latest/download/DesktopTodo.exe) 후 더블클릭하면 끝입니다.

- 처음 실행 시 "Windows의 PC 보호" 창이 뜨면 **추가 정보 → 실행**
- 코드가 바뀌면 GitHub Actions가 exe를 자동으로 다시 빌드해서 같은 링크에 올립니다.

### 파이썬으로 실행

Python 3.9 이상만 있으면 되고, 추가 설치할 패키지는 없습니다 (표준 라이브러리 tkinter 사용).

```bash
python todo_widget.py
```

Windows에서는 `start_todo.pyw`를 더블클릭하면 콘솔 창 없이 위젯만 뜹니다.

> 리눅스에서 `No module named tkinter` 오류가 나면 `sudo apt install python3-tk`

## 컴퓨터 켤 때 자동 실행 (Windows)

1. `Win + R` → `shell:startup` 입력 → 시작프로그램 폴더 열기
2. `DesktopTodo.exe`(또는 `start_todo.pyw`)를 **우클릭 → 바로 가기 만들기** 후, 만든 바로 가기를 그 폴더로 이동

## 데이터 저장 위치

`사용자 폴더/.desktop_todo/todos.json` (예: `C:\Users\이름\.desktop_todo\todos.json`)

- 할 일을 바꿀 때마다 바로 저장됩니다.
- 파일이 깨지면 `todos.broken.json`으로 백업한 뒤 빈 상태로 시작합니다.

## 알아 둘 점

- `Win + D`(바탕화면 보기)를 누르면 다른 창처럼 같이 숨겨집니다. 계속 보이게 하려면 `◆` 고정을 켜 두세요.
- 테두리 없는 창이라 작업 표시줄에는 나타나지 않습니다. 닫을 때는 `✕`를 누르세요.
- macOS에서는 키보드 입력 문제 때문에 일반 창(제목 표시줄 있음)으로 뜹니다.

## 파일 구성

| 파일 | 설명 |
|---|---|
| `todo_widget.py` | 위젯 화면 (tkinter) |
| `todo_store.py` | 할 일 저장/이월 로직 (화면과 분리) |
| `start_todo.pyw` | Windows용 콘솔 없는 실행 파일 |
| `.github/workflows/build-exe.yml` | Windows exe 자동 빌드 |
| `tests/` | 저장/이월 로직 테스트 (`python -m unittest discover -s tests`) |
