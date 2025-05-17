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

# --- 데이터 로드 함수 (세션 상태 사용) ---
# Streamlit에서는 새로고침 시 상태가 날아가므로, 실제 로컬 스토리지 연동은 JS 필요
# 여기서는 Streamlit 세션 상태를 사용하되, 로컬 스토리지에 저장/로드하는 것처럼 동작하는 척만 합니다.
# 실제 구현에서는 파일 업로드/다운로드 또는 별도의 JS 연동이 필요합니다.
def load_data():
    # 세션 상태에 app_data가 없으면 초기 데이터 생성
    if 'app_data' not in st.session_state:
        st.session_state.app_data = create_initial_data()
        # 실제 로컬 스토리지 로드 로직 (JS 필요) -> 여기서는 생략 또는 파일 업로드 유도
        st.info("데이터가 로드되었습니다. 또는 초기 데이터가 생성되었습니다. 새로고침 시 데이터는 유지되지 않습니다. 데이터 관리를 위해 JSON 파일 다운로드/업로드 기능을 이용해주세요.")
    else:
         # 데이터가 로드된 경우 (새로고침이 아닌 다른 Streamlit 인터랙션으로 인한 재실행)
         pass # 별도 메시지 없음

    # 자동 초기화 체크는 데이터 로드 후에 실행
    check_and_reset_tasks(st.session_state.app_data)


# --- 자동 초기화 로직 ---
def check_and_reset_tasks(data):
    now = datetime.now()
    last_daily_reset_str = data.get("last_daily_reset")
    last_weekly_reset_str = data.get("last_weekly_reset")

    # Parse last reset times, default to datetime.min if not found (initial load case)
    last_daily_reset = datetime.strptime(last_daily_reset_str, "%Y-%m-%d %H:%M:%S") if last_daily_reset_str else datetime.min
    last_weekly_reset = datetime.strptime(last_weekly_reset_str, "%Y-%m-%d %H:%M:%S") if last_weekly_reset_str else datetime.min

    # --- 일일 초기화 체크 ---
    # Calculate today's daily reset time (e.g., today at 06:00:00)
    daily_reset_time_today = datetime.combine(now.date(), datetime.strptime(f"{DAILY_RESET_TIME:02d}:00:00", "%H:%M:%S").time())

    # Reset if current time is >= today's reset time AND last daily reset was before today's reset time
    # This handles the case where the app wasn't run yesterday after reset, but is run today after reset.
    # Also ensures reset doesn't happen multiple times on the same day after 6am.
    if now >= daily_reset_time_today and last_daily_reset < daily_reset_time_today:
        manual_reset_daily(data, auto=True) # 자동 초기화 시 망탑 완료는 스킵
        data["last_daily_reset"] = now.strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.app_data = data # 세션 상태 업데이트
        st.toast("일일 숙제가 자동 초기화되었습니다.") # 사용자에게 알림
        st.rerun() # UI 새로고침

    # --- 주간 초기화 체크 (월요일 오전 6시) ---
    reset_day_weekday = WEEKLY_RESET_DAY # 0 for Monday
    today_date = now.date()

    # Calculate the date of the most recent target reset day (Monday) on or before today's date.
    # If today is Monday (weekday 0) and reset_day is Monday (0), days_since_last_reset_day is 0.
    # If today is Tuesday (weekday 1), days_since_last_reset_day is 1.
    # If today is Sunday (weekday 6), days_since_last_reset_day is 6.
    days_since_last_reset_day = (today_date.weekday() - reset_day_weekday + 7) % 7 # Ensures positive difference

    last_reset_day_date = today_date - timedelta(days=days_since_last_reset_day)

    # Calculate the datetime of this week's reset day at the reset time (e.g., 2025-05-19 06:00:00 if today is May 19th, 2025)
    this_week_reset_datetime = datetime.combine(last_reset_day_date, datetime.strptime(f"{WEEKLY_RESET_TIME:02d}:00:00", "%H:%M:%S").time())

    # Check if current time is on or after this week's reset datetime AND last weekly reset was before this week's reset datetime
    # This checks if we are currently in the weekly cycle that started at this week's Monday 6am,
    # and if the last reset occurred before that start time.
    if now >= this_week_reset_datetime and last_weekly_reset < this_week_reset_datetime:
        manual_reset_weekly(data)
        data["last_weekly_reset"] = now.strftime("%Y-%m-%d %H:%M:%S")
        data["guild_attendance_checked"] = False # 길드 출석도 주간 초기화 시 함께 초기화
        st.session_state.app_data = data # 세션 상태 업데이트
        st.toast("주간 숙제가 자동 초기화되었습니다.") # 사용자에게 알림
        st.rerun() # UI 새로고침


# --- 수동 초기화 로직 ---
def manual_reset_daily(data, auto=False):
    for char_data in data["characters"].values():
        # 각 캐릭터의 일일 숙제 상태를 메타 정보 기반으로 초기화
        for task_name, task_meta in DAILY_TASKS_META.items():
            if task_name == "망령의 탑":
                # 자동 초기화 시에는 '완료' 상태인 망령의 탑은 초기화하지 않음
                if auto and char_data["daily"].get(task_name, {}).get("status") == "완료":
                     continue
                # 그 외 (수동 초기화거나 망탑 상태가 완료가 아니면) '일일'로 초기화
                char_data["daily"][task_name] = {"status": "일일"}
            elif task_meta["type"] == "count":
                char_data["daily"][task_name] = {"count": 0}
            elif task_meta["type"] == "check":
                 # 공유 숙제(길드 출석)는 개별 초기화 대상이 아님 (전역 상태로 관리)
                 if not task_meta.get("shared", False):
                    char_data["daily"][task_name] = {"checked": False}

    # 길드 출석은 수동 초기화 시에만 여기서 전역 초기화
    # 자동 초기화는 일일 초기화 시점(하루 지남)에 이미 전역 상태가 리셋되어야 하므로 여기서 처리 안함
    if not auto:
         data["guild_attendance_checked"] = False

    st.session_state.app_data = data # 세션 상태 업데이트
    if not auto:
        st.success("일일 숙제가 수동 초기화되었습니다.")

def manual_reset_weekly(data):
    for char_data in data["characters"].values():
        # 각 캐릭터의 주간 숙제 상태 초기화
        for task_name in WEEKLY_TASKS_META:
            char_data["weekly"][task_name] = {"checked": False}
    data["guild_attendance_checked"] = False # 길드 출석도 주간 초기화 시 함께 초기화
    st.session_state.app_data = data # 세션 상태 업데이트
    st.success("주간 숙제가 수동 초기화되었습니다.")

# --- JSON 파일 다운로드 ---
def download_json(data):
    json_string = json.dumps(data, indent=4, ensure_ascii=False)
    b64 = base64.b64encode(json_string.encode('utf-8')).decode()
    # data:file/json;base64, 접두사를 사용하여 링크 생성
    href = f'<a href="data:application/json;base64,{b64}" download="mabinogi_tasks_data.json" style="text-decoration:none;"><button style="background-color:#007bff;color:white;border:none;padding:10px 20px;border-radius:5px;cursor:pointer;">⚙️ JSON 파일 다운로드</button></a>'
    return href

# --- Streamlit UI 구현 시작 ---
st.set_page_config(page_title=PROGRAM_TITLE, layout="wide") # 페이지 설정
st.title(PROGRAM_TITLE)

# 데이터 로드 (및 자동 초기화 체크)
load_data()
app_data = st.session_state.app_data

# 초기화 - 캐릭터 관련 상태 변수
if 'adding_character' not in st.session_state:
    st.session_state.adding_character = False
if 'editing_character' not in st.session_state:
    st.session_state.editing_character = False
if 'confirm_delete_char' not in st.session_state:
    st.session_state.confirm_delete_char = None
if 'new_char_name_input' not in st.session_state:
    st.session_state.new_char_name_input = "" # 캐릭터 추가/수정 입력 필드 값 저장
if 'last_selected_char' not in st.session_state:
     st.session_state.last_selected_char = None # 마지막 선택 캐릭터 저장

# --- 캐릭터 관리 섹션 ---
st.header("캐릭터 관리")

# 캐릭터 선택 selectbox
character_list = list(app_data.get("characters", {}).keys()) # characters 키가 없을 경우를 대비
# 마지막 선택 캐릭터가 있다면 그 캐릭터를 기본값으로 설정
last_selected_index = 0
if st.session_state.last_selected_char and st.session_state.last_selected_char in character_list:
    last_selected_index = character_list.index(st.session_state.last_selected_char)
elif character_list:
    # 캐릭터 목록이 있고 마지막 선택 캐릭터가 없거나 목록에 없으면 첫 캐릭터를 기본값으로
    st.session_state.last_selected_char = character_list[0]
else:
     # 캐릭터가 아예 없으면 None
     st.session_state.last_selected_char = None
     last_selected_index = None # index도 None으로 설정

current_character_name = st.selectbox(
    "캐릭터 선택",
    character_list,
    index=last_selected_index,
    key="char_select"
)

# 선택된 캐릭터 이름을 세션 상태에 저장 (selectbox 값이 변경될 때마다 업데이트)
st.session_state.last_selected_char = current_character_name


# 캐릭터 관리 버튼 (한 줄로 배치)
button_cols = st.columns(3) # 3개의 컬럼 생성
with button_cols[0]:
    add_button = st.button("추가", key="add_char_btn")
with button_cols[1]:
    # 수정, 삭제 버튼은 캐릭터가 있을 때만 활성화
    edit_button = st.button("수정", key="edit_char_btn", disabled=current_character_name is None)
with button_cols[2]:
    delete_button = st.button("삭제", key="delete_char_btn", disabled=current_character_name is None)

# 버튼 클릭 시 상태 업데이트 (입력 필드 및 확인 버튼 표시 제어)
if add_button:
    st.session_state.adding_character = True
    st.session_state.editing_character = False
    st.session_state.confirm_delete_char = None # 삭제 확인 상태 초기화
    st.session_state.new_char_name_input = "" # 추가 시 입력 필드 초기화
    st.rerun() # 상태 변경 즉시 반영

if edit_button:
    st.session_state.editing_character = True
    st.session_state.adding_character = False
    st.session_state.confirm_delete_char = None # 삭제 확인 상태 초기화
    st.session_state.new_char_name_input = current_character_name if current_character_name else "" # 수정 시 현재 이름으로 필드 채우기
    st.rerun() # 상태 변경 즉시 반영

# --- 캐릭터 추가 입력 필드 ---
# adding_character 상태가 True일 때만 이 섹션 렌더링
if st.session_state.adding_character:
    st.subheader("캐릭터 추가")
    new_char_name = st.text_input("추가할 캐릭터 이름을 입력하세요", key="add_char_name_input", value=st.session_state.new_char_name_input)
    # 입력 필드 값이 변경될 때마다 세션 상태에 저장 (Enter 키 입력 값도 포함)
    st.session_state.new_char_name_input = new_char_name # 세션 상태에 입력 값 저장

    col_confirm_add, col_cancel_add = st.columns(2)
    with col_confirm_add:
        # '확인' 버튼 클릭 시 추가 로직 실행
        if st.button("확인", key="confirm_add_char"):
            name_to_add = st.session_state.new_char_name_input.strip() # 앞뒤 공백 제거
            if name_to_add and name_to_add not in app_data.get("characters", {}): # 캐릭터 목록에 있는지 확인
                initial_char_data = {
                     "daily": {},
                     "weekly": {}
                }
                 # 숙제 메타 정보를 기반으로 초기 숙제 상태 설정
                for task_name, meta in DAILY_TASKS_META.items():
                     if meta["type"] == "count":
                         initial_char_data["daily"][task_name] = {"count": 0}
                     elif meta["type"] == "check":
                         if not meta.get("shared", False): # 공유 숙제는 개별 초기화 안함
                              initial_char_data["daily"][task_name] = {"checked": False}
                     elif meta["type"] == "status":
                         initial_char_data["daily"][task_name] = {"status": "일일"}

                for task_name, meta in WEEKLY_TASKS_META.items():
                     initial_char_data["weekly"][task_name] = {"checked": False}

                if "characters" not in app_data: # characters 키가 없을 경우 생성
                     app_data["characters"] = {}
                app_data["characters"][name_to_add] = initial_char_data
                st.session_state.app_data = app_data
                st.session_state.last_selected_char = name_to_add # 새로 추가한 캐릭터 선택
                st.success(f"캐릭터 '{name_to_add}'가 추가되었습니다.")
                st.session_state.adding_character = False # 상태 초기화
                st.session_state.new_char_name_input = "" # 입력 필드 초기화
                st.rerun() # UI 새로고침 (selectbox 업데이트 등)
            elif name_to_add in app_data.get("characters", {}):
                st.warning("같은 이름의 캐릭터가 이미 존재합니다.")
            else:
                st.warning("추가할 캐릭터 이름을 입력해주세요.")
    with col_cancel_add:
        # '취소' 버튼 클릭 시 상태 초기화
        if st.button("취소", key="cancel_add_char"):
            st.session_state.adding_character = False # 상태 초기화
            st.session_state.new_char_name_input = "" # 입력 필드 초기화
            st.rerun() # UI 새로고침

# --- 캐릭터 수정 입력 필드 ---
# editing_character 상태가 True이고 현재 선택된 캐릭터가 있을 때만 이 섹션 렌더링
elif st.session_state.editing_character and current_character_name:
    st.subheader(f"'{current_character_name}' 캐릭터 이름 수정")
    new_char_name = st.text_input("변경할 캐릭터 이름을 입력하세요", key="edit_char_name_input", value=st.session_state.new_char_name_input)
    st.session_state.new_char_name_input = new_char_name # 세션 상태에 입력 값 저장

    col_confirm_edit, col_cancel_edit = st.columns(2)
    with col_confirm_edit:
        # '확인' 버튼 클릭 시 수정 로직 실행
        if st.button("확인", key="confirm_edit_char"):
            name_to_edit = st.session_state.new_char_name_input.strip() # 앞뒤 공백 제거
            # 이름이 비어있지 않고, 현재 이름과 다르며, 기존 캐릭터 이름 목록에 없는 경우
            if name_to_edit and name_to_edit != current_character_name and name_to_edit not in app_data.get("characters", {}):
                # 기존 데이터 복사 후 삭제, 새 키로 저장
                app_data["characters"][name_to_edit] = app_data["characters"].pop(current_character_name)
                st.session_state.app_data = app_data
                st.session_state.last_selected_char = name_to_edit # 변경된 캐릭터 선택
                st.success(f"캐릭터 이름이 '{current_character_name}'에서 '{name_to_edit}'으로 변경되었습니다.")
                st.session_state.editing_character = False # 상태 초기화
                st.session_state.new_char_name_input = "" # 입력 필드 초기화
                st.rerun() # UI 새로고침
            elif name_to_edit == current_character_name:
                st.info("변경할 이름이 이전과 같습니다.")
            elif name_to_edit in app_data.get("characters", {}):
                st.warning("같은 이름의 캐릭터가 이미 존재합니다.")
            else:
                st.warning("변경할 이름을 입력해주세요.")
    with col_cancel_edit:
        # '취소' 버튼 클릭 시 상태 초기화
        if st.button("취소", key="cancel_edit_char"):
            st.session_state.editing_character = False # 상태 초기화
            st.session_state.new_char_name_input = "" # 입력 필드 초기화
            st.rerun() # UI 새로고침

# --- 캐릭터 삭제 확인 프롬프트 ---
# confirm_delete_char 상태가 True이고, 현재 선택된 캐릭터가 삭제 대상일 경우
if st.session_state.get('confirm_delete_char') and current_character_name and st.session_state.confirm_delete_char == current_character_name:
    st.subheader(f"'{current_character_name}' 캐릭터를 정말 삭제하시겠습니까?")
    col_confirm_delete, col_cancel_delete = st.columns(2)
    with col_confirm_delete:
        # '예' 버튼 클릭 시 삭제 로직 실행
        if st.button("예, 삭제합니다", key="confirm_delete_char_btn_yes"):
            del app_data["characters"][current_character_name]
            st.session_state.app_data = app_data
            st.session_state.last_selected_char = None # 삭제 후 선택 캐릭터 초기화
            st.success(f"캐릭터 '{current_character_name}'가 삭제되었습니다.")
            st.session_state.confirm_delete_char = None # 상태 초기화
            st.rerun() # UI 새로고침 (selectbox 업데이트)

    with col_cancel_delete:
        # '아니오' 버튼 클릭 시 상태 초기화
        if st.button("아니오, 취소합니다", key="confirm_delete_char_btn_no"):
             st.session_state.confirm_delete_char = None # 상태 초기화
             st.rerun() # UI 새로고침

st.markdown("---") # 구분선

# --- 숙제 현황 섹션 ---
st.header("숙제 현황")

# 캐릭터가 선택되었을 때만 숙제 현황 표시
if current_character_name and current_character_name in app_data.get("characters", {}):
    char_data = app_data["characters"][current_character_name]

    # 일일 숙제
    st.subheader("DAILY")
    # UI 이미지를 참고하여 레이아웃 구성
    # 예: 2개 컬럼 (숙제 이름 | 완료 체크/횟수 입력)
    daily_cols = st.columns(2)
    for i, (task_name, task_meta) in enumerate(DAILY_TASKS_META.items()):
        # Streamlit 컴포넌트는 위에서 아래로 순서대로 렌더링되므로, 각 숙제 항목을 하나의 단위로 처리
        # 각 숙제 이름과 입력 컴포넌트를 같은 행에 배치하기 위해 컬럼 사용
        with daily_cols[0]:
            st.write(task_name)
        with daily_cols[1]:
            # 숙제 타입에 따른 컴포넌트 렌더링 및 상태 관리
            if task_meta["type"] == "count":
                # 횟수형 숙제 (불길한 소환의 결계, 검은 구멍)
                current_count = char_data["daily"].get(task_name, {}).get("count", 0)
                new_count = st.number_input(
                    "횟수", # 라벨을 더 간결하게 수정
                    min_value=0,
                    max_value=task_meta["max"],
                    value=current_count,
                    step=1,
                    key=f"{current_character_name}_daily_{task_name}_count",
                    label_visibility="collapsed" # 라벨 숨김 (UI 이미지 참고)
                ) #+ 0 # number_input 버그 회피를 위한 +0 (최신 버전에서는 불필요할 수 있음)
                # 값이 변경되었으면 상태 업데이트 및 새로고침
                if int(new_count) != current_count: # number_input은 float를 반환할 수 있으므로 int로 형변환
                    char_data["daily"][task_name] = {"count": int(new_count)} # 정수로 저장
                    st.session_state.app_data = app_data
                    st.rerun()
            elif task_meta["type"] == "check":
                # 체크형 숙제 (요일던전, 아르바이트[오후], 길드 출석)
                if task_meta.get("shared", False): # 길드 출석 (공유)
                    is_checked = app_data.get("guild_attendance_checked", False)
                    new_checked = st.checkbox(
                         "완료", # 라벨
                         value=is_checked,
                         key=f"shared_daily_{task_name}_check"
                    )
                    # 상태 변경 시 전역 상태 업데이트 및 새로고침
                    if new_checked != is_checked:
                        app_data["guild_attendance_checked"] = new_checked
                         # 모든 캐릭터 데이터의 길드 출석 상태를 동기화 (UI는 전역 상태를 따라감)
                        for char_data_sync in app_data["characters"].values():
                            char_data_sync["daily"][task_name] = {"checked": new_checked}
                        st.session_state.app_data = app_data
                        st.rerun()
                else: # 개별 체크 숙제 (요일던전, 아르바이트[오후])
                    is_checked = char_data["daily"].get(task_name, {}).get("checked", False)
                    new_checked = st.checkbox(
                        "완료", # 라벨
                        value=is_checked,
                        key=f"{current_character_name}_daily_{task_name}_check"
                    )
                    # 상태 변경 시 캐릭터 데이터 업데이트 및 새로고침
                    if new_checked != is_checked:
                        char_data["daily"][task_name] = {"checked": new_checked}
                        st.session_state.app_data = app_data
                        st.rerun()
            elif task_meta["type"] == "status": # 상태형 숙제 (망령의 탑)
                 current_status = char_data["daily"].get(task_name, {}).get("status", "일일")
                 # 라디오 버튼 또는 selectbox 사용 가능, 여기서는 라디오 버튼 사용
                 new_status = st.radio(
                      "상태", # 라벨
                      options=task_meta["options"],
                      index=task_meta["options"].index(current_status) if current_status in task_meta["options"] else 0, # 현재 상태 인덱스 찾기
                      key=f"{current_character_name}_daily_{task_name}_status",
                      horizontal=True, # 가로로 배치
                      label_visibility="collapsed" # 라벨 숨김 (UI 이미지 참고)
                 )
                 # 상태 변경 시 캐릭터 데이터 업데이트 및 새로고침
                 if new_status != current_status:
                     char_data["daily"][task_name] = {"status": new_status}
                     st.session_state.app_data = app_data
                     st.rerun()

    # 주간 숙제
    st.subheader("WEEKLY")
    # UI 이미지를 참고하여 레이아웃 구성
    weekly_cols = st.columns(2) # 2개의 컬럼 (숙제 이름 | 완료 체크)
    for i, (task_name, task_meta) in enumerate(WEEKLY_TASKS_META.items()):
        with weekly_cols[0]:
            st.write(task_name)
        with weekly_cols[1]:
            # 체크형 숙제 (주간 숙제 대부분)
            is_checked = char_data["weekly"].get(task_name, {}).get("checked", False)
            new_checked = st.checkbox(
                "완료", # 라벨
                value=is_checked,
                key=f"{current_character_name}_weekly_{task_name}_check"
            )
            # 상태 변경 시 캐릭터 데이터 업데이트 및 새로고침
            if new_checked != is_checked:
                char_data["weekly"][task_name] = {"checked": new_checked}
                st.session_state.app_data = app_data
                st.rerun()

else:
    st.info("캐릭터를 추가하여 숙제를 관리해보세요!")


st.markdown("---") # 구분선

# --- 데이터 관리 섹션 ---
st.header("데이터 관리")

# '데이터 관리' 팝업 상태 변수
if 'show_data_management_popup' not in st.session_state:
    st.session_state.show_data_management_popup = False

# '데이터 관리' 버튼 클릭 시 팝업 상태 토글
if st.button("데이터 관리", key="open_data_management_popup"):
    st.session_state.show_data_management_popup = not st.session_state.show_data_management_popup
    # st.rerun() # 상태 변경 즉시 반영 (필요에 따라 활성화)

# 팝업 DIV (조건부 렌더링)
# 팝업창 스타일을 적용한 DIV를 마크다운으로 삽입
if st.session_state.get("show_data_management_popup"):
    st.markdown("""
    <style>
    .data-management-popup {
        position: fixed; /* 화면에 고정 */
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background-color: white;
        padding: 30px;
        border: 1px solid #ccc;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        z-index: 1000; /* 다른 요소 위로 표시 */
        border-radius: 10px; /* 둥근 모서리 */
        max-width: 90%; /* 최대 너비 */
        min-width: 300px; /* 최소 너비 */
        display: flex;
        flex-direction: column;
        gap: 15px; /* 요소 간 간격 */
    }
    </style>
    """, unsafe_allow_html=True)

    # 팝업 내용 컨테이너
    with st.container():
        st.markdown('<div class="data-management-popup">', unsafe_allow_html=True)
        st.write("### 데이터 관리 옵션")
        st.write("⚠️ **참고:** 프로그램 새로고침 시 데이터는 유지되지 않습니다. 데이터 유실 방지를 위해 JSON 파일 다운로드/업로드 기능을 사용해주세요.")


        # JSON 다운로드 버튼 (HTML 마크다운 사용)
        st.markdown(download_json(app_data), unsafe_allow_html=True)


        # JSON 업로드
        st.write("JSON 설정 파일 업로드:")
        uploaded_file = st.file_uploader("파일 선택", type="json", key="upload_json_file", label_visibility="collapsed")
        if uploaded_file is not None:
            try:
                # 파일 내용을 읽어서 JSON 파싱
                file_content = uploaded_file.getvalue().decode("utf-8")
                uploaded_data = json.loads(file_content)
                # TODO: 업로드된 데이터의 유효성 검사 로직 추가 필요 (프로그램 데이터 구조와 맞는지 등)

                st.session_state.app_data = uploaded_data # 세션 상태 업데이트
                # 업로드 후 선택된 캐릭터 초기화 방지 또는 유효성 검사 후 선택 등 필요
                # 여기서는 간단히 첫 캐릭터 선택 또는 None으로 설정
                char_keys = list(uploaded_data.get("characters", {}).keys())
                if char_keys:
                     st.session_state.last_selected_char = char_keys[0]
                else:
                     st.session_state.last_selected_char = None

                st.success("파일이 성공적으로 업로드되었습니다. 변경사항이 적용되었습니다.")
                st.session_state.show_data_management_popup = False # 팝업 닫기
                st.rerun() # UI 새로고침
            except Exception as e:
                st.error(f"파일 업로드 중 오류가 발생했습니다. 파일 형식을 확인해주세요: {e}")
                # 오류 발생 시에도 팝업은 열려 있게 유지

        st.markdown("---") # 구분선

        # 일일 숙제 수동 초기화
        if st.button("일일 숙제 수동 초기화", key="manual_reset_daily_btn"):
            manual_reset_daily(app_data, auto=False) # 수동 초기화임을 명시
            st.session_state.show_data_management_popup = False # 팝업 닫기
            st.rerun() # UI 새로고침

        # 주간 숙제 수동 초기화
        if st.button("주간 숙제 수동 초기화", key="manual_reset_weekly_btn"):
            manual_reset_weekly(app_data)
            st.session_state.show_data_management_popup = False # 팝업 닫기
            st.rerun() # UI 새로고침

        st.markdown("---")
        # 팝업 닫기 버튼
        # col_close_popup = st.columns(1)
        # with col_close_popup[0]: # 컬럼 안에 버튼 배치 (중앙 정렬 등에 사용)
        if st.button("닫기", key="close_data_management_popup"):
             st.session_state.show_data_management_popup = False
             st.rerun() # 팝업 숨김 즉시 반영

        st.markdown('</div>', unsafe_allow_html=True)

