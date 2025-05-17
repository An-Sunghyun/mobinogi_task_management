import streamlit as st
import json
from datetime import datetime, timedelta
import base64 # JSON 파일 다운로드를 위해 필요

# --- 프로그램 설정 ---
PROGRAM_TITLE = "Mobinogi Task Management Ver0.001"
DAILY_RESET_TIME = 6 # 오전 6시
WEEKLY_RESET_DAY = 0 # 월요일 (0: 월, 1: 화, ..., 6: 일)
WEEKLY_RESET_TIME = 6 # 오전 6시

# --- 숙제 정보 정의 ---
DAILY_TASKS_META = {
    "불길한 소환의 결계": {"type": "count", "max": 2},
    "검은 구멍": {"type": "count", "max": 3},
    "요일던전": {"type": "check"},
    "아르바이트[오후]": {"type": "check"},
    "길드 출석": {"type": "check", "shared": True},
    "망령의 탑": {"type": "status", "options": ["일일", "완료"]}
}

WEEKLY_TASKS_META = {
    "어비스 - 가라앉은 유적": {"type": "check"},
    "어비스 - 무너진 제단": {"type": "check"},
    "어비스 - 파멸의 전당": {"type": "check"},
    "레이드 - 글라스기브넨": {"type": "check"},
    "필드보스 - 페리": {"type": "check"},
    "필드보스 - 크라브네흐": {"type": "check"},
    "필드보스 - 크라마": {"type": "check"},
    "필드보스 재화 교환": {"type": "check"},
    "어비스 보상 수령": {"type": "check"}
}

# --- 데이터 초기 상태 생성 함수 ---
def create_initial_data():
    now = datetime.now()
    return {
        "version": PROGRAM_TITLE.split()[-1],
        "last_daily_reset": now.strftime("%Y-%m-%d %H:%M:%S"),
        "last_weekly_reset": now.strftime("%Y-%m-%d %H:%M:%S"),
        "guild_attendance_checked": False,
        "characters": {}
    }

# --- 데이터 로드 함수 (로컬 스토리지 대안: 세션 상태 사용) ---
# Streamlit에서는 새로고침 시 상태가 날아가므로, 실제 로컬 스토리지 연동은 JS 필요
# 여기서는 Streamlit 세션 상태를 사용하되, 로컬 스토리지에 저장/로드하는 것처럼 동작하는 척만 합니다.
# 실제 구현에서는 파일 업로드/다운로드 또는 별도의 JS 연동이 필요합니다.
def load_data():
    if 'app_data' not in st.session_state:
        st.session_state.app_data = create_initial_data()
        # 실제 로컬 스토리지 로드 로직 (JS 필요) -> 여기서는 생략 또는 파일 업로드 유도
        st.info("데이터가 로드되었습니다. 또는 초기 데이터가 생성되었습니다.")
        # TODO: 실제 로컬 스토리지에서 데이터를 읽어오는 JS 연동 또는 파일 업로드 안내 추가

    # 자동 초기화 체크
    check_and_reset_tasks(st.session_state.app_data)

# --- 자동 초기화 로직 ---
def check_and_reset_tasks(data):
    now = datetime.now()
    last_daily_reset_str = data.get("last_daily_reset")
    last_weekly_reset_str = data.get("last_weekly_reset")

    last_daily_reset = datetime.strptime(last_daily_reset_str, "%Y-%m-%d %H:%M:%S") if last_daily_reset_str else datetime.min
    last_weekly_reset = datetime.strptime(last_weekly_reset_str, "%Y-%m-%d %H:%M:%S") if last_weekly_reset_str else datetime.min

    # 일일 초기화 체크
    next_daily_reset = last_daily_reset.replace(hour=DAILY_RESET_TIME, minute=0, second=0, microsecond=0)
    if now.time() >= datetime.strptime(f"{DAILY_RESET_TIME}:00:00", "%H:%M:%S").time() and now.date() > last_daily_reset.date():
         manual_reset_daily(data, auto=True) # 자동 초기화 시 망탑 완료는 스킵
         data["last_daily_reset"] = now.strftime("%Y-%m-%d %H:%M:%S")
         st.session_state.app_data = data # 세션 상태 업데이트
         st.rerun() # UI 새로고침

    # 주간 초기화 체크 (월요일 오전 6시)
    next_weekly_reset = last_weekly_reset.replace(hour=WEEKLY_RESET_TIME, minute=0, second=0, microsecond=0)
    while next_weekly_reset.weekday() != WEEKLY_RESET_DAY or next_weekly_reset <= last_weekly_reset:
         next_weekly_reset += timedelta(days=1)

    if now >= next_weekly_reset:
        manual_reset_weekly(data)
        data["last_weekly_reset"] = now.strftime("%Y-%m-%d %H:%M:%S")
        data["guild_attendance_checked"] = False # 길드 출석도 주간 초기화 시 함께 초기화
        st.session_state.app_data = data # 세션 상태 업데이트
        st.rerun() # UI 새로고침


# --- 수동 초기화 로직 ---
def manual_reset_daily(data, auto=False):
    for char_data in data["characters"].values():
        for task_name, task_info in DAILY_TASKS_META.items():
            if task_name == "망령의 탑":
                if auto and char_data["daily"].get(task_name, {}).get("status") == "완료":
                     continue # 자동 초기화 시 망탑 완료는 스킵
                char_data["daily"][task_name] = {"status": "일일"}
            elif task_info["type"] == "count":
                char_data["daily"][task_name] = {"count": 0}
            elif task_info["type"] == "check":
                 if not task_info.get("shared", False): # 공유 숙제는 수동 초기화에서 제외 (아래에서 별도 처리)
                    char_data["daily"][task_name] = {"checked": False}

    # 길드 출석은 전역 초기화
    if not auto: # 자동 초기화 시에는 일일 초기화 시점 기준, 수동 초기화는 버튼 누르는 시점 기준
         data["guild_attendance_checked"] = False

    st.session_state.app_data = data # 세션 상태 업데이트
    st.success("일일 숙제가 초기화되었습니다.")

def manual_reset_weekly(data):
    for char_data in data["characters"].values():
        for task_name in WEEKLY_TASKS_META:
            char_data["weekly"][task_name] = {"checked": False}
    data["guild_attendance_checked"] = False # 길드 출석도 주간 초기화 시 함께 초기화
    st.session_state.app_data = data # 세션 상태 업데이트
    st.success("주간 숙제가 초기화되었습니다.")

# --- JSON 파일 다운로드 ---
def download_json(data):
    json_string = json.dumps(data, indent=4, ensure_ascii=False)
    b64 = base64.b64encode(json_string.encode('utf-8')).decode()
    href = f'<a href="data:file/json;base66,{b64}" download="mabinogi_tasks_data.json">JSON 파일 다운로드</a>'
    return href

# --- JSON 파일 업로드 ---
# Streamlit file_uploader를 통해 파일을 받고 파싱하는 로직 필요

# --- Streamlit UI 구현 시작 ---
st.title(PROGRAM_TITLE)

# 데이터 로드 (및 자동 초기화 체크)
load_data()
app_data = st.session_state.app_data

# --- 캐릭터 관리 섹션 ---
st.header("캐릭터 관리")

col1, col2 = st.columns([3, 1])
with col1:
    current_character_name = st.selectbox(
        "캐릭터 선택",
        list(app_data["characters"].keys()),
        index=0 if app_data["characters"] else None,
        key="char_select"
    )
with col2:
    # 추가, 수정, 삭제 버튼 컬럼 분리
    add_col, edit_col, delete_col = st.columns(3)
    with add_col:
        add_button = st.button("추가")
    with edit_col:
        edit_button = st.button("수정", disabled=current_character_name is None)
    with delete_col:
        delete_button = st.button("삭제", disabled=current_character_name is None)

# 캐릭터 추가 입력 필드
if add_button:
    new_char_name = st.text_input("추가할 캐릭터 이름")
    if st.button("확인", key="confirm_add"):
        if new_char_name and new_char_name not in app_data["characters"]:
            initial_char_data = {
                 "daily": {name: {"count": 0} if meta["type"] == "count" else ({"checked": False} if meta["type"] == "check" and not meta.get("shared", False) else {"status": "일일"} if meta["type"] == "status" else {}) for name, meta in DAILY_TASKS_META.items()},
                 "weekly": {name: {"checked": False} for name in WEEKLY_TASKS_META}
            }
            app_data["characters"][new_char_name] = initial_char_data
            st.session_state.app_data = app_data
            st.success(f"캐릭터 '{new_char_name}'가 추가되었습니다.")
            st.rerun()
        elif new_char_name in app_data["characters"]:
            st.warning("같은 이름의 캐릭터가 이미 존재합니다.")

# 캐릭터 수정 입력 필드
if edit_button and current_character_name:
    new_char_name = st.text_input("변경할 캐릭터 이름", value=current_character_name)
    if st.button("확인", key="confirm_edit"):
        if new_char_name and new_char_name != current_character_name and new_char_name not in app_data["characters"]:
            app_data["characters"][new_char_name] = app_data["characters"].pop(current_character_name)
            st.session_state.app_data = app_data
            st.success(f"캐릭터 이름이 '{current_character_name}'에서 '{new_char_name}'으로 변경되었습니다.")
            st.rerun()
        elif new_char_name == current_character_name:
             st.info("변경할 이름이 이전과 같습니다.")
        elif new_char_name in app_data["characters"]:
            st.warning("변경할 이름이 이미 존재합니다.")

# 캐릭터 삭제 확인
if delete_button and current_character_name:
    if st.button(f"'{current_character_name}' 캐릭터를 정말 삭제하시겠습니까?", key="confirm_delete"):
        del app_data["characters"][current_character_name]
        st.session_state.app_data = app_data
        st.success(f"캐릭터 '{current_character_name}'가 삭제되었습니다.")
        st.rerun()

st.markdown("---") # 구분선

# --- 숙제 현황 섹션 ---
st.header("숙제 현황")

if current_character_name:
    char_data = app_data["characters"][current_character_name]

    # 일일 숙제
    st.subheader("DAILY")
    daily_cols = st.columns(2) # 숙제 이름 / 체크/카운트 컴포넌트
    for i, (task_name, task_meta) in enumerate(DAILY_TASKS_META.items()):
        with daily_cols[0]:
            st.write(task_name)
        with daily_cols[1]:
            if task_meta["type"] == "count":
                current_count = char_data["daily"].get(task_name, {}).get("count", 0)
                new_count = st.number_input(
                    f"횟수 ({task_meta['max']}회)",
                    min_value=0,
                    max_value=task_meta["max"],
                    value=current_count,
                    step=1,
                    key=f"{current_character_name}_daily_{task_name}_count"
                )
                if new_count != current_count:
                    char_data["daily"][task_name] = {"count": new_count}
                    st.session_state.app_data = app_data
                    st.rerun() # 상태 변경 시 UI 업데이트
            elif task_meta["type"] == "check":
                if task_meta.get("shared", False): # 길드 출석
                    is_checked = app_data.get("guild_attendance_checked", False)
                    new_checked = st.checkbox(
                         "완료",
                         value=is_checked,
                         key=f"shared_daily_{task_name}_check"
                    )
                    if new_checked != is_checked:
                        app_data["guild_attendance_checked"] = new_checked
                        # 모든 캐릭터의 길드 출석 상태 업데이트 (UI는 전역 상태를 따라감)
                        for char in app_data["characters"].values():
                            char["daily"][task_name] = {"checked": new_checked}
                        st.session_state.app_data = app_data
                        st.rerun()
                else: # 개별 체크 숙제
                    is_checked = char_data["daily"].get(task_name, {}).get("checked", False)
                    new_checked = st.checkbox(
                        "완료",
                        value=is_checked,
                        key=f"{current_character_name}_daily_{task_name}_check"
                    )
                    if new_checked != is_checked:
                        char_data["daily"][task_name] = {"checked": new_checked}
                        st.session_state.app_data = app_data
                        st.rerun()
            elif task_meta["type"] == "status": # 망령의 탑
                 current_status = char_data["daily"].get(task_name, {}).get("status", "일일")
                 new_status = st.radio(
                      "상태",
                      options=task_meta["options"],
                      index=task_meta["options"].index(current_status),
                      key=f"{current_character_name}_daily_{task_name}_status"
                 )
                 if new_status != current_status:
                     char_data["daily"][task_name] = {"status": new_status}
                     st.session_state.app_data = app_data
                     st.rerun()

    # 주간 숙제
    st.subheader("WEEKLY")
    weekly_cols = st.columns(2)
    for i, (task_name, task_meta) in enumerate(WEEKLY_TASKS_META.items()):
        with weekly_cols[0]:
            st.write(task_name)
        with weekly_cols[1]:
            is_checked = char_data["weekly"].get(task_name, {}).get("checked", False)
            new_checked = st.checkbox(
                "완료",
                value=is_checked,
                key=f"{current_character_name}_weekly_{task_name}_check"
            )
            if new_checked != is_checked:
                char_data["weekly"][task_name] = {"checked": new_checked}
                st.session_state.app_data = app_data
                st.rerun()

else:
    st.info("캐릭터를 추가해주세요.")

st.markdown("---") # 구분선

# --- 푸터 영역 (데이터 관리) ---
# 푸터 영역을 별도 컨테이너로 만들고, 버튼 클릭 시 팝업 DIV를 조건부 렌더링

st.subheader("데이터 관리")

if st.button("데이터 관리 팝업 열기"):
    st.session_state.show_data_management_popup = True

# 팝업 DIV (조건부 렌더링)
if st.session_state.get("show_data_management_popup"):
    # 간단한 DIV 형태로 팝업 효과 (실제 팝업 스타일링은 CSS 필요)
    st.markdown("""
    <style>
    .popup-container {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background-color: white;
        padding: 30px;
        border: 1px solid #ccc;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        z-index: 1000;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="popup-container">', unsafe_allow_html=True)
        st.write("### 데이터 관리 옵션")

        # JSON 다운로드 버튼
        st.markdown(download_json(app_data), unsafe_allow_html=True)

        # JSON 업로드
        uploaded_file = st.file_uploader("JSON 설정 파일 업로드", type="json")
        if uploaded_file is not None:
            try:
                uploaded_data = json.load(uploaded_file)
                st.session_state.app_data = uploaded_data # 세션 상태 업데이트
                st.success("파일이 성공적으로 업로드되었습니다.")
                st.session_state.show_data_management_popup = False # 팝업 닫기
                st.rerun() # UI 새로고침
            except Exception as e:
                st.error(f"파일 업로드 중 오류가 발생했습니다: {e}")

        # 일일 숙제 수동 초기화
        if st.button("일일 숙제 수동 초기화"):
            manual_reset_daily(app_data)
            st.session_state.show_data_management_popup = False # 팝업 닫기
            st.rerun() # UI 새로고침

        # 주간 숙제 수동 초기화
        if st.button("주간 숙제 수동 초기화"):
            manual_reset_weekly(app_data)
            st.session_state.show_data_management_popup = False # 팝업 닫기
            st.rerun() # UI 새로고침

        st.markdown("---")
        if st.button("팝업 닫기", key="close_popup"):
             st.session_state.show_data_management_popup = False
             st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)


