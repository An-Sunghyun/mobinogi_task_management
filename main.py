# app.py
import streamlit as st
import json
from datetime import datetime
import copy

# ─── 1. 버전 정보 ─────────────────────────────────────────
VERSION = "0.001"

# ─── 2. 기본 데이터 템플릿 ─────────────────────────────────
DEFAULT_TASKS = {
    "daily": {
        "불길한 소환의 결계": {"limit": 2, "checked": False},
        "검은 구멍":             {"limit": 3, "checked": False},
        "요일던전":              {"limit": 1, "checked": False},
        "아르바이트[오후]":      {"limit": 1, "checked": False},
        "길드 출석":            {"limit": 1, "checked": False, "shared": True},
        "망령의 탑":            {"limit": 1, "checked": False, "completed": False},
    },
    "weekly": {
        "어비스 - 가라앉은 유적": False,
        "어비스 - 무너진 제단":   False,
        "어비스 - 파멸의 전당":   False,
        "레이드 - 글라스기브넨":  False,
        "필드보스 - 페리":       False,
        "필드보스 - 크라브네흐":  False,
        "필드보스 - 크라마":     False,
        "필드보스 재화 교환":    False,
        "어비스 보상 수령":      False,
    }
}

DEFAULT_DATA = {
    "version": VERSION,
    "last_daily_reset": None,
    "last_weekly_reset": None,
    "characters": ["캐릭터1"],
    "selected_character": "캐릭터1",
    "char_data": {
        # 각 캐릭터별로 deep copy된 체크리스트
        "캐릭터1": copy.deepcopy(DEFAULT_TASKS)
    }
}

# ─── 3. 세션 상태 로딩 ───────────────────────────────────────
def load_data():
    if "data" not in st.session_state:
        st.session_state.data = DEFAULT_DATA.copy()
        now = datetime.now().isoformat()
        st.session_state.data["last_daily_reset"] = now
        st.session_state.data["last_weekly_reset"] = now
        # 모드 플래그 초기화
        st.session_state["add_mode"] = False
        st.session_state["edit_mode"] = False
    return st.session_state.data

data = load_data()

# ─── 4. 초기화 로직 ─────────────────────────────────────────
def daily_reset():
    for ch in data["characters"]:
        for name, t in data["char_data"][ch]["daily"].items():
            if name == "망령의 탑" and t.get("completed"):
                continue
            t["checked"] = False
    data["last_daily_reset"] = datetime.now().isoformat()

def weekly_reset():
    for ch in data["characters"]:
        for name in data["char_data"][ch]["weekly"]:
            data["char_data"][ch]["weekly"][name] = False
    data["last_weekly_reset"] = datetime.now().isoformat()

now = datetime.now()
last_d = datetime.fromisoformat(data["last_daily_reset"])
if now.hour >= 6 and now.date() > last_d.date():
    daily_reset()
last_w = datetime.fromisoformat(data["last_weekly_reset"])
if now.weekday() == 0 and now.hour >= 6 and now.date() > last_w.date():
    weekly_reset()

# ─── 5. 페이지 설정 & 스타일 ─────────────────────────────────
st.set_page_config(page_title=f"Mobinogi Task Management Ver{VERSION}", layout="wide")
st.markdown(f"<h1 style='text-align:center;'>Mobinogi Task Management Ver{VERSION}</h1>", unsafe_allow_html=True)
st.markdown("""
<style>
body { background-color:#1e1e1e; color:#fafafa; }
h1 { font-size:2.5rem; }
button { padding:0.4rem 1rem; font-size:0.9rem; }
</style>
""", unsafe_allow_html=True)

# ─── 6. 캐릭터 선택 & 관리 ───────────────────────────────────
col1, col2, col3, col4 = st.columns([4,1,1,1])
with col1:
    sel = st.selectbox("캐릭터 선택", data["characters"],
                       index=data["characters"].index(data["selected_character"]))
    data["selected_character"] = sel

with col2:
    if st.button("캐릭터 추가"):
        st.session_state["add_mode"] = True
        st.session_state["edit_mode"] = False
with col3:
    if st.button("캐릭터 수정"):
        st.session_state["edit_mode"] = True
        st.session_state["add_mode"] = False
with col4:
    if st.button("캐릭터 삭제"):
        if len(data["characters"]) > 1:
            # 삭제 전 확인
            if st.confirm(f"'{sel}' 캐릭터를 정말 삭제하시겠습니까?"):
                data["characters"].remove(sel)
                data["char_data"].pop(sel, None)
                data["selected_character"] = data["characters"][0]
        else:
            st.error("최소 하나의 캐릭터는 있어야 합니다.")

# ── 6.1 캐릭터 추가 폼 ───────────────────────────────────────
if st.session_state["add_mode"]:
    with st.form("add_form", clear_on_submit=True):
        new_name = st.text_input("새 캐릭터 이름")
        submitted = st.form_submit_button("확인")
        if submitted:
            if new_name and new_name not in data["characters"]:
                data["characters"].append(new_name)
                # 새로운 캐릭터에 기본 TASKS deep copy
                data["char_data"][new_name] = copy.deepcopy(DEFAULT_TASKS)
                data["selected_character"] = new_name
                st.experimental_rerun()
            else:
                st.error("유효한 이름을 입력하세요.")

# ── 6.2 캐릭터 수정 폼 ───────────────────────────────────────
if st.session_state["edit_mode"]:
    with st.form("edit_form", clear_on_submit=True):
        edit_name = st.text_input("변경할 이름", value=sel)
        submitted = st.form_submit_button("확인")
        if submitted:
            if edit_name and edit_name not in data["characters"]:
                idx = data["characters"].index(sel)
                # 리스트와 dict 키 모두 교체
                data["characters"][idx] = edit_name
                data["char_data"][edit_name] = data["char_data"].pop(sel)
                data["selected_character"] = edit_name
                st.experimental_rerun()
            else:
                st.error("유효한 이름을 입력하세요.")

st.markdown("---")

# ─── 7. 체크리스트 그리기 ───────────────────────────────────
daily_col, weekly_col = st.columns(2)
ch_data = data["char_data"][data["selected_character"]]

with daily_col:
    st.subheader("DAILY")
    for name, t in ch_data["daily"].items():
        if name == "망령의 탑":
            c1, c2 = st.columns([1,1])
            with c1:
                t["checked"] = st.checkbox(f"{name} ({t['limit']}회)", t["checked"], key=f"{sel}_{name}_d")
            with c2:
                t["completed"] = st.checkbox("완료", t["completed"], key=f"{sel}_{name}_c")
        else:
            t["checked"] = st.checkbox(f"{name} ({t['limit']}회)", t["checked"], key=f"{sel}_{name}_d")
        # '길드 출석' 동기화
        if t.get("shared"):
            shared = t["checked"]
            for other in data["characters"]:
                data["char_data"][other]["daily"][name]["checked"] = shared

with weekly_col:
    st.subheader("WEEKLY")
    for name in ch_data["weekly"]:
        ch_data["weekly"][name] = st.checkbox(f"{name} (주 1회)", ch_data["weekly"][name],
                                              key=f"{sel}_{name}_w")

# ─── 8. 데이터 관리 Footer ─────────────────────────────────
st.markdown("---")
if st.button("데이터 관리"):
    with st.container():
        st.download_button(
            "JSON 다운로드",
            data=json.dumps(data, ensure_ascii=False, indent=2),
            file_name="mobinogi_tasks.json",
            mime="application/json",
        )
        uploaded = st.file_uploader("JSON 업로드", type="json")
        if uploaded:
            try:
                data.update(json.load(uploaded))
                st.success("업로드 완료, 페이지를 새로고침합니다.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"파싱 오류: {e}")
        if st.button("일일 숙제 수동 초기화"):
            daily_reset()
            st.success("일일 숙제가 초기화되었습니다.")
        if st.button("주간 숙제 수동 초기화"):
            weekly_reset()
            st.success("주간 숙제가 초기화되었습니다.")
