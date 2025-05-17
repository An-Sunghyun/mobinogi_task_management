import streamlit as st
import json
from datetime import datetime, time, date, timedelta
import pytz # 시간대 처리를 위해 필요

# 시간대 설정 (한국 시간)
KST = pytz.timezone('Asia/Seoul')

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

def load_data(uploaded_file=None):
    """데이터 로드 및 자동 초기화 처리"""
    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            # 필수 키가 누락된 경우 기본값으로 초기화 (안전성 강화)
            if "characters" not in data or "shared_tasks" not in data or "last_reset_timestamps" not in data:
                 st.warning("업로드된 파일 형식이 올바르지 않습니다. 기본 데이터로 로드합니다.")
                 st.session_state.data = DEFAULT_DATA.copy()
            else:
                st.session_state.data = data
            st.success("파일이 성공적으로 로드되었습니다.")
        except Exception as e:
            st.error(f"파일 로드 중 오류 발생: {e}")
            st.session_state.data = DEFAULT_DATA.copy() # 오류 시 기본값으로
    elif 'data' not in st.session_state:
        # 세션에 데이터가 없으면 기본값 로드
        st.session_state.data = DEFAULT_DATA.copy()

    # 데이터 로드 후 자동 초기화 확인 및 수행 (필요한 경우)
    check_and_perform_auto_reset()

def save_data():
    """현재 데이터를 JSON 문자열로 반환 (다운로드용)"""
    # 저장 시점의 타임스탬프 업데이트
    st.session_state.data["last_reset_timestamps"]["daily"] = datetime.now(KST).isoformat()
    st.session_state.data["last_reset_timestamps"]["weekly"] = datetime.now(KST).isoformat()
    return json.dumps(st.session_state.data, indent=4, ensure_ascii=False)

def _get_reset_time(base_datetime, hour=6, minute=0):
    """기준 시간으로부터 특정 시분으로 설정된 datetime 객체를 반환 (시간대 고려)"""
    reset_time_today = base_datetime.replace(hour=hour, minute=minute, second=0, microsecond=0)
    # 기준 시간의 time 부분이 reset_time보다 앞설 경우 하루 전으로 설정
    if base_datetime.time() < time(hour, minute):
        reset_time = reset_time_today - timedelta(days=1)
    else:
        reset_time = reset_time_today

    return reset_time.astimezone(KST) # 한국 시간대로 보정

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
    last_daily_reset_str = data.get("last_reset_timestamps", {}).get("daily") # 안전하게 접근
    if last_daily_reset_str:
        try:
            last_daily_reset = datetime.fromisoformat(last_daily_reset_str).astimezone(KST)
        except (ValueError, TypeError):
            pass # 유효하지 않으면 기본값 유지

    last_weekly_reset = datetime.min.replace(tzinfo=KST)
    last_weekly_reset_str = data.get("last_reset_timestamps", {}).get("weekly") # 안전하게 접근
    if last_weekly_reset_str:
        try:
            last_weekly_reset = datetime.fromisoformat(last_weekly_reset_str).astimezone(KST)
        except (ValueError, TypeError):
             pass # 유효하지 않으면 기본값 유지

    # 일일 초기화 시간 (오늘 오전 6시 기준)
    today_reset_base = datetime.now(KST) # 현재 시간 기준
    daily_reset_time = _get_reset_time(today_reset_base, hour=6)

    # 일일 초기화 필요 여부 판단
    # 마지막 초기화 시간이 오늘 6시 기준 시간보다 이전이면 초기화 필요
    if last_daily_reset < daily_reset_time:
        perform_daily_reset(data)
        # last_reset_timestamps 항목이 없으면 생성
        if "last_reset_timestamps" not in data or data["last_reset_timestamps"] is None:
             data["last_reset_timestamps"] = {}
        data["last_reset_timestamps"]["daily"] = now.isoformat() # 초기화 시간 업데이트
        st.rerun() # 초기화 후 화면 갱신 (필수)


    # 주간 초기화 시간 (이번 주 월요일 오전 6시 기준)
    today = now.date()
    monday_date = today - timedelta(days=today.weekday()) # 이번주 월요일 날짜
    this_monday_reset_base = datetime.combine(monday_date, time(0, 0), tzinfo=KST) # 월요일 0시 기준
    weekly_reset_time = _get_reset_time(this_monday_reset_base, hour=6) # 월요일 6시 계산

    # _get_reset_time 함수가 현재 시간이 6시 이전인 경우 하루 전으로 계산하므로
    # 월요일 0시~6시 사이에는 지난주 월요일 6시가 기준이 됩니다. 이 로직은 _get_reset_time 내에 포함되어 있습니다.

    # 주간 초기화 필요 여부 판단
    # 마지막 초기화 시간이 이번 주 월요일 6시 기준 시간보다 이전이면 초기화 필요
    if last_weekly_reset < weekly_reset_time:
        perform_weekly_reset(data)
        # last_reset_timestamps 항목이 없으면 생성
        if "last_reset_timestamps" not in data or data["last_reset_timestamps"] is None:
             data["last_reset_timestamps"] = {}
        data["last_reset_timestamps"]["weekly"] = now.isoformat() # 초기화 시간 업데이트
        st.rerun() # 초기화 후 화면 갱신 (필수)


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
                                       st.success(f"'{selected_char_name_for_modify}' 캐릭터 이름이 '{new_char_name}'(으)로 변경되었습니다.")
                                       st.session_state.selected_char = new_char_name # 선택된 캐릭터 이름도 업데이트
                                       st.rerun() # UI 구조 변경(selectbox 옵션) 반영을 위해 rerun
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
    # selectbox 선택 결과를 session_state에 저장 (다른 곳에서 사용하기 위함)
    st.session_state.selected_char = selected_char_name


    # 선택된 캐릭터 데이터 찾기
    selected_char_data = next((c for c in characters if isinstance(c, dict) and c.get("name") == selected_char_name), None)

    if selected_char_data:
        # --- 캐릭터 이름 표시 (라벨 제거) ---
        st.markdown(f"### {selected_char_name}")

        # --- DAILY ---
        st.header("DAILY")
        # daily_tasks가 없거나 None이면 빈 딕셔너리 사용 (안전한 접근)
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
        # 체크박스 상태 변경 시 공유 상태 및 모든 캐릭터 상태 업데이트
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
                        st.rerun() # 변경사항 즉시 반영
                else:
                     st.text("✔️ 완료")


        # --- DAILY 섹션 끝, 구분선 추가 ---
        st.markdown("---")


        # --- WEEKLY ---
        st.header("WEEKLY")
        # weekly_tasks가 없거나 None이면 빈 딕셔너리 사용 (안전한 접근)
        weekly_tasks = selected_char_data.get("weekly_tasks", {})
        if not isinstance(weekly_tasks, dict): # dict 형태가 아니면 빈 딕셔너리로 초기화
             weekly_tasks = {}
             selected_char_data["weekly_tasks"] = weekly_tasks # 데이터에 반영


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
                     st.rerun() # 변경사항 즉시 반영
             else:
                 st.text("✔️ 완료")

        # --- WEEKLY 섹션 끝, 구분선 추가 ---
        st.markdown("---")


    else:
        # 선택된 캐릭터는 있으나 데이터가 유효하지 않은 경우 메시지
        st.info("선택된 캐릭터 정보가 유효하지 않습니다.")
        # 구분선 추가 (Weekly 섹션 대체)
        st.markdown("---")
        st.markdown("---")


def _render_data_management(data):
    """데이터 관리 섹션 렌더링"""
    st.header("데이터 관리") # 이 헤더는 유지

    # 데이터 관리 팝업 대신 expander 사용 또는 상태 변수로 영역 표시/숨김
    # st.session_state를 사용하여 영역 표시 여부 제어
    show_data_management = st.session_state.get("show_data_management", False)

    if st.button("데이터 관리 열기/닫기", key="toggle_data_management"):
        st.session_state.show_data_management = not show_data_management
        st.rerun() # 영역 표시/숨김 변경 즉시 반영

    if st.session_state.get("show_data_management", False):
        st.subheader("데이터 관리 메뉴")

        # JSON 다운로드
        st.download_button(
            label="JSON 파일 다운로드",
            data=save_data(), # save_data 함수는 호출될 때 최신 상태를 가져옴
            file_name="mabinogi_tasks.json",
            mime="application/json",
            key="download_json"
        )

        # JSON 업로드
        uploaded_file = st.file_uploader("JSON 파일 업로드", type="json", key="upload_json")
        if uploaded_file is not None:
            load_data(uploaded_file) # 파일 업로드 시 로드 함수 호출 (자동 초기화 포함)
            # load_data 함수 내부에서 필요한 경우 rerun 호출

        # 수동 초기화 버튼
        col_reset1, col_reset2 = st.columns(2)
        with col_reset1:
            if st.button("일일 숙제 수동 초기화", key="manual_daily_reset"):
                perform_daily_reset(data)
                # last_reset_timestamps 항목이 없으면 생성
                if "last_reset_timestamps" not in data or data["last_reset_timestamps"] is None:
                    data["last_reset_timestamps"] = {}
                data["last_reset_timestamps"]["daily"] = datetime.now(KST).isoformat() # 수동 초기화 시간 업데이트
                # perform_daily_reset 내에서 success 메시지 표시
                st.rerun() # 화면 갱신 (필수)
        with col_reset2:
            if st.button("주간 숙제 수동 초기화", key="manual_weekly_reset"):
                perform_weekly_reset(data)
                 # last_reset_timestamps 항목이 없으면 생성
                if "last_reset_timestamps" not in data or data["last_reset_timestamps"] is None:
                    data["last_reset_timestamps"] = {}
                data["last_reset_timestamps"]["weekly"] = datetime.now(KST).isoformat() # 수동 초기화 시간 업데이트
                # perform_weekly_reset 내에서 success 메시지 표시
                st.rerun() # 화면 갱신 (필수)


# --- 메인 애플리케이션 로직 ---

st.title("마비노기 모바일 숙제 관리기")

# 데이터 로드 (앱 실행 시 최초 1회 또는 파일 업로드 시)
# 이 함수는 필요한 경우 내부적으로 st.rerun()을 호출할 수 있습니다.
load_data()

# 메인 데이터 가져오기
app_data = st.session_state.data

# --- UI 렌더링 함수 호출 ---
_render_character_management(app_data)

# 구분선 추가 (캐릭터 관리와 숙제 섹션 사이)
st.markdown("---")

_render_tasks(app_data)
# DAILY와 WEEKLY 사이, WEEKLY 하단에 구분선은 _render_tasks 내에 있습니다.

# 구분선 추가 (숙제 섹션과 데이터 관리 섹션 사이)
# _render_tasks 마지막에 WEEKLY 구분선이 있으므로, 여기에 추가하면 구분선 2개가 연달아 표시됨.
# 데이터 관리 헤더 앞에 넣는 것이 더 자연스러움.

_render_data_management(app_data) # 데이터 관리 헤더는 이 함수 내에 있음
# 데이터 관리 섹션 뒤에는 별도 구분선 필요 없음

