# app.py
import streamlit as st
import json
from datetime import datetime, timedelta
import calendar

# ─── 1. 버전 정보 ─────────────────────────────────────────
VERSION = "0.001"

# ─── 2. 기본 설정 ─────────────────────────────────────────
DEFAULT_DATA = {
    "version": VERSION,
    "last_daily_reset": None,
    "last_weekly_reset": None,
    "characters": ["Character1"],  # 기본 캐릭터
    "selected_character": "Character1",
    "tasks": {
        "daily": {
            "불길한 소환의 결계": {"count": 0, "limit": 2, "checked": False},
            "검은 구멍": {"count": 0, "limit": 3, "checked": False},
            "요일던전": {"count": 0, "limit": 1, "checked": False},
            "아르바이트[오후]": {"count": 0, "limit": 1, "checked": False},
            "길드 출석": {"count": 0, "limit": 1, "checked": False, "shared": True},
            "망령의 탑": {"count": 0, "limit": 1, "checked": False, "completed": False},
        },
        "weekly": {
            "어비스 - 가라앉은 유적": False,
            "어비스 - 무너진 제단": False,
            "어비스 - 파멸의 전당": False,
            "레이드 - 글라스기브넨": False,
            "필드보스 - 페리": False,
            "필드보스 - 크라브네흐": False,
            "필드보스 - 크라마": False,
            "필드보스 재화 교환": False,
            "어비스 보상 수령": False,
        }
    }
}

# ─── 3. 데이터 로드/초기화 ───────────────────────────────────
def load_data():
    if "data" not in st.session_state:
        st.session_state.data = DEFAULT_DATA.copy()
        # 초기화 시각 설정
        now = datetime.now()
        st.session_state.data["last_daily_reset"] = now.isoformat()
        st.session_state.data["last_weekly_reset"] = now.isoformat()
    return st.session_state.data

data = load_data()

# ─── 4. 리셋 로직 ───────────────────────────────────────────
def daily_reset():
    for name, t in data["tasks"]["daily"].items():
        # 망령의 탑 completed 가 True 면 skip
        if name == "망령의 탑" and t.get("completed", False):
            continue
        t["count"] = 0
        t["checked"] = False
    data["last_daily_reset"] = datetime.now().isoformat()

def weekly_reset():
    for name in data["tasks"]["weekly"]:
        data["tasks"]["weekly"][name] = False
    data["last_weekly_reset"] = datetime.now().isoformat()

# 자동 리셋 체크
now = datetime.now()
# daily: 매일 6시
last_d = datetime.fromisoformat(data["last_daily_reset"])
if now.hour >= 6 and now.date() > last_d.date():
    daily_reset()
# weekly: 월요일 6시
last_w = datetime.fromisoformat(data["last_weekly_reset"])
if now.weekday() == 0 and now.hour >= 6 and now.date() > last_w.date():
    weekly_reset()

# ─── 5. 레이아웃 & 스타일 적용 ───────────────────────────────
st.set_page_config(page_title=f"Mobinogi Task Management Ver{VERSION}", layout="wide")
st.markdown(f"<h1 style='text-align:center;'>Mobinogi Task Management Ver{VERSION}</h1>", unsafe_allow_html=True)
# 폰트, 버튼 크기 등 CSS
st.markdown("""
<style>
body { background-color: #1e1e1e; color: #fafafa; }
h1 { font-size:2.5rem; }
.sidebar .sidebar-content { font-size: 0.9rem; }
button { padding: 0.4rem 1rem; font-size: 0.9rem; }
.checkbox { transform: scale(1.2); }
</style>
""", unsafe_allow_html=True)

# ─── 6. 캐릭터 관리 컴포넌트 ─────────────────────────────────
col1, col2, col3 = st.columns([3,1,1])
with col1:
    selected = st.selectbox("캐릭터 선택", data["characters"], index=data["characters"].index(data["selected_character"]))
    data["selected_character"] = selected
with col2:
    if st.button("캐릭터 추가"):
        st.session_state.show_add = True
with col3:
    if st.button("캐릭터 수정"):
        st.session_state.show_edit = True
    if st.button("캐릭터 삭제"):
        if len(data["characters"]) <= 1:
            st.error("최소 한 개 이상의 캐릭터가 필요합니다.")
        else:
            data["characters"].remove(selected)
            data["selected_character"] = data["characters"][0]

# 추가 / 수정 입력창
if st.session_state.get("show_add", False):
    new_name = st.text_input("새 캐릭터 이름 입력")
    if st.button("확인"):
        if new_name and new_name not in data["characters"]:
            data["characters"].append(new_name)
            st.session_state.show_add = False
        else:
            st.error("유효한 이름을 입력하세요.")
if st.session_state.get("show_edit", False):
    edit_name = st.text_input("변경할 이름 입력", value=selected)
    if st.button("확인"):
        if edit_name and edit_name not in data["characters"]:
            idx = data["characters"].index(selected)
            data["characters"][idx] = edit_name
            data["selected_character"] = edit_name
            st.session_state.show_edit = False
        else:
            st.error("유효한 이름을 입력하세요.")

st.markdown("---")

# ─── 7. 숙제 체크박스 ───────────────────────────────────────
daily_box, weekly_box = st.columns(2)

with daily_box:
    st.subheader("DAILY")
    for name, t in data["tasks"]["daily"].items():
        if name == "망령의 탑":
            cols = st.columns([1,1])
            with cols[0]:
                checked = st.checkbox(f"{name} (일 {t['limit']}회)", t["checked"], key=f"{name}_daily")
                t["checked"] = checked
            with cols[1]:
                completed = st.checkbox("완료", t["completed"], key=f"{name}_completed")
                t["completed"] = completed
        else:
            checked = st.checkbox(f"{name} (일 {t['limit']}회)", t["checked"], key=name)
            t["checked"] = checked
        # '길드 출석' 공유 처리
        if t.get("shared", False):
            shared_flag = t["checked"]
            for c in data["tasks"]["daily"].values():
                if c.get("shared"):
                    c["checked"] = shared_flag

with weekly_box:
    st.subheader("WEEKLY")
    for name, checked in data["tasks"]["weekly"].items():
        data["tasks"]["weekly"][name] = st.checkbox(f"{name} (주 1회)", checked, key=name)

# ─── 8. 데이터 관리 Footer ─────────────────────────────────
st.markdown("---")
if st.button("데이터 관리"):
    with st.container():
        st.download_button(
            label="JSON 다운로드",
            data=json.dumps(data, ensure_ascii=False, indent=2),
            file_name="mobinogi_tasks.json",
            mime="application/json"
        )
        uploaded = st.file_uploader("JSON 업로드", type=["json"])
        if uploaded:
            try:
                new_data = json.load(uploaded)
                st.session_state.data = new_data
                st.success("업로드 및 적용 완료")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"파싱 오류: {e}")
        if st.button("일일 숙제 수동 초기화"):
            daily_reset()
            st.success("일일 숙제가 초기화되었습니다.")
        if st.button("주간 숙제 수동 초기화"):
            weekly_reset()
            st.success("주간 숙제가 초기화되었습니다.")
