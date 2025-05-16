import streamlit as st
import datetime
import json
from streamlit.components.v1 import html

# -------------------------
# 앱 버전 정보
# -------------------------
APP_NAME = "Mobinogi Task Management"
VERSION = "V0.01"

# -------------------------
# 페이지 설정
# -------------------------
st.set_page_config(
    page_title=f"{APP_NAME} {VERSION}",
    layout="centered",
)

# -------------------------
# 로컬 스토리지 연동: JS 로드 & Python 초기화
# -------------------------
# 1) JS: localStorage에 tasksData가 있으면 initialData 파라미터로 전달
html(
    """
    <script>
      const data = localStorage.getItem('tasksData');
      const params = new URLSearchParams(window.location.search);
      if (data && !params.has('initialData')) {
        const url = window.location.pathname + '?initialData=' + encodeURIComponent(data);
        window.location.replace(url);
      }
    </script>
    """,
    height=0,
)
# 2) Python: initialData 파라미터가 있으면 세션에 로드
if "initialData" in st.query_params:
    try:
        loaded = json.loads(st.query_params["initialData"][0])
        st.session_state.data = loaded
    except Exception:
        pass
    # 파라미터 제거
    st.experimental_set_query_params()

# -------------------------
# 태스크 정의
# -------------------------
DAILY_TASKS = [
    {"id": "불길한_소환의_결계", "label": "불길한 소환의 결계", "exclude": False},
    {"id": "심층으로_떨린_검은_구멍", "label": "심층으로 떨린 검은 구멍", "exclude": False},
    {"id": "일일_아르바이트", "label": "일일 아르바이트", "exclude": False},
    {"id": "요일_던전", "label": "요일 던전", "exclude": False},
    {"id": "길드_출석", "label": "길드 출석", "exclude": False},
    {"id": "망령의_탑", "label": "망령의 탑", "exclude": True},
]
WEEKLY_TASKS = [
    {"id": "어비스_가라앉은_유적", "label": "어비스 - 가라앉은 유적"},
    {"id": "어비스_무너진_제단", "label": "어비스 - 무너진 제단"},
    {"id": "어비스_파멸의_전당", "label": "어비스 - 파멸의 전당"},
    {"id": "레이드_글라스기브넨", "label": "레이드 - 글라스기브넨"},
    {"id": "필드보스_페리", "label": "필드보스 - 페리"},
    {"id": "필드보스_크라브니흐", "label": "필드보스 - 크라브니흐"},
    {"id": "필드보스_크라마", "label": "필드보스 - 크라마"},
    {"id": "필드보스_재화_교환", "label": "필드보스 재화 교환"},
    {"id": "어비스_보상_수령", "label": "어비스 보상 수령"},
    {"id": "냥원랜드", "label": "냥원랜드"},
]

# -------------------------
# 상태 초기화
# -------------------------
def init_state():
    if "characters" not in st.session_state:
        st.session_state.characters = ["오덕왕의석궁병"]
    if "selected_char" not in st.session_state:
        st.session_state.selected_char = st.session_state.characters[0]
    if "data" not in st.session_state:
        st.session_state.data = {
            char: {
                "daily": {t["id"]: False for t in DAILY_TASKS},
                "weekly": {t["id"]: False for t in WEEKLY_TASKS},
            }
            for char in st.session_state.characters
        }

# -------------------------
# 로컬스토리지 업데이트
# -------------------------
def update_localstorage():
    json_str = json.dumps(st.session_state.data, ensure_ascii=False)
    html(
        f"""
        <script>
          localStorage.setItem('tasksData', `{json_str}`);
        </script>
        """,
        height=0,
    )

# -------------------------
# 자동 리셋 로직 (매일 6시, 매주 월요일 6시)
# -------------------------
def get_monday(dt):
    return dt - datetime.timedelta(days=dt.weekday())

def reset_if_needed():
    now = datetime.datetime.now()
    for char, info in st.session_state.data.items():
        # 일일
        last = info.get("last_daily", None)
        if last is None or (now.date() > last and now.hour >= 6):
            for t in DAILY_TASKS:
                if not t.get("exclude", False):
                    info["daily"][t["id"]] = False
            info["last_daily"] = now.date()
        # 주간
        lastw = info.get("last_weekly", None)
        monday = get_monday(now)
        if lastw is None or (lastw < monday.date() and now.hour >= 6):
            for t in WEEKLY_TASKS:
                info["weekly"][t["id"]] = False
            info["last_weekly"] = now.date()

# -------------------------
# 수동 초기화 함수
# -------------------------
def manual_daily_reset():
    for info in st.session_state.data.values():
        for t in DAILY_TASKS:
            if not t.get("exclude", False):
                info["daily"][t["id"]] = False
    update_localstorage()

def manual_weekly_reset():
    for info in st.session_state.data.values():
        for t in WEEKLY_TASKS:
            info["weekly"][t["id"]] = False
    update_localstorage()

# -------------------------
# 메인
# -------------------------
def main():
    init_state()
    reset_if_needed()

    st.title(f"{APP_NAME} {VERSION}")

    # 캐릭터 선택
    char = st.selectbox(
        "캐릭터 선택",
        st.session_state.characters,
        key="selected_char",
        on_change=update_localstorage
    )

    info = st.session_state.data[char]

    # DAILY
    st.header("DAILY")
    cols = st.columns(2)
    for idx, t in enumerate(DAILY_TASKS):
        cb = st.checkbox(
            t["label"],
            value=info["daily"][t["id"]],
            key=f"d_{t['id']}",
            on_change=update_localstorage
        )
        info["daily"][t["id"]] = cb

    # WEEKLY
    st.header("WEEKLY")
    for t in WEEKLY_TASKS:
        cb = st.checkbox(
            t["label"],
            value=info["weekly"][t["id"]],
            key=f"w_{t['id']}",
            on_change=update_localstorage
        )
        info["weekly"][t["id"]] = cb

    # 데이터 관리
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("일일 숙제 수동 초기화"):
            manual_daily_reset()
    with c2:
        if st.button("주간 숙제 수동 초기화"):
            manual_weekly_reset()
    with c3:
        if st.button("초기 상태로 복원"):
            st.session_state.pop('data')
            init_state()
            update_localstorage()

    # 초기 저장 호출
    update_localstorage()

if __name__ == "__main__":
    main()
