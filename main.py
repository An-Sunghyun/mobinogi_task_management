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
        # Avoid showing errors repeatedly in production
        # st.sidebar.error(f"데이터 자동 저장 실패: {e}")
        pass # Silent failure for auto-save might be acceptable


def load_data(uploaded_file=None):
    """데이터 로드 및 자동 초기화 처리"""
    data = None
    loaded_successfully = False # Track if data was loaded from file or upload

    # Ensure session state variables for forms are initialized
    if 'show_add_char_form' not in st.session_state:
        st.session_state.show_add_char_form = False
    if 'show_modify_char_form' not in st.session_state:
        st.session_state.show_modify_char_form = False
    if 'show_data_management' not in st.session_state:
        st.session_state.show_data_management = False


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
                     # st.info(f"'{DATA_FILE}' 파일에서 데이터를 로드했습니다.") # Suppress verbose load message
                     loaded_successfully = True
            except Exception as e:
                # st.warning(f"'{DATA_FILE}' 파일 로드 중 오류 발생: {e}. 기본 데이터로 시작합니다.") # Suppress verbose error
                data = DEFAULT_DATA.copy()
        else:
            # 4. No file exists, load default data
            # st.info(f"'{DATA_FILE}' 파일이 없습니다. 새 데이터로 시작합니다.") # Suppress verbose message
            data = DEFAULT_DATA.copy()

    # Ensure session state is initialized with loaded/default data if it wasn't already
    # or if the previously loaded data was invalid
    if 'data' not in st.session_state or st.session_state.data is None or not loaded_successfully:
         st.session_state.data = data


    # Perform auto-reset based on the data that was just loaded/set to session state
    check_and_perform_auto_reset()

    # Save data to server file after initial load if it came from file, upload, or default
    # This ensures the file exists and contains the current state (including potential auto-resets)
    # Only save if data was successfully loaded or initialized as default
    # Also saves if auto-reset happened. Avoid double-saving on initial load.
    # The auto-reset logic already saves if a reset occurs.
    # Let's ensure a save happens even if no auto-reset occurs but data was just loaded/defaulted.
    if loaded_successfully and 'data' in st.session_state: # Ensure session state has data
         # Check if auto-reset caused a rerun already. If not, save now.
         # This is tricky with Streamlit's execution model.
         # Simplest is to save after check_and_perform_auto_reset if data was just loaded/initialized.
         # However, auto-reset already saves *and* reruns.
         # Let's trust the auto-reset logic to save and just save on initial load if file didn't exist.
         if not os.path.exists(DATA_FILE):
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
    # Removed st.header("캐릭터 관리")

    characters = data.get("characters", []) # 안전하게 데이터 접근

    # 유효한 캐릭터 이름 목록 생성
    valid_char_names = [c.get("name") for c in characters if isinstance(c, dict) and c.get("name")]
    if not valid_char_names:
         valid_char_names_for_select = ["캐릭터 없음"] # 캐릭터가 없을 때 selectbox에 표시될 기본 텍스트
    else:
         valid_char_names_for_select = valid_char_names[:] # 목록 복사

    # 현재 선택된 캐릭터 이름 가져오기 (세션 상태 또는 유효한 첫 캐릭터 이름)
    # valid_char_names가 비어있지 않으면 첫 번째 이름으로 기본값 설정
    if 'selected_char' not in st.session_state or st.session_state.selected_char not in valid_char_names:
        st.session_state.selected_char = valid_char_names[0] if valid_char_names else None

    # --- 캐릭터 선택 selectbox 및 관리 버튼 배치 ---
    # Adjust columns to fit selectbox and 3 buttons
    col_select, col_btn1, col_btn2, col_btn3 = st.columns([4, 1, 1, 1]) # Adjusted column ratios

    with col_select:
        # 캐릭터 선택 selectbox
        selected_char_name = st.selectbox(
            "캐릭터 선택:", # Keep label for selectbox clarity
            options=valid_char_names_for_select,
            key="selected_char_selectbox",
            # 현재 선택된 이름이 목록에 있으면 해당 인덱스 사용, 없으면 0 사용
            index=valid_char_names_for_select.index(st.session_state.selected_char) if st.session_state.selected_char in valid_char_names_for_select else 0,
            disabled=not characters # 캐릭터 없으면 비활성화
        )
        # selectbox 선택 결과를 session_state에 저장 (실제 캐릭터 이름인 경우만)
        # This ensures st.session_state.selected_char always reflects the selectbox value, unless '캐릭터 없음' is selected and there are actual characters (a safeguard).
        if selected_char_name != "캐릭터 없음":
             st.session_state.selected_char = selected_char_name
        elif characters and st.session_state.selected_char not in valid_char_names: # Safeguard: if selectbox shows '캐릭터 없음' but characters exist and selected_char is invalid
             st.session_state.selected_char = characters[0].get("name") # Force to first character
             st.rerun() # Force rerun to correct selectbox

    with col_btn1:
        st.write(" ") # Add spacing to align buttons vertically
        # 캐릭터 추가 버튼 - 클릭 시 입력 UI 표시 플래그 설정
        if st.button("추가", key="btn_add_char"):
            st.session_state.show_add_char_form = True
            st.session_state.show_modify_char_form = False # Close other form
            st.rerun() # State change needs rerun to show the form

    with col_btn2:
        st.write(" ") # Add spacing
        # 캐릭터 변경 버튼 - 클릭 시 입력 UI 표시 플래그 설정
        if st.button("변경", key="btn_modify_char", disabled=not characters): # Disable if no characters
            st.session_state.show_modify_char_form = True
            st.session_state.show_add_char_form = False # Close other form
            st.rerun() # State change needs rerun to show the form

    with col_btn3:
        st.write(" ") # Add spacing
        # 캐릭터 삭제 버튼 - 클릭 시 삭제 로직 실행
        if st.button("삭제", key="btn_delete_char", disabled=not characters): # Disable if no characters
            selected_char_name_to_delete = st.session_state.get("selected_char")
            # Ensure selected character is valid before deleting
            if selected_char_name_to_delete and selected_char_name_to_delete in valid_char_names:
                # Filter out the character to delete
                original_char_count = len(characters)
                data["characters"][:] = [c for c in characters if isinstance(c, dict) and c.get("name") != selected_char_name_to_delete] # Modify list in place via slice

                if len(data["characters"]) < original_char_count: # Check if deletion happened
                     save_data_to_server_file(data) # Save after modifying data
                     st.success(f"'{selected_char_name_to_delete}' 캐릭터가 삭제되었습니다.")
                     # Update selected character state after deletion
                     if data["characters"]:
                         st.session_state.selected_char = data["characters"][0].get("name")
                     else:
                         st.session_state.selected_char = None # No characters left
                     st.rerun() # UI update
                else:
                     st.warning("캐릭터 삭제에 실패했습니다. (캐릭터를 찾을 수 없습니다)")
            elif not characters:
                 st.info("삭제할 캐릭터가 없습니다.")
            else:
                 st.info("유효한 캐릭터가 선택되지 않았습니다.") # Should not happen with proper state management but as safeguard


    # --- 캐릭터 추가 입력 UI (조건부 표시) ---
    if st.session_state.get("show_add_char_form"):
        with st.container(border=True): # Visually distinct container
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
                        valid_char_names_current = [c.get("name") for c in data.get("characters", []) if isinstance(c, dict) and c.get("name")] # Get latest list
                        if new_char_name_input not in valid_char_names_current:
                            new_character = {
                                "name": new_char_name_input,
                                "daily_tasks": DAILY_TASK_TEMPLATE.copy(),
                                "weekly_tasks": WEEKLY_TASK_TEMPLATE.copy()
                            }
                            new_character["daily_tasks"]["길드 출석"] = data.get("shared_tasks", {}).get("길드 출석", 0)
                            data["characters"].append(new_character) # Add to the list in data
                            save_data_to_server_file(data)
                            st.success(f"'{new_char_name_input}' 캐릭터가 추가되었습니다.")
                            st.session_state.selected_char = new_char_name_input # Auto-select new char
                            st.session_state.show_add_char_form = False # Hide form
                            st.rerun() # Update UI (selectbox options, tasks)
                        else:
                            st.warning("이미 존재하는 이름입니다.")
                    else:
                        st.warning("캐릭터 이름을 입력해주세요.")
                elif cancel_add_button:
                     st.session_state.show_add_char_form = False # Hide form
                     st.rerun() # Hide form immediately


    # --- 캐릭터 변경 입력 UI (조건부 표시) ---
    if st.session_state.get("show_modify_char_form"):
         selected_char_name_to_modify = st.session_state.get("selected_char")
         valid_char_names = [c.get("name") for c in characters if isinstance(c, dict) and c.get("name")]
         # Only show form if a valid character is selected for modification
         if selected_char_name_to_modify and selected_char_name_to_modify in valid_char_names:
              with st.container(border=True): # Visually distinct container
                   st.markdown(f"#### '{selected_char_name_to_modify}' 이름 변경")
                   with st.form("modify_character_input_form", clear_on_submit=False): # Don't clear input on submit failure
                        # Pre-fill with current name
                        new_char_name_input = st.text_input("새 이름을 입력하세요:", value=selected_char_name_to_modify, key="modify_char_name_input")
                        col_modify_form1, col_modify_form2 = st.columns(2)
                        with col_modify_form1:
                             submit_modify_button = st.form_submit_button("변경하기")
                        with col_modify_form2:
                             cancel_modify_button = st.form_submit_button("취소")


                        if submit_modify_button:
                             if new_char_name_input and new_char_name_input != selected_char_name_to_modify:
                                # Check for duplicate name among *other* characters
                                other_char_names = [c.get("name") for c in data.get("characters", []) if isinstance(c, dict) and c.get("name") and c.get("name") != selected_char_name_to_modify]
                                if new_char_name_input not in other_char_names:
                                   # Find and update the character's name
                                   found_char = next((c for c in data["characters"] if isinstance(c, dict) and c.get("name") == selected_char_name_to_modify), None)
                                   if found_char:
                                       found_char["name"] = new_char_name_input
                                       save_data_to_server_file(data)
                                       st.success(f"'{selected_char_name_to_modify}' 캐릭터 이름이 '{new_char_name_input}'(으)로 변경되었습니다.")
                                       st.session_state.selected_char = new_char_name_input # Update selected state
                                       st.session_state.show_modify_char_form = False # Hide form
                                       st.rerun() # Update UI
                                   else:
                                        st.error("변경 대상 캐릭터를 찾을 수 없습니다. (데이터 불일치)") # Should not happen
                                else:
                                    st.warning("이미 존재하는 이름입니다.")
                             elif new_char_name_input == selected_char_name_to_modify:
                                 st.info("이름 변경이 없습니다.")
                             else:
                                 st.warning("새 이름을 입력해주세요.")
                        elif cancel_modify_button:
                             st.session_state.show_modify_char_form = False # Hide form
                             st.rerun() # Hide form immediately
         else: # If no valid character is selected when modify form is supposed to show, reset the flag
              st.session_state.show_modify_char_form = False


# --- UI 렌더링 함수 ---

def _render_tasks(data):
    """숙제 목록 섹션 렌더링 (DAILY, WEEKLY)"""
    characters = data.get("characters", [])
    shared_tasks = data.get("shared_tasks", {}) # 안전하게 데이터 접근

    # 유효한 캐릭터 이름 목록 생성
    valid_char_names = [c.get("name") for c in characters if isinstance(c, dict) and c.get("name") is not None]

    # Determine the currently selected character data
    selected_char_data = None
    selected_char_name = st.session_state.get("selected_char")
    if selected_char_name and selected_char_name in valid_char_names:
         selected_char_data = next((c for c in characters if isinstance(c, dict) and c.get("name") == selected_char_name), None)


    # Only render task sections if characters exist AND a valid character is selected
    if not characters or not selected_char_data:
         # No characters or no valid character selected, display instructions.
         # Character management section already handles messages.
         # Add the separator after the character management section, before where tasks *would* be.
         # The separator after selectbox/buttons is rendered in the main app logic.
         # If this function runs because there are no characters, we don't need task headers/separators.
         pass # Do nothing, the character management section handled the "no characters" case.
         # The separator *after* character management section is in main app logic.
    else:
        # A valid character is selected, render tasks for this character.

        # --- DAILY ---
        st.header("DAILY")
        # --- 구분선 추가: DAILY 헤더와 숙제 목록 사이 ---
        st.markdown("---")

        daily_tasks = selected_char_data.get("daily_tasks", {})
        if not isinstance(daily_tasks, dict): # Ensure daily_tasks is a dict
            daily_tasks = {}
            selected_char_data["daily_tasks"] = daily_tasks # Update data


        # 길드 출석 (공용) - 모든 캐릭터의 상태 동기화
        current_shared_guild_status = shared_tasks.get("길드 출석", 0)
        # Key must be unique across all runs, not depending on selected character name
        shared_guild_checked = st.checkbox(
            "길드 출석 (모든 캐릭터 공유)",
            value=current_shared_guild_status == 1,
            key=f"shared_guild_checkbox" # Consistent key
        )
        new_shared_guild_status = 1 if shared_guild_checked else 0
        # Update shared status in data if it changed
        if data.get("shared_tasks", {}).get("길드 출석", 0) != new_shared_guild_status:
             if not isinstance(data.get("shared_tasks"), dict): # Ensure shared_tasks is a dict
                  data["shared_tasks"] = {}
             data["shared_tasks"]["길드 출석"] = new_shared_guild_status
             # Sync all characters' guild status
             for char in characters:
                  if isinstance(char, dict) and isinstance(char.get("daily_tasks"), dict):
                     char["daily_tasks"]["길드 출석"] = new_shared_guild_status
             save_data_to_server_file(data)
             st.rerun() # Rerun to update all UIs using shared status

        # 일일 숙제 목록 표시 (DAILY_TASK_TEMPLATE 기준으로 표시)
        for task, template_state in DAILY_TASK_TEMPLATE.items():
            if task == "길드 출석":
                continue # Skip shared task here

            # Get current state for the task (default to template if not found or invalid)
            current_task_state = daily_tasks.get(task, template_state)

            if task == "망령의 탑":
                # Handle '망령의 탑' which has nested state
                mt_state = current_task_state if isinstance(current_task_state, dict) else {"daily": 0, "complete": False}
                daily_done = mt_state.get("daily", 0) == 1
                complete_done = mt_state.get("complete", False)

                st.markdown(f"**{task}:**")
                col_mt1, col_mt2 = st.columns(2)
                with col_mt1:
                    daily_checked = st.checkbox(
                        f"일일 완료",
                        value=daily_done,
                        key=f"{selected_char_name}_{task}_daily_checkbox" # Key unique to char and task
                    )
                    # Update data if checkbox state changed
                    # Ensure nested structure exists
                    if not isinstance(daily_tasks.get(task), dict): daily_tasks[task] = {"daily": 0, "complete": False}
                    new_daily_status = 1 if daily_checked else 0
                    if daily_tasks[task].get("daily", 0) != new_daily_status:
                        daily_tasks[task]["daily"] = new_daily_status
                        save_data_to_server_file(data)
                        st.rerun() # Rerun to reflect state change

                with col_mt2:
                    complete_checked = st.checkbox(
                        f"주간 완료 (일일 초기화 안됨)",
                        value=complete_done,
                        key=f"{selected_char_name}_{task}_complete_checkbox" # Key unique to char and task
                    )
                    # Update data if checkbox state changed
                    # Ensure nested structure exists
                    if not isinstance(daily_tasks.get(task), dict): daily_tasks[task] = {"daily": 0, "complete": False}
                    new_complete_status = complete_checked
                    if daily_tasks[task].get("complete", False) != new_complete_status:
                         daily_tasks[task]["complete"] = new_complete_status
                         save_data_to_server_file(data)
                         st.rerun() # Rerun to reflect state change


            else: # Standard count-based tasks
                count = current_task_state if isinstance(current_task_state, int) else template_state
                st.markdown(f"**{task}:** 남은 횟수 {count}")
                if count > 0:
                    # Button to decrement count
                    if st.button(f"{task} 1회 완료", key=f"{selected_char_name}_{task}_daily_btn"): # Key unique to char and task
                        daily_tasks[task] = count - 1
                        save_data_to_server_file(data)
                        st.rerun() # Rerun to reflect state change
                else:
                     st.text("✔️ 완료")


        # --- DAILY 섹션 끝, 구분선 추가 (WEEKLY 시작 전) ---
        st.markdown("---")


        # --- WEEKLY ---
        st.header("WEEKLY")
        # --- 구분선 추가: WEEKLY 헤더와 숙제 목록 사이 ---
        st.markdown("---")

        weekly_tasks = selected_char_data.get("weekly_tasks", {})
        if not isinstance(weekly_tasks, dict): # Ensure weekly_tasks is a dict
             weekly_tasks = {}
             selected_char_data["weekly_tasks"] = weekly_tasks


        # 주간 숙제 목록 표시 (WEEKLY_TASK_TEMPLATE 기준으로 표시)
        for task, template_count in WEEKLY_TASK_TEMPLATE.items():
             # Get current count for the task (default to template if not found or invalid)
             current_task_count = weekly_tasks.get(task, template_count)
             count = current_task_count if isinstance(current_task_count, int) else template_count

             st.markdown(f"**{task}:** 남은 횟수 {count}")
             if count > 0:
                 # Button to decrement count
                 if st.button(f"{task} 1회 완료", key=f"{selected_char_name}_{task}_weekly_btn"): # Key unique to char and task
                     weekly_tasks[task] = count - 1
                     save_data_to_server_file(data)
                     st.rerun() # Rerun to reflect state change
             else:
                 st.text("✔️ 완료")

        # --- WEEKLY 섹션 끝, 구분선 추가 (데이터 관리 시작 전) ---
        st.markdown("---")


    # No else block needed for selected_char_data is None, as the outer if handles this case
    # The final separator before data management is handled in the main app logic.


def _render_data_management(data):
    """데이터 관리 섹션 렌더링"""
    st.header("데이터 관리")

    show_data_management = st.session_state.get("show_data_management", False)

    if st.button("데이터 관리 열기/닫기", key="toggle_data_management"):
        st.session_state.show_data_management = not show_data_management
        st.rerun() # Rerun to show/hide the section

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
            # load_data handles loading, validation, auto-reset, and saving to server file.
            # It will also trigger a rerun if needed.
            load_data(uploaded_file)
            # No explicit rerun needed here as load_data takes care of it


        # 수동 초기화 버튼
        col_reset1, col_reset2 = st.columns(2)
        with col_reset1:
            if st.button("일일 숙제 수동 초기화", key="manual_daily_reset"):
                perform_daily_reset(data)
                # Update timestamp and save after reset
                if not isinstance(data.get("last_reset_timestamps"), dict): data["last_reset_timestamps"] = {}
                data["last_reset_timestamps"]["daily"] = datetime.now(KST).isoformat()
                save_data_to_server_file(data)
                st.rerun() # Update UI

        with col_reset2:
            if st.button("주간 숙제 수동 초기화", key="manual_weekly_reset"):
                perform_weekly_reset(data)
                # Update timestamp and save after reset
                if not isinstance(data.get("last_reset_timestamps"), dict): data["last_reset_timestamps"] = {}
                data["last_reset_timestamps"]["weekly"] = datetime.now(KST).isoformat()
                save_data_to_server_file(data)
                st.rerun() # Update UI


# --- 메인 애플리케이션 로직 ---

# Add custom CSS for font size and spacing adjustments
st.markdown('''
<style>
/* Global Font and Spacing Adjustments */
/* Base font size for the document */
html {
    font-size: 14px !important;
}
/* Text size for most elements relative to html font size */
body, [class*="st-emotion"], [class*="stText"], label {
    font-size: 1em !important; /* 14px */
    line-height: 1.4 !important; /* Reduced line height */
}

/* Title and Header Spacing */
h1 { font-size: 1.8em !important; margin-top: 0.5em !important; margin-bottom: 0.5em !important; }
/* DAILY, WEEKLY 헤더 크기 확대 및 여백 조정 */
h2 { font-size: 1.6em !important; margin-top: 1em !important; margin-bottom: 0.4em !important; padding-bottom: 0 !important; } /* Ensure h2 has less bottom padding */
h3 { font-size: 1.1em !important; margin-top: 0.8em !important; margin-bottom: 0.3em !important; }
h4 { font-size: 1em !important; margin-top: 0.6em !important; margin-bottom: 0.2em !important; } /* Used for form titles */


/* Button Sizing and Padding */
div[data-testid="stButton"] button {
    font-size: 0.9em !important; /* Slightly smaller than base text */
    padding: 0.3em 0.6em !important; /* Reduced padding */
    margin: 0.2em 0 !important; /* Reduced vertical margin */
}

/* Checkbox Label Size and Spacing */
div[data-testid="stCheckbox"] label {
    font-size: 1em !important; /* Base font size */
    margin-bottom: 0.3em !important; /* Reduced bottom margin */
    padding-top: 0 !important; /* Remove top padding */
    padding-bottom: 0 !important; /* Remove bottom padding */
}

/* Input Label Size and Spacing */
div[data-testid="stTextInput"] label,
div[data-testid="stSelectbox"] label,
div[data-testid="stFileUploader"] label {
    font-size: 1em !important; /* Base font size */
    margin-bottom: 0.1em !important; /* Reduced bottom margin */
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}

/* Input Field Text Size and Padding */
div[data-testid="stTextInput"] input {
     font-size: 1em !important; /* Base font size */
     padding: 0.3em 0.6em !important; /* Reduced padding */
}

/* Selectbox Selected Value Text Size */
div[data-testid="stSelectbox"] div[data-testid="stText"] {
     font-size: 1em !important; /* Base font size */
}
/* Selectbox dropdown list text size (might not apply everywhere) */
/* .stSelectbox > div > div > div > div { font-size: 1em !important; } */


/* Markdown Text Spacing (e.g., task names) */
/* Targets markdown output, often wrapped in p tags inside markdown container */
div[data-testid="stMarkdownContainer"] {
     margin-top: 0.4em !important; /* Reduced top margin */
     margin-bottom: 0.2em !important; /* Reduced bottom margin */
     padding-top: 0 !important;
     padding-bottom: 0 !important;
}
div[data-testid="stMarkdownContainer"] p {
    margin: 0 !important; /* Ensure p tag default margins are removed */
    padding: 0 !important;
}

/* Horizontal Rule (Separator) Spacing */
hr {
    margin-top: 0.8em !important; /* Reduced top margin */
    margin-bottom: 0.8em !important; /* Reduced bottom margin */
}

/* Form Container Padding/Margin */
/* This targets the border=True containers used for add/modify input forms */
div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"] {
    margin-top: 0.8em !important; /* Add margin above the form container */
    margin-bottom: 1em !important; /* Reduced margin below the form container */
    padding: 0.8em !important; /* Padding inside the container */
}

/* Form itself padding */
div[data-testid="stForm"] {
    padding: 0 !important; /* Remove default form padding as container has padding */
}


/* Column Gap Adjustment */
/* Reduces horizontal space between columns */
div[data-testid="stHorizontalBlock"] {
    gap: 0.8rem !important; /* Reduced gap */
}

/* Alert Message Boxes Spacing */
div[data-testid="stAlert"] {
    margin-top: 0.5em !important;
    margin-bottom: 0.5em !important;
    padding: 0.8em !important;
    font-size: 0.9em !important;
}


</style>
''', unsafe_allow_html=True)


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
# 이 구분선은 캐릭터 selectbox/button row 와 DAILY 헤더 사이에 위치합니다.
st.markdown("---")

_render_tasks(app_data)
# _render_tasks 함수 내부에서 DAILY 섹션 끝과 WEEKLY 섹션 끝에 구분선이 추가됩니다.

# 데이터 관리 섹션은 _render_tasks 마지막 구분선 바로 아래에 옵니다.
_render_data_management(app_data)

# 데이터 관리 섹션 하단에는 별도 구분선이 필요 없습니다.
