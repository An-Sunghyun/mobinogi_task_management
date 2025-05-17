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

# 일일 숙제 목록 및 초기 횟수/상태
DAILY_TASK_TEMPLATE = {
    "불길한 소환의 결계": 2,
    "검은 구멍": 3,
    "요일던전": 1,
    "아르바이트[오후]": 1,
    "길드 출석": 0, # 이 값은 shared_tasks와 동기화
    "망령의 탑": {"daily": 0, "complete": False} # daily: 0 미완료, 1 완료
}

# 주간 숙제 목록 및 초기 횟수
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
    reset_time = base_datetime.replace(hour=hour, minute=minute, second=0, microsecond=0)
    # 기준 시간이 reset_time보다 빠르면 하루 전으로 설정 (예: 현재 시간이 02시인데 reset_time이 06시면 어제 06시가 기준)
    if base_datetime < reset_time:
        reset_time -= timedelta(days=1)
    return reset_time.astimezone(KST) # 한국 시간대로 보정

def perform_daily_reset(data):
    """일일 숙제 초기화 로직 (망령의 탑 완료 제외)"""
    st.info("일일 숙제를 초기화합니다.")
    for char in data["characters"]:
        # 템플릿을 기반으로 초기화
        for task, initial_state in DAILY_TASK_TEMPLATE.items():
            if task == "길드 출석":
                # 길드 출석은 공유 상태를 따름
                char["daily_tasks"][task] = data["shared_tasks"]["길드 출석"]
            elif task == "망령의 탑":
                 # 망령의 탑 초기화: daily 상태만 초기화, complete가 False일 경우에만
                 mt_state = char["daily_tasks"].get("망령의 탑", {"daily": 0, "complete": False}) # 현재 상태 가져오기
                 if not mt_state.get("complete", False):
                     char["daily_tasks"]["망령의 탑"]["daily"] = 0 # 일일 상태 초기화
            else:
                 char["daily_tasks"][task] = initial_state # 횟수 초기화


def perform_weekly_reset(data):
    """주간 숙제 초기화 로직"""
    st.info("주간 숙제를 초기화합니다.")
    for char in data["characters"]:
        # 템플릿을 기반으로 초기화
        for task, initial_state in WEEKLY_TASK_TEMPLATE.items():
             char["weekly_tasks"][task] = initial_state
        # 망령의 탑 complete 상태 초기화 (주간 초기화 시에만 해당)
        char["daily_tasks"]["망령의 탑"]["complete"] = False


def check_and_perform_auto_reset():
    """자동 초기화 필요 시 수행"""
    data = st.session_state.data
    now = datetime.now(KST)

    # 마지막 초기화 시간 가져오기 (없으면 아주 과거 시간으로 설정)
    last_daily_reset_str = data["last_reset_timestamps"].get("daily", datetime.min.replace(tzinfo=KST).isoformat())
    last_weekly_reset_str = data["last_reset_timestamps"].get("weekly", datetime.min.replace(tzinfo=KST).isoformat())

    try:
        last_daily_reset = datetime.fromisoformat(last_daily_reset_str).astimezone(KST)
    except (ValueError, TypeError):
        last_daily_reset = datetime.min.replace(tzinfo=KST) # 유효하지 않은 경우 아주 과거 시간으로 설정

    try:
        last_weekly_reset = datetime.fromisoformat(last_weekly_reset_str).astimezone(KST)
    except (ValueError, TypeError):
         last_weekly_reset = datetime.min.replace(tzinfo=KST) # 유효하지 않은 경우 아주 과거 시간으로 설정

    # 일일 초기화 시간 (오늘 오전 6시 기준)
    today_reset_ 기준 = datetime.now(KST) # 현재 시간 기준
    daily_reset_time = _get_reset_time(today_reset_ 기준, hour=6)

    # 일일 초기화 필요 여부 판단
    if last_daily_reset < daily_reset_time:
        perform_daily_reset(data)
        data["last_reset_timestamps"]["daily"] = now.isoformat() # 초기화 시간 업데이트
        st.rerun() # 초기화 후 화면 갱신 (필수)


    # 주간 초기화 시간 (이번 주 월요일 오전 6시 기준)
    today = now.date()
    monday_date = today - timedelta(days=today.weekday()) # 이번주 월요일 날짜
    this_monday_reset_기준 = datetime.combine(monday_date, time(0, 0), tzinfo=KST) # 월요일 0시 기준
    weekly_reset_time = _get_reset_time(this_monday_reset_기준, hour=6) # 월요일 6시 계산

     # 만약 현재 시간이 월요일 0시 ~ 6시 사이라면, 주간 초기화 기준은 지난주 월요일 6시가 되어야 함
    if now.weekday() == 0 and now.time() < time(6,0):
         weekly_reset_time -= timedelta(days=7)


    # 주간 초기화 필요 여부 판단
    if last_weekly_reset < weekly_reset_time:
        perform_weekly_reset(data)
        data["last_reset_timestamps"]["weekly"] = now.isoformat() # 초기화 시간 업데이트
        st.rerun() # 초기화 후 화면 갱신 (필수)


# --- UI 렌더링 함수 ---

def _render_character_management(data):
    """캐릭터 관리 섹션 렌더링"""
    st.header("캐릭터 관리")
    characters = data["characters"]
    col1, col2, col3 = st.columns(3)

    with col1:
        # 캐릭터 추가 (Form 사용)
        with st.form("add_character_form", clear_on_submit=True):
            new_char_name = st.text_input("새 캐릭터 이름 입력:")
            add_button_clicked = st.form_submit_button("캐릭터 추가")

            if add_button_clicked:
                if new_char_name:
                    if new_char_name not in [c["name"] for c in characters]:
                        # 새 캐릭터 데이터 추가 (템플릿 복사)
                        characters.append({
                            "name": new_char_name,
                            "daily_tasks": DAILY_TASK_TEMPLATE.copy(),
                            "weekly_tasks": WEEKLY_TASK_TEMPLATE.copy()
                        })
                        # 길드 출석 상태는 현재 공유 상태로 초기화
                        characters[-1]["daily_tasks"]["길드 출석"] = data["shared_tasks"]["길드 출석"]

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
            selected_char_name_for_modify = st.session_state.get("selected_char", characters[0]["name"])
            # 현재 선택된 캐릭터가 삭제되었을 경우 대비
            if selected_char_name_for_modify not in [c["name"] for c in characters]:
                 selected_char_name_for_modify = characters[0]["name"] if characters else None


            if selected_char_name_for_modify:
                 with st.form("modify_character_form", clear_on_submit=False): # clear_on_submit=False로 현재 입력값 유지
                     new_char_name = st.text_input(f"'{selected_char_name_for_modify}'의 새 이름 입력:", value=selected_char_name_for_modify, key="modify_name_input")
                     modify_button_clicked = st.form_submit_button("이름 변경")

                     if modify_button_clicked:
                         if new_char_name and new_char_name != selected_char_name_for_modify:
                            # 다른 캐릭터 이름과 중복 확인
                            if new_char_name not in [c["name"] for c in characters if c["name"] != selected_char_name_for_modify]:
                               for char in characters:
                                   if char["name"] == selected_char_name_for_modify:
                                       char["name"] = new_char_name
                                       st.success(f"'{selected_char_name_for_modify}' 캐릭터 이름이 '{new_char_name}'(으)로 변경되었습니다.")
                                       st.session_state.selected_char = new_char_name # 선택된 캐릭터 이름도 업데이트
                                       st.rerun() # UI 구조 변경(selectbox 옵션) 반영을 위해 rerun
                                       break
                            else:
                                st.warning("이미 존재하는 이름입니다.")
                         elif new_char_name == selected_char_name_for_modify:
                             st.info("이름 변경이 없습니다.")
                         else:
                             st.warning("새 캐릭터 이름을 입력해주세요.")


    with col3:
        # 캐릭터 삭제
        if len(characters) > 0:
            selected_char_name_for_delete = st.session_state.get("selected_char", characters[0]["name"])
            # 현재 선택된 캐릭터가 삭제되었을 경우 대비
            if selected_char_name_for_delete not in [c["name"] for c in characters]:
                 selected_char_name_for_delete = characters[0]["name"] if characters else None

            if selected_char_name_for_delete:
                # 삭제 확인 메시지 추가 (선택 사항)
                if st.button(f"'{selected_char_name_for_delete}' 캐릭터 삭제", key="delete_char_btn"):
                    # 실제로 삭제
                    characters[:] = [c for c in characters if c["name"] != selected_char_name_for_delete] # 슬라이싱으로 원본 리스트 직접 수정
                    st.success(f"'{selected_char_name_for_delete}' 캐릭터가 삭제되었습니다.")
                    if characters:
                        st.session_state.selected_char = characters[0]["name"] # 삭제 후 첫 번째 캐릭터 선택
                    else:
                        st.session_state.selected_char = None # 선택된 캐릭터 없음
                    st.rerun() # UI 구조 변경(selectbox 옵션) 반영을 위해 rerun
            else:
                 st.text("삭제할 캐릭터 없음") # 캐릭터가 0개일 때

    st.markdown("---") # 구분선


def _render_tasks(data):
    """숙제 목록 섹션 렌더링"""
    characters = data["characters"]
    shared_tasks = data["shared_tasks"]

    if len(characters) > 0:
        char_names = [c["name"] for c in characters]
        # 현재 선택된 캐릭터 이름이 유효한지 확인하고 필요시 업데이트
        if st.session_state.get("selected_char") not in char_names:
             st.session_state.selected_char = char_names[0] if char_names else None

        # 캐릭터 선택 selectbox
        selected_char_name = st.selectbox(
            "캐릭터 선택:",
            char_names,
            key="selected_char",
            index=char_names.index(st.session_state.selected_char) if st.session_state.selected_char in char_names else 0
        )

        selected_char_data = next((c for c in characters if c["name"] == selected_char_name), None)

        if selected_char_data:
            st.markdown(f"### 현재 캐릭터: {selected_char_name}")

            # --- 일일 숙제 ---
            st.header("일일 숙제")
            daily_tasks = selected_char_data["daily_tasks"]

            # 길드 출석 (공용) - 모든 캐릭터의 상태 동기화
            shared_guild_checked = st.checkbox(
                "길드 출석 (모든 캐릭터 공유)",
                value=shared_tasks["길드 출석"] == 1,
                key="shared_guild_checkbox" # 공유 상태는 고유 키 사용
            )
            # 체크박스 상태 변경 시 공유 상태 및 모든 캐릭터 상태 업데이트
            if (shared_tasks["길드 출석"] == 0 and shared_guild_checked) or (shared_tasks["길드 출석"] == 1 and not shared_guild_checked):
                 data["shared_tasks"]["길드 출석"] = 1 if shared_guild_checked else 0
                 for char in characters:
                      char["daily_tasks"]["길드 출석"] = data["shared_tasks"]["길드 출석"]
                 # 상태 변경 후 화면 갱신 (필요시) - 여기서는 체크박스 변경 자체가 rerun을 유발
                 # st.rerun() # 불필요한 rerun 제거


            # 나머지 일일 숙제 목록 표시
            for task, current_state in daily_tasks.items():
                if task == "길드 출석":
                    continue # 이미 위에서 처리함

                if task == "망령의 탑":
                    # 망령의 탑은 일일/완료 두 가지 상태 관리
                    mt_state = daily_tasks.get("망령의 탑", {"daily": 0, "complete": False}) # 기본값 처리
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
                        if (daily_tasks["망령의 탑"].get("daily", 0) == 0 and daily_checked) or (daily_tasks["망령의 탑"].get("daily", 1) == 1 and not daily_checked):
                            daily_tasks["망령의 탑"]["daily"] = 1 if daily_checked else 0
                            # st.rerun() # 불필요한 rerun 제거

                    with col_mt2:
                        # key에 캐릭터 이름 포함하여 각 캐릭터별 상태 유지
                        complete_checked = st.checkbox(
                            f"주간 완료 (일일 초기화 안됨)",
                            value=complete_done,
                            key=f"{selected_char_name}_{task}_complete_checkbox"
                        )
                         # 체크박스 상태 변경 시 데이터 업데이트
                        if (daily_tasks["망령의 탑"].get("complete", False) == False and complete_checked) or (daily_tasks["망령의 탑"].get("complete", True) == True and not complete_checked):
                             daily_tasks["망령의 탑"]["complete"] = complete_checked
                             # st.rerun() # 불필요한 rerun 제거


                else:
                    # 횟수 차감 방식
                    count = current_state # 남은 횟수
                    st.markdown(f"**{task}:** 남은 횟수 {count}")
                    if count > 0:
                        # key에 캐릭터 이름 포함
                        if st.button(f"{task} 1회 완료", key=f"{selected_char_name}_{task}_daily_btn"):
                            daily_tasks[task] -= 1
                            # st.rerun() # 불필요한 rerun 제거 (session_state 변경으로 충분)


            # --- 주간 숙제 ---
            st.header("주간 숙제")
            weekly_tasks = selected_char_data["weekly_tasks"]

            # 주간 숙제 목록 표시
            for task, count in weekly_tasks.items():
                 st.markdown(f"**{task}:** 남은 횟수 {count}")
                 if count > 0:
                     # key에 캐릭터 이름 포함
                     if st.button(f"{task} 1회 완료", key=f"{selected_char_name}_{task}_weekly_btn"):
                         weekly_tasks[task] -= 1
                         # st.rerun() # 불필요한 rerun 제거 (session_state 변경으로 충분)
                 else:
                     st.text("✔️ 완료")


        else:
            st.info("선택된 캐릭터 정보가 없습니다. (목록에서 캐릭터를 선택해주세요)")

    else:
        st.info("등록된 캐릭터가 없습니다. 캐릭터 관리에서 캐릭터를 추가해주세요.")

    st.markdown("---") # 구분선


def _render_data_management(data):
    """데이터 관리 섹션 렌더링"""
    st.header("데이터 관리")

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
                data["last_reset_timestamps"]["daily"] = datetime.now(KST).isoformat() # 수동 초기화 시간 업데이트
                st.success("일일 숙제가 수동으로 초기화되었습니다.")
                st.rerun() # 화면 갱신 (필수)
        with col_reset2:
            if st.button("주간 숙제 수동 초기화", key="manual_weekly_reset"):
                perform_weekly_reset(data)
                data["last_reset_timestamps"]["weekly"] = datetime.now(KST).isoformat() # 수동 초기화 시간 업데이트
                st.success("주간 숙제가 수동으로 초기화되었습니다.")
                st.rerun() # 화면 갱신 (필수)


# --- 메인 애플리케이션 로직 ---

st.title("마비노기 모바일 숙제 관리기")

# 데이터 로드 (앱 실행 시 최초 1회 또는 파일 업로드 시)
load_data()

# 메인 데이터 가져오기
app_data = st.session_state.data

# --- UI 렌더링 함수 호출 ---
_render_character_management(app_data)
_render_tasks(app_data)
_render_data_management(app_data)

