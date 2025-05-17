import streamlit as st
import json
from datetime import datetime, time, date, timedelta
import pytz # 시간대 처리를 위해 필요
import os # 파일 처리

# 시간대 설정 (한국 시간)
KST = pytz.timezone('Asia/Seoul')

# 데이터 저장 파일 경로
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
        # st.sidebar.info("데이터 자동 저장됨") # Optional feedback
    except Exception as e:
        st.sidebar.error(f"데이터 자동 저장 실패: {e}") # Indicate save failure


def load_data(uploaded_file=None):
    """데이터 로드 및 자동 초기화 처리"""
    data = None
    loaded_from_file = False

    if 'data' in st.session_state:
        # 1. Data already in session state (e.g., after rerun), use it
        data = st.session_state.data
    elif uploaded_file is not None:
        # 2. Uploaded file takes next priority if no session state data
        try:
            data = json.load(uploaded_file)
            # Validate minimum structure after upload
            if not isinstance(data, dict) or "characters" not in data or "shared_tasks" not in data or "last_reset_timestamps" not in data:
                 st.warning("업로드된 파일 형식이 올바르지 않습니다. 기본 데이터로 로드합니다.")
                 data = DEFAULT_DATA.copy()
            else:
                 st.success("파일이 성공적으로 로드되었습니다.")
                 loaded_from_file = True # Indicate successful load for saving later
        except Exception as e:
            st.error(f"파일 로드 중 오류 발생: {e}")
            data = DEFAULT_DATA.copy() # Error on upload, revert to default
    else:
        # 3. No session state data, no upload -> try loading from server file
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Validate minimum structure after loading server file
                if not isinstance(data, dict) or "characters" not in data or "shared_tasks" not in data or "last_reset_timestamps" not in data:
                     st.warning(f"'{DATA_FILE}' 파일 형식이 올바르지 않습니다. 기본 데이터로 로드합니다.")
                     data = DEFAULT_DATA.copy()
                else:
                     st.info(f"'{DATA_FILE}' 파일에서 데이터를 로드했습니다.")
                     loaded_from_file = True # Indicate successful load for saving later
            except Exception as e:
                st.warning(f"'{DATA_FILE}' 파일 로드 중 오류 발생: {e}. 기본 데이터로 시작합니다.")
                data = DEFAULT_DATA.copy()
        else:
            # 4. No file exists, load default data
            st.info(f"'{DATA_FILE}' 파일이 없습니다. 새 데이터로 시작합니다.")
            data = DEFAULT_DATA.copy()

    # Ensure session state is initialized with loaded/default data
    if 'data' not in st.session_state or st.session_state.data is None:
         st.session_state.data = data

    # Perform auto-reset based on loaded data (or default data)
    check_and_perform_auto_reset()

    # Save data to server file after initial load if it came from file or default
    # This ensures the file exists and contains the current state (including potential auto-resets)
    # If loaded from uploaded_file, it's also saved.
    if loaded_from_file or not os.path.exists(DATA_FILE):
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
        # daily_tasks 항목이 없거나 None이면 생성
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

    st.success("일일 숙제 초기화 완료.")


def perform_weekly_reset(data):
    """주간 숙제 초기화 로직"""
    st.info("주간 숙제 초기화 중...")
    # 안전하게 데이터 구조에 접근
    characters = data.get("characters", [])

    for char in characters:
        # weekly_tasks 항목이 없거나 None이면 생성
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
        # Update timestamp in data object
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
    col1, col2, col3 = st.columns(3)

    with col1:
        # 캐릭터 추가 (Form 사용)
        with st.form("add_character_form", clear_on_submit=True):
            new_char_name = st.text_input("새 캐릭터 이름 입력:")
            add_button_clicked = st.form_submit_button("캐릭터 추가")

            if add_button_clicked:
                if new_char_name:
                    # 캐릭터 이름 유효성 확인 및 중복 체크
                    valid_char_names = [c.get("name") for c in characters if isinstance(c, dict) and c.get("name")]
                    if new_char_name not in valid_char_names:
                        # 새 캐릭터 데이터 추가 (템플릿 복사)
                        new_character = {
                            "name": new_char_name,
                            "daily_tasks": DAILY_TASK_TEMPLATE.copy(),
                            "weekly_tasks": WEEKLY_TASK_TEMPLATE.copy()
                        }
                        # 길드 출석 상태는 현재 공유 상태로 초기화
                        new_character["daily_tasks"]["길드 출석"] = data.get("shared_tasks", {}).get("길드 출석", 0)

                        characters.append(new_character)
                        save_data_to_server_file(data) # 데이터 변경 후 저장
                        st.success(f"'{new_char_name}' 캐릭터가 추가되었습니다.")
                        # 새로 추가된 캐릭터를 자동으로 선택
                        st.session_state.selected_char = new_char_name
                        st.rerun() # UI 구조 변경(selectbox 옵션) 반영을 위해 rerun

                    else:
                        st.warning("이미 존재하는 이름입니다.")
                else:
                    st.warning("캐릭터 이름을 입력해주세요.")


    with col2:
        # 캐릭터 수정 (선택된 캐릭터 이름 변경)
        if len(characters) > 0:
            # 현재 선택된 캐릭터 이름 가져오기 (세션 상태 또는 첫 캐릭터 이름)
            selected_char_name_for_modify = st.session_state.get("selected_char")
            # 유효한 캐릭터 이름 목록
            valid_char_names = [c.get("name") for c in characters if isinstance(c, dict) and c.get("name")]

            # 현재 선택된 이름이 유효하지 않으면 목록의 첫 이름으로 설정
            if selected_char_name_for_modify not in valid_char_names:
                 selected_char_name_for_modify = valid_char_names[0] if valid_char_names else None

            if selected_char_name_for_modify:
                 with st.form("modify_character_form", clear_on_submit=False): # clear_on_submit=False로 현재 입력값 유지
                     # value 기본값 설정 시 유효한 이름인지 다시 확인
                     default_name = selected_char_name_for_modify if selected_char_name_for_modify in valid_char_names else (valid_char_names[0] if valid_char_names else "")
                     new_char_name = st.text_input(f"'{selected_char_name_for_modify}'의 새 이름 입력:", value=default_name, key="modify_name_input")
                     modify_button_clicked = st.form_submit_button("이름 변경")

                     if modify_button_clicked:
                         if new_char_name and new_char_name != selected_char_name_for_modify:
                            # 다른 캐릭터 이름과 중복 확인 (수정 대상 캐릭터 제외)
                            other_char_names = [c.get("name") for c in characters if isinstance(c, dict) and c.get("name") and c.get("name") != selected_char_name_for_modify]
                            if new_char_name not in other_char_names:
                               # 해당 캐릭터 찾아서 이름 변경
                               for char in characters:
                                   if isinstance(char, dict) and char.get("name") == selected_char_name_for_modify:
                                       char["name"] = new_char_name
                                       save_data_to_server_file(data) # 데이터 변경 후 저장
                                       st.success(f"'{selected_char_name_for_modify}' 캐릭터 이름이 '{new_char_name}'(으)로 변경되었습니다.")
                                       st.session_state.selected_char = new_char_name # 선택된 캐릭터 이름도 업데이트
                                       st.rerun() # UI 구조 변경 반영
                                       break # 찾았으면 루프 중단
                            else:
                                st.warning("이미 존재하는 이름입니다.")
                         elif new_char_name == selected_char_name_for_modify:
                             st.info("이름 변경이 없습니다.")
                         else:
                             st.warning("새 캐릭터 이름을 입력해주세요.")
            else:
                 st.text("수정할 캐릭터 없음")


    with col3:
        # 캐릭터 삭제
        if len(characters) > 0:
            # 현재 선택된 캐릭터 이름 가져오기
            selected_char_name_for_delete = st.session_state.get("selected_char")
             # 유효한 캐릭터 이름 목록
            valid_char_names = [c.get("name") for c in characters if isinstance(c, dict) and c.get("name")]

            # 현재 선택된 이름이 유효하지 않으면 목록의 첫 이름으로 설정
            if selected_char_name_for_delete not in valid_char_names:
                 selected_char_name_for_delete = valid_char_names[0] if valid_char_names else None

            if selected_char_name_for_delete:
                # 삭제 확인 메시지 추가 (선택 사항)
                if st.button(f"'{selected_char_name_for_delete}' 캐릭터 삭제", key="delete_char_btn"):
                    # 실제로 삭제 - 필터링 후 리스트 재할당
                    original_char_count = len(characters)
                    # 유효한 캐릭터 중 선택된 이름과 다른 캐릭터만 남김
                    data["characters"] = [c for c in characters if isinstance(c, dict) and c.get("name") != selected_char_name_for_delete]

                    if len(data["characters"]) < original_char_count: # 실제로 삭제되었는지 확인
                         save_data_to_server_file(data) # 데이터 변경 후 저장
                         st.success(f"'{selected_char_name_for_delete}' 캐릭터가 삭제되었습니다.")
                         if data["characters"]:
                             # 남은 캐릭터 중 첫 번째 캐릭터 이름으로 업데이트
                             st.session_state.selected_char = data["characters"][0].get("name")
                         else:
                             st.session_state.selected_char = None # 남은 캐릭터 없음
                         st.rerun() # UI 구조 변경(selectbox 옵션) 반영을 위해 rerun
                    else:
                         st.warning("캐릭터 삭제에 실패했습니다.") # 선택된 이름의 캐릭터를 찾지 못한 경우 등
            else:
                 st.text("삭제할 캐릭터 없음") # 캐릭터가 0개일 때 또는 선택된 캐릭터가 없을 때


# --- UI 렌더링 함수 ---

def _render_tasks(data):
    """숙제 목록 섹션 렌더링 (DAILY, WEEKLY)"""
    characters = data.get("characters", [])
    shared_tasks = data.get("shared_tasks", {}) # 안전하게 데이터 접근

    # 유효한 캐릭터 이름 목록 생성
    valid_char_names = [c.get("name") for c in characters if isinstance(c, dict) and c.get("name") is not None]

    # 목록이 비어있을 경우 selectbox 표시 안함
    if not valid_char_names:
         st.info("등록된 캐릭터가 없습니다. 캐릭터 관리에서 캐릭터를 추가해주세요.")
         # selectbox 영역이 사라지므로 구분선 추가하지 않음 (render_character_management 후 구분선으로 충분)
         return # 함수 종료

    # 현재 선택된 캐릭터 이름이 유효한지 확인하고 필요시 업데이트
    current_selection = st.session_state.get("selected_char")
    if current_selection not in valid_char_names:
         st.session_state.selected_char = valid_char_names[0] if valid_char_names else None # 유효하지 않으면 첫 캐릭터 선택 또는 None

    # 캐릭터 선택 selectbox
    selected_char_name = st.selectbox(
        "캐릭터 선택:",
        valid_char_names, # 유효한 이름 목록 사용
        key="selected_char_selectbox", # 다른 위젯과의 키 중복 방지를 위해 selectbox 전용 키 사용
        index=valid_char_names.index(st.session_state.selected_char) if st.session_state.selected_char in valid_char_names else 0 # 인덱스 설정
    )
    st.session_state.selected_char = selected_char_name # Keep session state in sync


    # --- 구분선 추가: 캐릭터 selectbox와 DAILY 헤더 사이 ---
    st.markdown("---")


    selected_char_data = next((c for c in characters if isinstance(c, dict) and c.get("name") == selected_char_name), None)

    if selected_char_data:
        # Removed redundant character name display: st.markdown(f"### {selected_char_name}")

        # --- DAILY ---
        st.header("DAILY")
        # --- 구분선 추가: DAILY 헤더와 숙제 목록 사이 ---
        st.markdown("---")

        daily_tasks = selected_char_data.get("daily_tasks", {})
        if not isinstance(daily_tasks, dict): # dict 형태가 아니면 빈 딕셔너리로 초기화
            daily_tasks = {}
            selected_char_data["daily_tasks"] = daily_tasks # 데이터에 반영

        # 길드 출석 (공용) - 모든 캐릭터의 상태 동기화
        # shared_tasks 항목이 없으면 기본값 0 사용
        current_shared_guild_status = shared_tasks.get("길드 출석", 0)
        shared_guild_checked = st.checkbox(
            "길드 출석 (모든 캐릭터 공유)",
            value=current_shared_guild_status == 1,
            key=f"shared_guild_checkbox" # 공유 상태는 고유 키 사용
        )
        new_shared_guild_status = 1 if shared_guild_checked else 0
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
        # 템플릿의 순서대로 표시하기 위해 템플릿을 순회
        for task, template_state in DAILY_TASK_TEMPLATE.items():
            if task == "길드 출석":
                continue # 이미 위에서 처리함

            # 현재 캐릭터 데이터에서 해당 숙제 상태 가져오기 (없으면 템플릿 기본값)
            current_task_state = daily_tasks.get(task, template_state)

            if task == "망령의 탑":
                # 망령의 탑은 일일/완료 두 가지 상태 관리
                # 현재 상태가 딕셔너리가 아니거나 키가 없을 경우 안전하게 기본값 사용
                mt_state = current_task_state if isinstance(current_task_state, dict) else {"daily": 0, "complete": False}
                daily_done = mt_state.get("daily", 0) == 1
                complete_done = mt_state.get("complete", False)

                st.markdown(f"**{task}:**")
                col_mt1, col_mt2 = st.columns(2)
                with col_mt1:
                    # key에 캐릭터 이름 포함하여 각 캐릭터별 상태 유지
                    daily_checked = st.checkbox(
                        f"일일 완료",
                        value=daily_done,
                        key=f"{selected_char_name}_{task}_daily_checkbox"
                    )
                    # 체크박스 상태 변경 시 데이터 업데이트
                    # daily_tasks[task]가 딕셔너리가 아니면 딕셔너리로 초기화
                    if not isinstance(daily_tasks.get(task), dict):
                         daily_tasks[task] = {"daily": 0, "complete": False}

                    new_daily_status = 1 if daily_checked else 0
                    if daily_tasks[task].get("daily", 0) != new_daily_status:
                        daily_tasks[task]["daily"] = new_daily_status
                        save_data_to_server_file(data) # 데이터 변경 후 저장
                        st.rerun() # 상태 변경 시 즉시 반영

                with col_mt2:
                    # key에 캐릭터 이름 포함하여 각 캐릭터별 상태 유지
                    complete_checked = st.checkbox(
                        f"주간 완료 (일일 초기화 안됨)",
                        value=complete_done,
                        key=f"{selected_char_name}_{task}_complete_checkbox"
                    )
                     # 체크박스 상태 변경 시 데이터 업데이트
                     # daily_tasks[task]가 딕셔너리가 아니면 딕셔너리로 초기화
                    if not isinstance(daily_tasks.get(task), dict):
                         daily_tasks[task] = {"daily": 0, "complete": False}

                    new_complete_status = complete_checked
                    if daily_tasks[task].get("complete", False) != new_complete_status:
                         daily_tasks[task]["complete"] = new_complete_status
                         save_data_to_server_file(data) # 데이터 변경 후 저장
                         st.rerun() # 상태 변경 시 즉시 반영


            else:
                # 횟수 차감 방식
                # 현재 상태가 정수가 아니면 템플릿 기본값 사용
                count = current_task_state if isinstance(current_task_state, int) else template_state
                st.markdown(f"**{task}:** 남은 횟수 {count}")
                if count > 0:
                    # key에 캐릭터 이름 포함
                    if st.button(f"{task} 1회 완료", key=f"{selected_char_name}_{task}_daily_btn"):
                        daily_tasks[task] = count - 1 # 횟수 차감
                        save_data_to_server_file(data) # 데이터 변경 후 저장
                        st.rerun() # 변경사항 즉시 반영
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
        # 템플릿의 순서대로 표시하기 위해 템플릿을 순회
        for task, template_count in WEEKLY_TASK_TEMPLATE.items():
             # 현재 캐릭터 데이터에서 해당 숙제 상태 가져오기 (없으면 템플릿 기본값)
             current_task_count = weekly_tasks.get(task, template_count)
             # 현재 상태가 정수가 아니면 템플릿 기본값 사용
             count = current_task_count if isinstance(current_task_count, int) else template_count

             st.markdown(f"**{task}:** 남은 횟수 {count}")
             if count > 0:
                 # key에 캐릭터 이름 포함
                 if st.button(f"{task} 1회 완료", key=f"{selected_char_name}_{task}_weekly_btn"):
                     weekly_tasks[task] = count - 1 # 횟수 차감
                     save_data_to_server_file(data) # 데이터 변경 후 저장
                     st.rerun() # 변경사항 즉시 반영
             else:
                 st.text("✔️ 완료")

        # --- WEEKLY 섹션 끝, 구분선 추가 (데이터 관리 시작 전) ---
        st.markdown("---")


    else:
        st.info("선택된 캐릭터 정보가 유효하지 않습니다. (데이터 구조 오류)")
        # 캐릭터가 없는 경우 또는 유효하지 않은 경우 표시될 구분선들
        st.markdown("---") # DAILY 섹션 대체
        st.markdown("---") # WEEKLY 섹션 대체
        st.markdown("---") # WEEKLY 숙제 목록 대체


def _render_data_management(data):
    """데이터 관리 섹션 렌더링"""
    st.header("데이터 관리") # 이 헤더는 유지

    show_data_management = st.session_state.get("show_data_management", False)

    if st.button("데이터 관리 열기/닫기", key="toggle_data_management"):
        st.session_state.show_data_management = not show_data_management
        st.rerun() # 영역 표시/숨김 변경 즉시 반영

    if st.session_state.get("show_data_management", False):
        st.subheader("데이터 관리 메뉴")

        # JSON 다운로드
        st.download_button(
            label="JSON 파일 다운로드",
            data=save_data(), # save_data 함수는 호출될 때 최신 상태를 가져오고 타임스탬프 업데이트
            file_name="mabinogi_tasks.json",
            mime="application/json",
            key="download_json"
        )

        # JSON 업로드
        uploaded_file = st.file_uploader("JSON 파일 업로드", type="json", key="upload_json")
        if uploaded_file is not None:
            load_data(uploaded_file) # load_data handles loading and saving to server file after successful upload
            # load_data 내부에서 필요한 경우 rerun 호출

        # 수동 초기화 버튼
        col_reset1, col_reset2 = st.columns(2)
        with col_reset1:
            if st.button("일일 숙제 수동 초기화", key="manual_daily_reset"):
                perform_daily_reset(data)
                # Update timestamp and save after reset
                if not isinstance(data.get("last_reset_timestamps"), dict): data["last_reset_timestamps"] = {}
                data["last_reset_timestamps"]["daily"] = datetime.now(KST).isoformat()
                save_data_to_server_file(data) # 데이터 변경 후 저장
                st.rerun() # 화면 갱신 (필수)
        with col_reset2:
            if st.button("주간 숙제 수동 초기화", key="manual_weekly_reset"):
                perform_weekly_reset(data)
                 # Update timestamp and save after reset
                if not isinstance(data.get("last_reset_timestamps"), dict): data["last_reset_timestamps"] = {}
                data["last_reset_timestamps"]["weekly"] = datetime.now(KST).isoformat()
                save_data_to_server_file(data) # 데이터 변경 후 저장
                st.rerun() # 화면 갱신 (필수)


# --- 메인 애플리케이션 로직 ---

st.title("마비노기 모바일 숙제 관리기")

# Add custom CSS for font size and minor style adjustments
st.markdown("""
<style>
/* 전체 글자 크기 및 여백 조정 */
html, body, [class*="st-emotion"], [class*="stText"] {
    font-size: 14px !important; /* 기본 폰트 크기 */
    line-height: 1.5 !important; /* 줄 간격 */
}
h1 { font-size: 1.8em !important; margin-bottom: 0.8em !important; }
h2 { font-size: 1.4em !important; margin-top: 1em !important; margin-bottom: 0.5em !important; }
h3 { font-size: 1.1em !important; margin-top: 1em !important; margin-bottom: 0.5em !important; }

/* 버튼 크기 및 패딩 조정 */
div[data-testid="stButton"] button {
    font-size: 12px !important;
    padding: 4px 8px !important; /* 상하 좌우 패딩 */
    margin: 2px 0 !important; /* 버튼 위아래 마진 */
}

/* 체크박스 라벨 크기 조정 */
div[data-testid="stCheckbox"] label {
    font-size: 14px !important;
    margin-bottom: 5px !important; /* 체크박스 아래 마진 */
}

/* 입력 필드 및 셀렉트 박스 라벨 크기 조정 */
div[data-testid="stTextInput"] label,
div[data-testid="stSelectbox"] label,
div[data-testid="stFileUploader"] label {
    font-size: 14px !important;
    margin-bottom: 0.2em !important;
}

/* 입력 필드 내부 텍스트 크기 조정 */
div[data-testid="stTextInput"] input {
     font-size: 14px !important;
     padding: 4px 8px !important;
}

/* selectbox 드롭다운 내부 텍스트 크기 조정 (셀렉터 복잡할 수 있음) */
/* .stSelectbox > div > div { font-size: 14px !important; } */


/* markdown으로 만든 텍스트 (예: 숙제 이름) 마진 조정 */
div[data-testid="stMarkdownContainer"] {
     margin-top: 0.5em !important;
     margin-bottom: 0.3em !important;
}
div[data-testid="stMarkdownContainer"] p {
    margin: 0 !important; /* p 태그 기본 마진 제거 */
}

/* 구분선 마진 조정 */
hr {
    margin-top: 1em !important;
    margin-bottom: 1em !important;
}

/* 컬럼 간 간격 조정 (필요시) */
div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] {
    gap: 1rem; /* 기본 간격보다 줄이기 */
}

</style>
""", unsafe_allow_html=True)


# 데이터 로드 (앱 실행 시 최초 1회 또는 파일 업로드 시)
# 이 함수는 필요한 경우 내부적으로 st.rerun()을 호출하고 파일 자동 저장을 시도합니다.
load_data()

# 메인 데이터 가져오기
# load_data 함수 내에서 st.session_state.data가 설정되거나 로드됩니다.
app_data = st.session_state.data

# --- UI 렌더링 함수 호출 ---
_render_character_management(app_data)

# 구분선 추가 (캐릭터 관리 섹션과 숙제/선택 섹션 사이)
st.markdown("---")

_render_tasks(app_data)
# _render_tasks 함수 내에서 DAILY와 WEEKLY 섹션 사이, WEEKLY 섹션 끝에 구분선이 추가됩니다.

# 데이터 관리 섹션 헤더는 _render_data_management 함수 내에 있으므로 별도 구분선 없이 호출합니다.
_render_data_management(app_data)

# 데이터 관리 섹션 하단에는 별도 구분선이 필요 없습니다.

