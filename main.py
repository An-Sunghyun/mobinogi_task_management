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
# 페이지 구성
# -------------------------
st.set_page_config(
    page_title=f"{APP_NAME} {VERSION}",
    layout="centered",
    initial_sidebar_state="auto"
)

# -------------------------
# 로컬 스토리지 연동: JS -> 파라미터 및 초기 로드
# -------------------------
# JS: 브라우저 localStorage에서 tasksData가 있고, 'loaded' 플래그가 없으면 쿼리파라미터로 전달 및 플래그 설정
html(
    """
    <script>
      const data = localStorage.getItem('tasksData');
      const loaded = localStorage.getItem('loaded');
      if (data && !loaded) {
        localStorage.setItem('loaded', '1');
        const url = window.location.pathname + '?initialData=' + encodeURIComponent(data);
        window.location.replace(url);
      }
    </script>
    """,
    height=0,
)
# Python: URL 쿼리파라미터에서 초기 데이터 로드
params = st.query_params
if 'initialData' in params:
    try:
        loaded_data = json.loads(params['initialData'][0])
        st.session_state.data = loaded_data
    except Exception:
        pass
    # 쿼리 파라미터 제거
    st.experimental_set_query_params()
# -------------------------
params = st.query_params
if 'initialData' in params:
    try:
        loaded_data = json.loads(params['initialData'][0])
        st.session_state.data = loaded_data
    except Exception:
        pass
    # 쿼리 파라미터 제거
    st.experimental_set_query_params()
# -------------------------
)

# -------------------------
# 스타일 및 반응형: 모바일 + 폰트 크기
# -------------------------
st.markdown(
    """
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      @media (max-width: 768px) {
        .stColumns > div { width: 100% !important; flex: 100% !important; }
      }
      .stCheckbox label { font-size: 16px; }
      .stSelectbox label, .stSelectbox div[data-testid] { font-size: 16px; }
      button, .stDownloadButton>button, .stFileUploader>div { font-size: 14px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# 설정: 태스크 정의
# -------------------------
DAILY_TASKS = [
    {"id": "불길한_소환의_결계", "label": "불길한 소환의 결계"},
    {"id": "심층으로_떨린_검은_구멍", "label": "심층으로 떨린 검은 구멍"},
    {"id": "일일_아르바이트", "label": "일일 아르바이트"},
    {"id": "요일_던전", "label": "요일 던전"},
    {"id": "길드_출석", "label": "길드 출석"},
    {"id": "망령의_탑", "label": "망령의 탑", "exclude_reset": True},
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
# 상태 초기화 및 자동 리셋 로직
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
                "last_daily_reset": None,
                "last_weekly_reset": None,
            }
            for char in st.session_state.characters
        }

def get_monday(dt):
    return dt - datetime.timedelta(days=dt.weekday())

def reset_if_needed():
    now = datetime.datetime.now()
    for char, info in st.session_state.data.items():
        # 일일 리셋
        if info["last_daily_reset"] is None or ((now - info["last_daily_reset"]).days >= 1 and now.hour >= 6):
            for t in DAILY_TASKS:
                if not t.get("exclude_reset"): info["daily"][t["id"]] = False
            info["last_daily_reset"] = now
        # 주간 리셋
        mon = get_monday(now)
        if info["last_weekly_reset"] is None or (info["last_weekly_reset"].date() < mon.date() and now.hour >= 6):
            for t in WEEKLY_TASKS:
                info["weekly"][t["id"]] = False
            info["last_weekly_reset"] = now

def sync_guild(val):
    for info in st.session_state.data.values():
        info["daily"]["길드_출석"] = val

# -------------------------
# 메인 함수
# -------------------------
def main():
    init_state()
    reset_if_needed()

    # 타이틀 출력
    st.title(f"{APP_NAME} {VERSION}")

    # 캐릭터 선택
    char = st.selectbox("캐릭터 선택", st.session_state.characters, key="selected_char")
    info = st.session_state.data[char]

    # DAILY 섹션
    st.header("DAILY")
    c1, c2 = st.columns(2)
    with c1:
        for t in DAILY_TASKS[:3]:
            info["daily"][t["id"]] = st.checkbox(t["label"], value=info["daily"][t["id"]], key=f"d_{t['id']}")
    with c2:
        for t in DAILY_TASKS[3:]:
            if t["id"] == "길드_출석":
                v = st.checkbox(t["label"], value=info["daily"][t["id"]], key=f"d_{t['id']}")
                if v != info["daily"]["길드_출석"]: sync_guild(v)
            else:
                info["daily"][t["id"]] = st.checkbox(t["label"], value=info["daily"][t["id"]], key=f"d_{t['id']}")

    # WEEKLY 섹션
    st.header("WEEKLY")
    for t in WEEKLY_TASKS:
        info["weekly"][t["id"]] = st.checkbox(t["label"], value=info["weekly"][t["id"]], key=f"w_{t['id']}")

    # 데이터 관리 영역
    st.markdown("---")
    st.subheader("데이터 관리")
    # JSON 다운로드
    json_str = json.dumps(st.session_state.data, default=str, ensure_ascii=False)
    st.download_button("JSON 다운로드", data=json_str, file_name="tasks_data.json", mime="application/json")
    # JSON 업로드
    up = st.file_uploader("JSON 업로드", type="json")
    if up:
        st.session_state.data = json.load(up)
        st.experimental_rerun()

    # 수동 초기화 버튼
    ca, cb = st.columns(2)
    with ca:
        if st.button("일일 숙제 수동 초기화"): manual_daily_reset()
    with cb:
        if st.button("주간 숙제 수동 초기화"): manual_weekly_reset()

    # 렌더 완료 후 로컬스토리지에 저장
    html(
        f"""
        <script>
          const dataObj = {json_str};
          localStorage.setItem('tasksData', JSON.stringify(dataObj));
        </script>
        """,
        height=0,
    )

# -------------------------
# 수동 초기화 함수 정의
# -------------------------
def manual_daily_reset():
    now = datetime.datetime.now()
    for info in st.session_state.data.values():
        for t in DAILY_TASKS:
            if not t.get("exclude_reset"): info["daily"][t["id"]] = False
        info["last_daily_reset"] = now
    st.experimental_rerun()

def manual_weekly_reset():
    now = datetime.datetime.now()
    for info in st.session_state.data.values():
        for t in WEEKLY_TASKS: info["weekly"][t["id"]] = False
        info["last_weekly_reset"] = now
    st.experimental_rerun()

if __name__ == "__main__":
    main()
