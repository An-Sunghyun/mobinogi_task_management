import streamlit as st
import json
from datetime import datetime, time, date, timedelta
import pytz # 시간대 처리를 위해 필요

# 시간대 설정 (한국 시간)
KST = pytz.timezone('Asia/Seoul')

# 초기 데이터 구조
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

# 초기 숙제 상태 (캐릭터 추가 시 사용)
DEFAULT_DAILY_TASKS = {
  "불길한 소환의 결계": 2,
  "검은 구멍": 3,
  "요일던전": 1,
  "아르바이트[오후]": 1,
  "길드 출석": 0, # 이 값은 shared_tasks와 동기화
  "망령의 탑": {"daily": 0, "complete": False} # daily: 0 미완료, 1 완료
}

DEFAULT_WEEKLY_TASKS = {
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

    # 데이터 로드 후 자동 초기화 확인
    check_and_perform_auto_reset()

def save_data():
    """현재 데이터를 JSON 문자열로 반환"""
    # 저장 시점의 타임스탬프 업데이트
    st.session_state.data["last_reset_timestamps"]["daily"] = datetime.now(KST).isoformat()
    st.session_state.data["last_reset_timestamps"]["weekly"] = datetime.now(KST).isoformat()
    return json.dumps(st.session_state.data, indent=4, ensure_ascii=False)

def perform_daily_reset(data):
    """일일 숙제 초기화 로직 (망령의 탑 완료 제외)"""
    st.info("일일 숙제를 초기화합니다.")
    for char in data["characters"]:
        for task, count in DEFAULT_DAILY_TASKS.items():
            if task != "길드 출석" and task != "망령의 탑":
                 char["daily_tasks"][task] = count
        # 망령의 탑 초기화: daily 상태만 초기화, complete가 False일 경우에만
        # 기본값 처리를 위해 .get() 사용
        if not char["daily_tasks"].get("망령의 탑", {}).get("complete", False):
             char["daily_tasks"]["망령의 탑"] = char["daily_tasks"].get("망령의 탑", {"daily": 0, "complete": False}) # 기본 구조 확인
             char["daily_tasks"]["망령의 탑"]["daily"] = 0 # 0으로 초기화
        # 길드 출석은 공유 상태를 따름
        char["daily_tasks"]["길드 출석"] = data["shared_tasks"]["길드 출석"]


def perform_weekly_reset(data):
    """주간 숙제 초기화 로직"""
    st.info("주간 숙제를 초기화합니다.")
    for char in data["characters"]:
        for task, count in DEFAULT_WEEKLY_TASKS.items():
             char["weekly_tasks"][task] = count
    # 망령의 탑 complete 상태 초기화 (주간 초기화 시에만 해당)
    for char in data["characters"]:
        char["daily_tasks"]["망령의 탑"]["complete"] = False


def check_and_perform_auto_reset():
    """자동 초기화 필요 시 수행"""
    data = st.session_state.data
    now = datetime.now(KST)
    last_daily_reset_str = data["last_reset_timestamps"].get("daily")
    last_weekly_reset_str = data["last_reset_timestamps"].get("weekly")

    try:
        last_daily_reset = datetime.fromisoformat(last_daily_reset_str).astimezone(KST)
    except (ValueError, TypeError):
        last_daily_reset = datetime.min.replace(tzinfo=KST) # 유효하지 않은 경우 아주 과거 시간으로 설정

    try:
        last_weekly_reset = datetime.fromisoformat(last_weekly_reset_str).astimezone(KST)
    except (ValueError, TypeError):
         last_weekly_reset = datetime.min.replace(tzinfo=KST) # 유효하지 않은 경우 아주 과거 시간으로 설정


    # 일일 초기화 시간 (오전 6시)
    today_reset_time = now.replace(hour=6, minute=0, second=0, microsecond=0)
    if now < today_reset_time:
        today_reset_time -= timedelta(days=1) # 아직 6시 전이면 어제의 6시 기준

    # 일일 초기화 필요?
    if last_daily_reset < today_reset_time:
        perform_daily_reset(data)
        data["last_reset_timestamps"]["daily"] = now.isoformat() # 초기화 시간 업데이트
        st.experimental_rerun() # 초기화 후 화면 갱신

    # 주간 초기화 시간 (월요일 오전 6시)
    # 오늘이 월요일 6시 이전이면 지난주 월요일, 아니면 이번주 월요일
    monday = now.date() - timedelta(days=now.weekday()) # 이번주 월요일 날짜
    this_monday_reset_time = datetime.combine(monday, time(6, 0), tzinfo=KST)
    # 만약 지금이 월요일이고 오전 6시 이전이라면, 지난주 월요일 오전 6시가 기준
    if now.weekday() == 0 and now.time() < time(6, 0):
         this_monday_reset_time -= timedelta(days=7)

    # 주간 초기화 필요?
    if last_weekly_reset < this_monday_reset_time:
        perform_weekly_reset(data)
        data["last_reset_timestamps"]["weekly"] = now.isoformat() # 초기화 시간 업데이트
        st.experimental_rerun() # 초기화 후 화면 갱신


# --- Streamlit UI ---

st.title("마비노기 모바일 숙제 관리기")

# 데이터 로드 (앱 실행 시)
load_data()

data = st.session_state.data
characters = data["characters"]
shared_tasks = data["shared_tasks"]

# --- 캐릭터 관리 ---
st.header("캐릭터 관리")
col1, col2, col3 = st.columns(3)

with col1:
    # 캐릭터 추가 (Form 사용)
    with st.form("add_character_form", clear_on_submit=True):
        new_char_name = st.text_input("새 캐릭터 이름 입력:")
        add_button_clicked = st.form_submit_button("캐릭터 추가")

        if add_button_clicked:
            if new_char_name:
                if new_char_name not in [c["name"] for c in characters]:
                    characters.append({
                        "name": new_char_name,
                        "daily_tasks": DEFAULT_DAILY_TASKS.copy(),
                        "weekly_tasks": DEFAULT_WEEKLY_TASKS.copy()
                    })
                    st.session_state.data["characters"] = characters # 데이터 업데이트
                    st.success(f"'{new_char_name}' 캐릭터가 추가되었습니다.")
                    # 새로 추가된 캐릭터를 자동으로 선택하도록 세션 상태 업데이트
                    st.session_state.selected_char = new_char_name
                    st.experimental_rerun() # 변경사항 반영
                else:
                    st.warning("이미 존재하는 이름입니다.")
            else:
                st.warning("캐릭터 이름을 입력해주세요.")


with col2:
    # 캐릭터 수정 (선택된 캐릭터 이름 변경)
    if len(characters) > 0:
        selected_char_name_for_modify = st.session_state.get("selected_char", characters[0]["name"] if characters else None)
        if selected_char_name_for_modify:
             with st.form("modify_character_form", clear_on_submit=False): # clear_on_submit=False로 현재 입력값 유지
                 new_char_name = st.text_input(f"'{selected_char_name_for_modify}'의 새 이름 입력:", value=selected_char_name_for_modify, key="modify_name_input")
                 modify_button_clicked = st.form_submit_button("이름 변경")

                 if modify_button_clicked:
                     if new_char_name and new_char_name != selected_char_name_for_modify:
                        if new_char_name not in [c["name"] for c in characters if c["name"] != selected_char_name_for_modify]: # 다른 캐릭터 이름과 중복 확인
                           for char in characters:
                               if char["name"] == selected_char_name_for_modify:
                                   char["name"] = new_char_name
                                   st.session_state.data["characters"] = characters # 데이터 업데이트
                                   st.success(f"'{selected_char_name_for_modify}' 캐릭터 이름이 '{new_char_name}'(으)로 변경되었습니다.")
                                   st.session_state.selected_char = new_char_name # 선택된 캐릭터 이름도 업데이트
                                   st.experimental_rerun() # 변경사항 반영
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
        if st.button("캐릭터 삭제", key="delete_char_btn"):
            if selected_char_name_for_delete:
                # 삭제 확인 메시지 (선택 사항, 구현 방식 다양)
                # 예시: st.warning이나 st.info로 확인 메시지 표시 후 다른 버튼으로 최종 삭제 실행 등
                # 여기서는 버튼 클릭 시 바로 삭제
                characters = [c for c in characters if c["name"] != selected_char_name_for_delete]
                st.session_state.data["characters"] = characters # 데이터 업데이트
                st.success(f"'{selected_char_name_for_delete}' 캐릭터가 삭제되었습니다.")
                if characters:
                    st.session_state.selected_char = characters[0]["name"] # 삭제 후 첫 번째 캐릭터 선택
                else:
                    st.session_state.selected_char = None # 선택된 캐릭터 없음
                st.experimental_rerun() # 변경사항 반영

st.markdown("---")

# --- 캐릭터 선택 ---
if len(characters) > 0:
    char_names = [c["name"] for c in characters]
    # characters 목록이 비어있지 않을 때만 selectbox 표시
    if st.session_state.get("selected_char") not in char_names:
         # 이전 선택 캐릭터가 삭제되었거나 유효하지 않으면 첫 캐릭터 선택
         st.session_state.selected_char = char_names[0] if char_names else None

    selected_char_name = st.selectbox("캐릭터 선택:", char_names, key="selected_char", index=char_names.index(st.session_state.selected_char) if st.session_state.selected_char in char_names else 0)

    selected_char_data = next((c for c in characters if c["name"] == selected_char_name), None)

    if selected_char_data:
        st.markdown(f"### 현재 캐릭터: {selected_char_name}")

        # --- 일일 숙제 ---
        st.header("일일 숙제")
        daily_tasks = selected_char_data["daily_tasks"]

        # 길드 출석 (공용)
        # 세션 상태 키를 캐릭터 이름 없이 고유하게 설정 (공용이니까)
        shared_guild_checked = st.checkbox("길드 출석 (모든 캐릭터 공유)", value=shared_tasks["길드 출석"] == 1, key="shared_guild_checkbox")
        data["shared_tasks"]["길드 출석"] = 1 if shared_guild_checked else 0
        # 모든 캐릭터의 길드 출석 상태를 공유 상태로 동기화 (매번 렌더링 시)
        for char in characters:
             char["daily_tasks"]["길드 출석"] = data["shared_tasks"]["길드 출석"]


        # 나머지 일일 숙제
        # dictionary copy 후 순회하여 변경 시 오류 방지
        tasks_to_display = list(daily_tasks.items())

        for task, count in tasks_to_display:
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
                      daily_checked = st.checkbox(f"일일 완료", value=daily_done, key=f"{selected_char_name}_{task}_daily")
                      daily_tasks["망령의 탑"]["daily"] = 1 if daily_checked else 0
                 with col_mt2:
                      # key에 캐릭터 이름 포함하여 각 캐릭터별 상태 유지
                      complete_checked = st.checkbox(f"주간 완료 (일일 초기화 안됨)", value=complete_done, key=f"{selected_char_name}_{task}_complete")
                      daily_tasks["망령의 탑"]["complete"] = complete_checked

            else:
                # 횟수 차감 방식
                st.markdown(f"**{task}:** 남은 횟수 {count}")
                if count > 0:
                     # key에 캐릭터 이름 포함
                     if st.button(f"{task} 1회 완료", key=f"{selected_char_name}_{task}_btn"):
                         daily_tasks[task] -= 1
                         st.experimental_rerun() # 변경사항 반영
                else:
                     st.text("✔️ 완료")


        # --- 주간 숙제 ---
        st.header("주간 숙제")
        weekly_tasks = selected_char_data["weekly_tasks"]

        # dictionary copy 후 순회
        weekly_tasks_to_display = list(weekly_tasks.items())

        for task, count in weekly_tasks_to_display:
             st.markdown(f"**{task}:** 남은 횟수 {count}")
             if count > 0:
                 # key에 캐릭터 이름 포함
                 if st.button(f"{task} 1회 완료", key=f"{selected_char_name}_{task}_weekly_btn"):
                     weekly_tasks[task] -= 1
                     st.experimental_rerun() # 변경사항 반영
             else:
                 st.text("✔️ 완료")


    else:
        st.info("선택된 캐릭터 정보가 없습니다. (문제가 발생했거나 삭제된 캐릭터일 수 있습니다)")

else:
    st.info("등록된 캐릭터가 없습니다. 캐릭터를 추가해주세요.")

st.markdown("---") # 구분선

# --- 데이터 관리 푸터 영역 ---
st.header("데이터 관리")

# 데이터 관리 팝업 대신 expander 사용 또는 상태 변수로 영역 표시/숨김
show_data_management = st.session_state.get("show_data_management", False)

if st.button("데이터 관리 열기/닫기"):
    st.session_state.show_data_management = not show_data_management
    st.experimental_rerun()

if st.session_state.get("show_data_management", False):
    #st.container() # 팝업 대신 사용할 컨테이너 - 명시적으로 컨테이너를 쓸 필요는 없습니다.
    st.subheader("데이터 관리 메뉴")

    # JSON 다운로드
    st.download_button(
        label="JSON 파일 다운로드",
        data=save_data(), # save_data 함수는 호출될 때 최신 상태를 가져옴
        file_name="mabinogi_tasks.json",
        mime="application/json"
    )

    # JSON 업로드
    uploaded_file = st.file_uploader("JSON 파일 업로드", type="json")
    if uploaded_file is not None:
        load_data(uploaded_file) # 파일 업로드 시 로드 함수 호출 (자동 초기화 포함)
        # st.experimental_rerun() 은 load_data 안에 이미 있습니다.

    # 수동 초기화 버튼
    col_reset1, col_reset2 = st.columns(2)
    with col_reset1:
        if st.button("일일 숙제 수동 초기화", key="manual_daily_reset"):
            perform_daily_reset(data)
            data["last_reset_timestamps"]["daily"] = datetime.now(KST).isoformat() # 수동 초기화 시간 업데이트
            st.success("일일 숙제가 수동으로 초기화되었습니다.")
            st.experimental_rerun() # 화면 갱신
    with col_reset2:
        if st.button("주간 숙제 수동 초기화", key="manual_weekly_reset"):
            perform_weekly_reset(data)
            data["last_reset_timestamps"]["weekly"] = datetime.now(KST).isoformat() # 수동 초기화 시간 업데이트
            st.success("주간 숙제가 수동으로 초기화되었습니다.")
            st.experimental_rerun() # 화면 갱신
