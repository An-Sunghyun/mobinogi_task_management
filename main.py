import streamlit as st
import json
from datetime import datetime, time, date, timedelta
import pytz # 시간대 처리를 위해 필요
import os # 파일 처리

# --- 버전 관리 ---
APP_VERSION = "0.01"
APP_TITLE = f"Mobinog Task Management V{APP_VERSION}"

# 시간대 설정 (한국 시간)
KST = pytz.timezone('Asia/Seoul')

# 데이터 저장 파일 경로 (서버 기준)
DATA_FILE = "mabinogi_tasks_data.json"

# --- 상수 정의 ---
# 초기 데이터 구조 기본값
DEFAULT_DATA = {
    "characters": [],
    "shared_tasks": {
        "길드 출석": 0 # 0: 미완료, 1: 완료
    },
    "last_reset_timestamps": {
        "daily": datetime.now(KST).isoformat(),
        "weekly": datetime.now(KST).isoformat()
    }
}

# 일일 숙제 목록 및 초기 횟수/상태 템플릿
DAILY_TASK_TEMPLATE = {
    "불길한 소환의 결계": 2,
    "검은 구멍": 3,
    "요일던전": 1,
    "아르바이트[오후]": 1,
    "길드 출석": 0, # 이 값은 shared_tasks와 동기화
    "망령의 탑": {"daily": 0, "complete": False} # daily: 0 미완료, 1 완료
}

# 주간 숙제 목록 및 초기 횟수 템플릿
WEEKLY_TASK_TEMPLATE = {
    "어비스 - 가라앉은 유적": 1,
    "어비스 - 무너진 제단": 1,
    "어비스 - 파멸의 전당": 1,
    "레이드 - 글라스기브넨": 1,
    "필드보스 - 페리": 1,
    "필드보스 - 크라브네흐": 1,
    "필드보스 - 크라마": 1,
    "필드보스 재화 교환": 1,
    "어비스 보상 수령": 1
}

# --- 헬퍼 함수 ---

def save_data_to_server_file(data):
    """현재 데이터를 서버 파일에 저장"""
    try:
        # 저장 시점의 타임스탬프 업데이트
        # Ensure last_reset_timestamps exists and is a dict
        if not isinstance(data.get("last_reset_timestamps"), dict):
            data["last_reset_timestamps"] = {}
        data["last_reset_timestamps"]["daily"] = datetime.now(KST).isoformat()
        data["last_reset_timestamps"]["weekly"] = datetime.now(KST).isoformat()

        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        # st.sidebar.info("데이터 자동 저장됨") # Optional feedback - can be noisy
    except Exception as e:
        st.sidebar.error(f"데이터 자동 저장 실패: {e}") # Indicate save failure


def load_data(uploaded_file=None):
    """데이터 로드 및 자동 초기화 처리"""
    data = None
    loaded_successfully = False # Track if data was loaded from file or upload

    if 'data' in st.session_state and st.session_state.data is not None:
        # 1. Data already in session state (e.g., after rerun), use it
        data = st.session_state.data
        loaded_successfully = True
    elif uploaded_file is not None:
        # 2. Uploaded file takes priority if no valid session state data
        try:
            uploaded_data = json.load(uploaded_file)
            # Validate minimum structure after upload
            if not isinstance(uploaded_data, dict) or "characters" not in uploaded_data or "shared_tasks" not in uploaded_data or "last_reset_timestamps" not in uploaded_data:
                 st.warning("업로드된 파일 형식이 올바르지 않습니다. 기본 데이터로 로드합니다.")
                 data = DEFAULT_DATA.copy()
            else:
                data = uploaded_data
                st.success("파일이 성공적으로 로드되었습니다.")
                loaded_successfully = True
        except Exception as e:
            st.error(f"파일 로드 중 오류 발생: {e}")
            data = DEFAULT_DATA.copy() # Error on upload, revert to default
    else:
        # 3. No session state data, no upload -> try loading from server file
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    file_data = json.load(f)
                # Validate minimum structure after loading server file
                if not isinstance(file_data, dict) or "characters" not in file_data or "shared_tasks" not in file_data or "last_reset_timestamps" not in file_data:
                     st.warning(f"'{DATA_FILE}' 파일 형식이 올바르지 않습니다. 기본 데이터로 로드합니다.")
                     data = DEFAULT_DATA.copy()
                else:
                     data = file_data
                     st.info(f"'{DATA_FILE}' 파일에서 데이터를 로드했습니다.")
                     loaded_successfully = True
            except Exception as e:
                st.warning(f"'{DATA_FILE}' 파일 로드 중 오류 발생: {e}. 기본 데이터로 시작합니다.")
                data = DEFAULT_DATA.copy()
        else:
            # 4. No file exists, load default data
            st.info(f"'{DATA_FILE}' 파일이 없습니다. 새 데이터로 시작합니다.")
            data = DEFAULT_DATA.copy()

    # Ensure session state is initialized with loaded/default data if it wasn't already
    if 'data' not in st.session_state or st.session_state.data is None or not loaded_successfully:
         st.session_state.data = data


    # Perform auto-reset based on the data that was just loaded/set to session state
    check_and_perform_auto_reset()

    # Save data to server file after initial load if it came from file, upload, or default
    # This ensures the file exists and contains the current state (including potential auto-resets)
    # Only save if data was successfully loaded or initialized as default
    if loaded_successfully or not os.path.exists(DATA_FILE):
         save_data_to_server_file(st.session_state.data)


def _set_time_to_datetime(dt, hour=6, minute=0):
    """Sets the time of a datetime object to a specific hour and minute, preserving date and timezone."""
    return dt.replace(hour=hour, minute=minute, second=0, microsecond=0)


def perform_daily_reset(data):
    """일일 숙제 초기화 로직 (망령의 탑 완료 제외)"""
    st.info("일일 숙제 초기화 중...")
    # 안전하게 데이터 구조에 접근
    characters = data.get("characters", [])
    shared_tasks = data.get("shared_tasks", {})

    for char in characters:
        # daily_tasks 항목이 없거나 None이면 생성 및 기본 구조 확인
        if not isinstance(char.get("daily_tasks"), dict):
            char["daily_tasks"] = {}

        # 템플릿을 기반으로 초기화
        for task, initial_state in DAILY_TASK_TEMPLATE.items():
            if task == "길드 출석":
                # 길드 출석은 공유 상태를 따름
                char["daily_tasks"][task] = shared_tasks.get("길드 출석", 0)
            elif task == "망령의 탑":
                 # 망령의 탑 초기화: daily 상태만 초기화, complete가 False일 경우에만
                 # get으로 안전하게 접근하고 기본값 처리
                 mt_state = char["daily_tasks"].get("망령의 탑", {"daily": 0, "complete": False})
                 if not mt_state.get("complete", False):
                     # 망령의 탑 항목이 없거나 딕셔너리가 아니면 새로 추가하며 초기화
                     if not isinstance(char["daily_tasks"].get("망령의 탑"), dict):
                          char["daily_tasks"]["망령의 탑"] = {"daily": 0, "complete": False}
                     else:
                         char["daily_tasks"]["망령의 탑"]["daily"] = 0 # 일일 상태 초기화
            else:
                 # 해당하는 일일 숙제 항목이 없으면 새로 추가하거나 초기화
                 char["daily_tasks"][task] = initial_state

    # Initial timestamp update and save happens in check_and_perform_auto_reset or _render_data_management
    st.success("일일 숙제 초기화 완료.")


def perform_weekly_reset(data):
    """주간 숙제 초기화 로직"""
    st.info("주간 숙제 초기화 중...")
    # 안전하게 데이터 구조에 접근
    characters = data.get("characters", [])

    for char in characters:
        # weekly_tasks 항목이 없거나 None이면 생성 및 기본 구조 확인
        if not isinstance(char.get("weekly_tasks"), dict):
            char["weekly_tasks"] = {}

        # 템플릿을 기반으로 초기화
        for task, initial_state in WEEKLY_TASK_TEMPLATE.items():
             # 해당하는 주간 숙제 항목이 없으면 새로 추가하거나 초기화
             char["weekly_tasks"][task] = initial_state

        # 망령의 탑 complete 상태 초기화 (주간 초기화 시에만 해당)
        # 망령의 탑 항목이 있는지 확인 후 초기화
        if isinstance(char.get("daily_tasks"), dict) and isinstance(char["daily_tasks"].get("망령의 탑"), dict):
            char["daily_tasks"]["망령의 탑"]["complete"] = False

    # Initial timestamp update and save happens in check_and_perform_auto_reset or _render_data_management
    st.success("주간 숙제 초기화 완료.")


def check_and_perform_auto_reset():
    """자동 초기화 필요 시 수행"""
    data = st.session_state.data
    now = datetime.now(KST)

    # 마지막 초기화 시간 가져오기 (없거나 유효하지 않으면 아주 과거 시간으로 설정)
    last_daily_reset = datetime.min.replace(tzinfo=KST)
    last_reset_ts = data.get("last_reset_timestamps", {}) # 안전하게 접근
    last_daily_reset_str = last_reset_ts.get("daily")
    if last_daily_reset_str:
        try:
            last_daily_reset = datetime.fromisoformat(last_daily_reset_str).astimezone(KST)
        except (ValueError, TypeError):
            pass # 유효하지 않으면 기본값 유지

    last_weekly_reset = datetime.min.replace(tzinfo=KST)
    last_weekly_reset_str = last_reset_ts.get("weekly")
    if last_weekly_reset_str:
        try:
            last_weekly_reset = datetime.fromisoformat(last_weekly_reset_str).astimezone(KST)
        except (ValueError, TypeError):
             pass # 유효하지 않으면 기본값 유지

    # Daily reset time: Today at 6:00 AM KST. If 'now' is before 6 AM KST, it's yesterday's 6 AM.
    daily_reset_time_today = _set_time_to_datetime(now, hour=6)
    if now < daily_reset_time_today:
         daily_reset_time = daily_reset_time_today - timedelta(days=1)
    else:
         daily_reset_time = daily_reset_time_today

    # 일일 초기화 필요 여부 판단
    # 마지막 초기화 시간이 일일 초기화 기준 시간보다 이전이면 초기화 필요
    if last_daily_reset < daily_reset_time:
        perform_daily_reset(data)
        # Update timestamp in data object and save before rerun
        if not isinstance(data.get("last_reset_timestamps"), dict): data["last_reset_timestamps"] = {}
        data["last_reset_timestamps"]["daily"] = now.isoformat()
        save_data_to_server_file(data) # Save updated data including new timestamp
        st.rerun() # Trigger UI update


    # Weekly reset time: This Monday at 6:00 AM KST. If 'now' is before Mon 6 AM KST, it's last Monday 6 AM.
    today_weekday = now.weekday() # Monday is 0, Sunday is 6
    # Find this Monday's date
    this_monday_date = now.date() - timedelta(days=today_weekday)
    # Datetime for this Monday at 6:00 AM
    this_monday_reset_time = datetime.combine(this_monday_date, time(6, 0), tzinfo=KST).astimezone(KST) # Ensure KST timezone

    # If current time is before this Monday 6 AM, the reset happened last Monday
    if now < this_monday_reset_time:
        weekly_reset_time = this_monday_reset_time - timedelta(days=7)
    else:
        weekly_reset_time = this_monday_reset_time


    # 주간 초기화 필요 여부 판단
    # 마지막 초기화 시간이 주간 초기화 기준 시간보다 이전이면 초기화 필요
    if last_weekly_reset < weekly_reset_time:
        perform_weekly_reset(data)
        # Update timestamp and save before rerun
        if not isinstance(data.get("last_reset_timestamps"), dict): data["last_reset_timestamps"] = {}
        data["last_reset_timestamps"]["weekly"] = now.isoformat()
        save_data_to_server_file(data) # Save updated data including new timestamp
        st.rerun() # Trigger UI update


# --- UI 렌더링 함수 ---

def _render_character_management(data):
    """캐릭터 관리 섹션 렌더링"""
    st.header("캐릭터 관리")
    characters = data.get("characters", []) # 안전하게 데이터 접근

    # 유효한 캐릭터 이름 목록 생성
    valid_char_names = [c.get("name") for c in characters if isinstance(c, dict) and c.get("name")]
    if not valid_char_names:
         valid_char_names = ["캐릭터 없음"] # 캐릭터가 없을 때 selectbox에 표시될 기본 텍스트

    # 현재 선택된 캐릭터 이름 가져오기 (세션 상태 또는 유효한 첫 캐릭터 이름)
    # valid_char_names가 비어있지 않으면 첫 번째 이름으로 기본값 설정
    if 'selected_char' not in st.session_state or st.session_state.selected_char not in [c.get("name") for c in characters if isinstance(c, dict) and c.get("name")]:
        st.session_state.selected_char = valid_char_names[0] if valid_char_names and valid_char_names[0] != "캐릭터 없음" else None # "캐릭터 없음"일 경우 None

    # --- 캐릭터 선택 selectbox 및 관리 버튼 배치 ---
    col_select, col_btn1, col_btn2, col_btn3 = st.columns([3, 1, 1, 1]) # 컬럼 비율 조정

    with col_select:
        # 캐릭터 선택 selectbox
        # characters 리스트가 비어있으면 기본값 ('캐릭터 없음')으로 selectbox 표시
        selected_char_name = st.selectbox(
            "캐릭터 선택:",
            options=valid_char_names,
            key="selected_char_selectbox",
            # 현재 선택된 이름이 목록에 있으면 해당 인덱스 사용, 없으면 0 사용
            index=valid_char_names.index(st.session_state.selected_char) if st.session_state.selected_char in valid_char_names else 0,
            disabled=not [c for c in characters if isinstance(c, dict) and c.get("name")] # 캐릭터 없으면 비활성화
        )
        # selectbox 선택 결과를 session_state에 저장
        if selected_char_name != "캐릭터 없음": # "캐릭터 없음"은 실제 캐릭터가 아니므로 저장하지 않음
             st.session_state.selected_char = selected_char_name
        elif characters: # 캐릭터는 있는데 selectbox에 "캐릭터 없음"이 선택된 이상한 상태일 경우
             st.session_state.selected_char = characters[0].get("name") # 첫 캐릭터로 강제 설정
             st.rerun() # Force rerun to correct selectbox


    with col_btn1:
        st.write(" ") # Add spacing to align buttons
        # 캐릭터 추가 버튼 - 클릭 시 입력 UI 표시 플래그 설정
        if st.button("추가", key="btn_add_char"):
            st.session_state.show_add_char_form = True
            st.session_state.show_modify_char_form = False # 다른 폼 닫기
            st.rerun() # 상태 변경 즉시 반영

    with col_btn2:
        st.write(" ") # Add spacing
        # 캐릭터 변경 버튼 - 클릭 시 입력 UI 표시 플래그 설정
        if st.button("변경", key="btn_modify_char", disabled=not characters): # 캐릭터 없으면 비활성화
            st.session_state.show_modify_char_form = True
            st.session_state.show_add_char_form = False # 다른 폼 닫기
            st.rerun() # 상태 변경 즉시 반영

    with col_btn3:
        st.write(" ") # Add spacing
        # 캐릭터 삭제 버튼 - 클릭 시 삭제 로직 실행
        if st.button("삭제", key="btn_delete_char", disabled=not characters): # 캐릭터 없으면 비활성화
            selected_char_name_to_delete = st.session_state.get("selected_char")
            if selected_char_name_to_delete and selected_char_name_to_delete in [c.get("name") for c in characters if isinstance(c, dict) and c.get("name")]:
                # 실제로 삭제 - 필터링 후 리스트 재할당
                original_char_count = len(characters)
                # 유효한 캐릭터 중 선택된 이름과 다른 캐릭터만 남김
                data["characters"] = [c for c in characters if isinstance(c, dict) and c.get("name") != selected_char_name_to_delete]

                if len(data["characters"]) < original_char_count: # 실제로 삭제되었는지 확인
                     save_data_to_server_file(data) # 데이터 변경 후 저장
                     st.success(f"'{selected_char_name_to_delete}' 캐릭터가 삭제되었습니다.")
                     # 삭제 후 선택될 캐릭터 업데이트
                     if data["characters"]:
                         st.session_state.selected_char = data["characters"][0].get("name")
                     else:
                         st.session_state.selected_char = None # 남은 캐릭터 없음
                     st.rerun() # UI 구조 변경 반영
                else:
                     st.warning("캐릭터 삭제에 실패했습니다.") # 선택된 이름의 캐릭터를 찾지 못한 경우 등
            else:
                 st.info("삭제할 캐릭터를 선택해주세요.") # 이미 캐릭터가 없거나 선택된 캐릭터가 유효하지 않은 경우


    # --- 캐릭터 추가 입력 UI (조건부 표시) ---
    if st.session_state.get("show_add_char_form"):
        with st.container(border=True): # 입력 폼을 컨테이너로 감싸서 시각적으로 구분
            st.markdown("#### 새 캐릭터 추가")
            with st.form("add_character_input_form", clear_on_submit=True):
                new_char_name_input = st.text_input("캐릭터 이름을 입력하세요:", key="add_char_name_input")
                col_add_form1, col_add_form2 = st.columns(2)
                with col_add_form1:
                    submit_add_button = st.form_submit_button("추가하기")
                with col_add_form2:
                    cancel_add_button = st.form_submit_button("취소")

                if submit_add_button:
                    if new_char_name_input:
                        valid_char_names = [c.get("name") for c in characters if isinstance(c, dict) and c.get("name")]
                        if new_char_name_input not in valid_char_names:
                            new_character = {
                                "name": new_char_name_input,
                                "daily_tasks": DAILY_TASK_TEMPLATE.copy(),
                                "weekly_tasks": WEEKLY_TASK_TEMPLATE.copy()
                            }
                            new_character["daily_tasks"]["길드 출석"] = data.get("shared_tasks", {}).get("길드 출석", 0)
                            characters.append(new_character)
                            save_data_to_server_file(data)
                            st.success(f"'{new_char_name_input}' 캐릭터가 추가되었습니다.")
                            st.session_state.selected_char = new_char_name_input
                            st.session_state.show_add_char_form = False # 폼 숨김
                            st.rerun()
                        else:
                            st.warning("이미 존재하는 이름입니다.")
                    else:
                        st.warning("캐릭터 이름을 입력해주세요.")
                elif cancel_add_button:
                     st.session_state.show_add_char_form = False # 폼 숨김
                     st.rerun()


    # --- 캐릭터 변경 입력 UI (조건부 표시) ---
    if st.session_state.get("show_modify_char_form"):
         selected_char_name_to_modify = st.session_state.get("selected_char")
         # 변경 대상 캐릭터가 유효한 경우에만 폼 표시
         if selected_char_name_to_modify and selected_char_name_to_modify in [c.get("name") for c in characters if isinstance(c, dict) and c.get("name")]:
              with st.container(border=True): # 입력 폼을 컨테이너로 감싸서 시각적으로 구분
                   st.markdown(f"#### '{selected_char_name_to_modify}' 이름 변경")
                   with st.form("modify_character_input_form", clear_on_submit=False): # 변경 중에는 clear 안함
                        new_char_name_input = st.text_input("새 이름을 입력하세요:", value=selected_char_name_to_modify, key="modify_char_name_input")
                        col_modify_form1, col_modify_form2 = st.columns(2)
                        with col_modify_form1:
                             submit_modify_button = st.form_submit_button("변경하기")
                        with col_modify_form2:
                             cancel_modify_button = st.form_submit_button("취소")


                        if submit_modify_button:
                             if new_char_name_input and new_char_name_input != selected_char_name_to_modify:
                                # 다른 캐릭터 이름과 중복 확인
                                other_char_names = [c.get("name") for c in characters if isinstance(c, dict) and c.get("name") and c.get("name") != selected_char_name_to_modify]
                                if new_char_name_input not in other_char_names:
                                   # 해당 캐릭터 찾아서 이름 변경
                                   for char in characters:
                                       if isinstance(char, dict) and char.get("name") == selected_char_name_to_modify:
                                           char["name"] = new_char_name_input
                                           save_data_to_server_file(data)
                                           st.success(f"'{selected_char_name_to_modify}' 캐릭터 이름이 '{new_char_name_input}'(으)로 변경되었습니다.")
                                           st.session_state.selected_char = new_char_name_input
                                           st.session_state.show_modify_char_form = False # 폼 숨김
                                           st.rerun()
                                           break # 찾았으면 루프 중단
                                else:
                                    st.warning("이미 존재하는 이름입니다.")
                             elif new_char_name_input == selected_char_name_to_modify:
                                 st.info("이름 변경이 없습니다.")
                             else:
                                 st.warning("새 이름을 입력해주세요.")
                        elif cancel_modify_button:
                             st.session_state.show_modify_char_form = False # 폼 숨김
                             st.rerun()
         else: # 변경 대상 캐릭터가 유효하지 않으면 폼 표시 플래그 초기화
              st.session_state.show_modify_char_form = False


# --- UI 렌더링 함수 ---

def _render_tasks(data):
    """숙제 목록 섹션 렌더링 (DAILY, WEEKLY)"""
    characters = data.get("characters", [])
    shared_tasks = data.get("shared_tasks", {}) # 안전하게 데이터 접근

    # 유효한 캐릭터 이름 목록 생성 (selectbox 렌더링 시 이미 수행됨)
    valid_char_names = [c.get("name") for c in characters if isinstance(c, dict) and c.get("name") is not None]

    # 캐릭터 목록이 비어있거나 선택된 캐릭터가 유효하지 않으면 숙제 목록을 표시하지 않음
    selected_char_name = st.session_state.get("selected_char")
    if not characters or selected_char_name not in valid_char_names:
         # 캐릭터 관리 섹션에서 이미 메시지 및 구분선 처리됨
         return # 함수 종료

    # 선택된 캐릭터 데이터 찾기
    selected_char_data = next((c for c in characters if isinstance(c, dict) and c.get("name") == selected_char_name), None)

    if selected_char_data:
        # --- DAILY ---
        st.header("DAILY")
        # --- 구분선 추가: DAILY 헤더와 숙제 목록 사이 ---
        st.markdown("---")

        daily_tasks = selected_char_data.get("daily_tasks", {})
        if not isinstance(daily_tasks, dict): # dict 형태가 아니면 빈 딕셔너리로 초기화
            daily_tasks = {}
            selected_char_data["daily_tasks"] = daily_tasks # 데이터에 반영

        # 길드 출석 (공용) - 모든 캐릭터의 상태 동기화
        current_shared_guild_status = shared_tasks.get("길드 출석", 0)
        shared_guild_checked = st.checkbox(
            "길드 출석 (모든 캐릭터 공유)",
            value=current_shared_guild_status == 1,
            key=f"shared_guild_checkbox" # 공유 상태는 고유 키 사용
        )
        new_shared_guild_status = 1 if shared_guild_checked else 0
        # 값이 변경되었을 때만 업데이트 및 동기화
        if data.get("shared_tasks", {}).get("길드 출석", 0) != new_shared_guild_status:
             if "shared_tasks" not in data or data["shared_tasks"] is None:
                  data["shared_tasks"] = {} # shared_tasks 항목 없으면 생성
             data["shared_tasks"]["길드 출석"] = new_shared_guild_status
             # 모든 캐릭터의 길드 출석 상태를 공유 상태로 동기화
             for char in characters:
                  if isinstance(char, dict) and "daily_tasks" in char and isinstance(char["daily_tasks"], dict): # daily_tasks 항목이 있는 유효한 캐릭터인 경우에만 업데이트
                     char["daily_tasks"]["길드 출석"] = new_shared_guild_status
             save_data_to_server_file(data) # 데이터 변경 후 저장
             st.rerun() # 공유 상태 변경 시 즉시 반영


        # 일일 숙제 목록 표시 (DAILY_TASK_TEMPLATE 기준으로 표시)
        for task, template_state in DAILY_TASK_TEMPLATE.items():
            if task == "길드 출석":
                continue # 이미 위에서 처리함

            # 현재 캐릭터 데이터에서 해당 숙제 상태 가져오기 (없으면 템플릿 기본값)
            current_task_state = daily_tasks.get(task, template_state)

            if task == "망령의 탑":
                # 망령의 탑은 일일/완료 두 가지 상태 관리
                mt_state = current_task_state if isinstance(current_task_state, dict) else {"daily": 0, "complete": False}
                daily_done = mt_state.get("daily", 0) == 1
                complete_done = mt_state.get("complete", False)

                st.markdown(f"**{task}:**")
                col_mt1, col_mt2 = st.columns(2)
                with col_mt1:
                    daily_checked = st.checkbox(
                        f"일일 완료",
                        value=daily_done,
                        key=f"{selected_char_name}_{task}_daily_checkbox"
                    )
                    if not isinstance(daily_tasks.get(task), dict): daily_tasks[task] = {"daily": 0, "complete": False}
                    new_daily_status = 1 if daily_checked else 0
                    if daily_tasks[task].get("daily", 0) != new_daily_status:
                        daily_tasks[task]["daily"] = new_daily_status
                        save_data_to_server_file(data)
                        st.rerun()

                with col_mt2:
                    complete_checked = st.checkbox(
                        f"주간 완료 (일일 초기화 안됨)",
                        value=complete_done,
                        key=f"{selected_char_name}_{task}_complete_checkbox"
                    )
                    if not isinstance(daily_tasks.get(task), dict): daily_tasks[task] = {"daily": 0, "complete": False}
                    new_complete_status = complete_checked
                    if daily_tasks[task].get("complete", False) != new_complete_status:
                         daily_tasks[task]["complete"] = new_complete_status
                         save_data_to_server_file(data)
                         st.rerun()


            else: # 횟수 차감 방식 숙제
                count = current_task_state if isinstance(current_task_state, int) else template_state
                st.markdown(f"**{task}:** 남은 횟수 {count}")
                if count > 0:
                    if st.button(f"{task} 1회 완료", key=f"{selected_char_name}_{task}_daily_btn"):
                        daily_tasks[task] = count - 1
                        save_data_to_server_file(data)
                        st.rerun()
                else:
                     st.text("✔️ 완료")


        # --- DAILY 섹션 끝, 구분선 추가 (WEEKLY 시작 전) ---
        st.markdown("---")


        # --- WEEKLY ---
        st.header("WEEKLY")
        # --- 구분선 추가: WEEKLY 헤더와 숙제 목록 사이 ---
        st.markdown("---")

        weekly_tasks = selected_char_data.get("weekly_tasks", {})
        if not isinstance(weekly_tasks, dict): # dict 형태가 아니면 빈 딕셔너리로 초기화
             weekly_tasks = {}
             selected_char_data["weekly_tasks"] = weekly_tasks


        # 주간 숙제 목록 표시 (WEEKLY_TASK_TEMPLATE 기준으로 표시)
        for task, template_count in WEEKLY_TASK_TEMPLATE.items():
             current_task_count = weekly_tasks.get(task, template_count)
             count = current_task_count if isinstance(current_task_count, int) else template_count

             st.markdown(f"**{task}:** 남은 횟수 {count}")
             if count > 0:
                 if st.button(f"{task} 1회 완료", key=f"{selected_char_name}_{task}_weekly_btn"):
                     weekly_tasks[task] = count - 1
                     save_data_to_server_file(data)
                     st.rerun()
             else:
                 st.text("✔️ 완료")

        # --- WEEKLY 섹션 끝, 구분선 추가 (데이터 관리 시작 전) ---
        st.markdown("---")


    else: # Should not happen if selected_char_name is valid and characters list is not empty, but as a safeguard
        st.info("선택된 캐릭터 정보를 불러올 수 없습니다.")
        # Safeguard: Render default separators if something went wrong
        st.markdown("---") # DAILY section separator
        st.markdown("---") # WEEKLY section separator
        st.markdown("---") # Data management separator


def _render_data_management(data):
    """데이터 관리 섹션 렌더링"""
    st.header("데이터 관리")

    show_data_management = st.session_state.get("show_data_management", False)

    if st.button("데이터 관리 열기/닫기", key="toggle_data_management"):
        st.session_state.show_data_management = not show_data_management
        st.rerun()

    if st.session_state.get("show_data_management", False):
        st.subheader("데이터 관리 메뉴")

        # JSON 다운로드
        st.download_button(
            label="JSON 파일 다운로드",
            data=save_data(), # save_data gets current state and updates timestamps before returning JSON string
            file_name="mabinogi_tasks.json",
            mime="application/json",
            key="download_json"
        )

        # JSON 업로드
        uploaded_file = st.file_uploader("JSON 파일 업로드", type="json", key="upload_json")
        if uploaded_file is not None:
            load_data(uploaded_file) # load_data handles loading, validation, auto-reset and saving to server file
            # load_data 내부에서 필요한 경우 rerun 호출

        # 수동 초기화 버튼
        col_reset1, col_reset2 = st.columns(2)
        with col_reset1:
            if st.button("일일 숙제 수동 초기화", key="manual_daily_reset"):
                perform_daily_reset(data)
                # Update timestamp and save after reset
                if not isinstance(data.get("last_reset_timestamps"), dict): data["last_reset_timestamps"] = {}
                data["last_reset_timestamps"]["daily"] = datetime.now(KST).isoformat()
                save_data_to_server_file(data)
                st.rerun()
        with col_reset2:
            if st.button("주간 숙제 수동 초기화", key="manual_weekly_reset"):
                perform_weekly_reset(data)
                # Update timestamp and save after reset
                if not isinstance(data.get("last_reset_timestamps"), dict): data["last_reset_timestamps"] = {}
                data["last_reset_timestamps"]["weekly"] = datetime.now(KST).isoformat()
                save_data_to_server_file(data)
                st.rerun()


# --- 메인 애플리케이션 로직 ---

# Add custom CSS for font size and spacing adjustments
st.markdown("""
<style>
/* 전체 글자 크기 및 여백 조정 */
/* root 폰트 사이즈를 줄여서 전체적으로 작게 만듭니다. */
html {
    font-size: 14px !important;
}
/* 일부 요소의 폰트 사이즈 재조정 */
body, [class*="st-emotion"], [class*="stText"] {
    font-size: 1em !important; /* 14px 기준 */
    line-height: 1.4 !important; /* 줄 간격 */
}

/* 제목 크기 및 여백 조정 */
h1 { font-size: 1.8em !important; margin-top: 0.5em !important; margin-bottom: 0.5em !important; }
/* DAILY, WEEKLY 헤더 크기 확대 */
h2 { font-size: 1.6em !important; margin-top: 1em !important; margin-bottom: 0.4em !important; }
h3 { font-size: 1.1em !important; margin-top: 0.8em !important; margin-bottom: 0.3em !important; }
h4 { font-size: 1em !important; margin-top: 0.6em !important; margin-bottom: 0.2em !important; } /* Added for form titles */


/* 버튼 크기 및 패딩 조정 */
div[data-testid="stButton"] button {
    font-size: 0.9em !important; /* 14px 기준 0.9em */
    padding: 0.3em 0.6em !important; /* 상하 좌우 패딩 */
    margin: 0.2em 0 !important; /* 버튼 위아래 마진 */
}

/* 체크박스 라벨 크기 조정 */
div[data-testid="stCheckbox"] label {
    font-size: 1em !important; /* 14px 기준 */
    margin-bottom: 0.3em !important; /* 체크박스 아래 마진 */
    padding-top: 0 !important; /* 체크박스 위쪽 패딩 줄임 */
    padding-bottom: 0 !important; /* 체크박스 아래쪽 패딩 줄임 */
}

/* 입력 필드 및 셀렉트 박스 라벨 크기 조정 */
div[data-testid="stTextInput"] label,
div[data-testid="stSelectbox"] label,
div[data-testid="stFileUploader"] label {
    font-size: 1em !important; /* 14px 기준 */
    margin-bottom: 0.1em !important;
}

/* 입력 필드 내부 텍스트 크기 및 패딩 조정 */
div[data-testid="stTextInput"] input {
     font-size: 1em !important; /* 14px 기준 */
     padding: 0.3em 0.6em !important;
}

/* selectbox 선택된 값 텍스트 크기 조정 */
div[data-testid="stSelectbox"] div[data-testid="stText"] {
     font-size: 1em !important; /* 14px 기준 */
}
/* selectbox 드롭다운 목록 텍스트 크기 조정 (셀렉터 복잡할 수 있음, 일부 환경에서만 적용될 수 있음) */
/* .stSelectbox > div > div > div > div { font-size: 1em !important; } */


/* markdown으로 만든 텍스트 (예: 숙제 이름) 마진 조정 */
div[data-testid="stMarkdownContainer"] {
     margin-top: 0.4em !important; /* 마크다운 위 마진 */
     margin-bottom: 0.2em !important; /* 마크다운 아래 마진 */
     padding-top: 0 !important;
     padding-bottom: 0 !important;
}
div[data-testid="stMarkdownContainer"] p {
    margin: 0 !important; /* p 태그 기본 마진 제거 */
    padding: 0 !important;
}

/* 구분선 마진 조정 */
hr {
    margin-top: 0.8em !important; /* 구분선 위 마진 */
    margin-bottom: 0.8em !important; /* 구분선 아래 마진 */
}

/* Form 컨테이너 마진/패딩 조정 */
div[data-testid="stForm"] {
    padding: 0.8em !important; /* 폼 내부 패딩 */
    margin-bottom: 1em !important; /* 폼 아래 마진 */
}

/* 컨테이너 (border=True) 패딩/마진 조정 */
div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"] {
    margin-bottom: 0.8em !important; /* 컨테이너 블록 아래 마진 */
    padding: 0.8em !important; /* 컨테이너 내부 패딩 */
}


/* 컬럼 간 간격 조정 (기본 gap 줄이기) */
div[data-testid="stHorizontalBlock"] {
    gap: 0.8rem !important; /* 컬럼 사이 간격 */
}

/* 정보/경고/성공 메시지 박스 마진 조정 */
div[data-testid="stAlert"] {
    margin-top: 0.5em !important;
    margin-bottom: 0.5em !important;
    padding: 0.8em !important;
    font-size: 0.9em !important;
}


</style>
""", unsafe_allow_html=True)


# 데이터 로드 (앱 실행 시 최초 1회 또는 파일 업로드 시)
# load_data 함수는 필요한 경우 내부적으로 st.rerun()을 호출하고 파일 자동 저장을 시도합니다.
# 이 함수는 st.session_state.data에 데이터를 설정합니다.
load_data()

# 메인 데이터 가져오기 (load_data 호출 후에는 st.session_state.data에 유효한 데이터가 있다고 가정)
app_data = st.session_state.data

# --- 메인 타이틀 ---
st.title(APP_TITLE)


# --- UI 렌더링 함수 호출 ---
_render_character_management(app_data)

# 구분선 추가 (캐릭터 관리 섹션과 숙제/선택 섹션 사이)
# 이 구분선은 _render_character_management 함수의 마지막 콤보박스/버튼 그룹과 _render_tasks 함수의 시작 (DAILY 헤더) 사이에 위치합니다.
# _render_tasks 함수 내부에서 selectbox와 DAILY 헤더 사이의 구분선이 추가됩니다.

_render_tasks(app_data)
# _render_tasks 함수 내부에서 DAILY 섹션 끝과 WEEKLY 섹션 끝에 구분선이 추가됩니다.

# 데이터 관리 섹션 헤더는 _render_data_management 함수 내에 있으므로 별도 구분선 없이 호출합니다.
_render_data_management(app_data)

# 데이터 관리 섹션 하단에는 별도 구분선이 필요 없습니다.

