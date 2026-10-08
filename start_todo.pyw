# Windows에서 더블클릭하면 콘솔(검은 창) 없이 위젯만 실행된다.
import os
import sys

# 이 파일이 있는 폴더를 기준으로 모듈을 찾도록 경로를 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from todo_widget import main

main()
