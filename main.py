import streamlit as st
import datetime
import json
from streamlit.components.v1 import html

# -------------------------
# 앱 버전 정보
# -------------------------
APP_NAME = "Mobinogi Task Management"
VERSION = "V0.01"

# -------------------------
# 페이지 설정
# -------------------------
st.set_page_config(
    page_title=f"{APP_NAME} {VERSION}",
    layout="centered",
)

# -------------------------
# 태스크 정의
# -------------------------
DAILY_TASKS = [
    {"id": "불길한_소환의_결계", "label": "불길한 소환의 결계", "exclude": False},
    {"id": "심층으로_떨린_검은_구멍", "label": "심층으로 떨린 검은 구멍", "exclude": False},
    {"id": "일일_아르바이트", "label": "일일 아르바이트", "exclude": False},
    {"id": "요일_던전", "label": "요일 던전", "exclude": False},
    {"id": "길드_출석", "label": "길드 출석", "exclude": False},
    {"id": "망령의_탑", "label": "망령의 탑", "exclude": True},
]
WEEKLY_TASKS = [
    {"id": "어비스_가라앉은_유적", "label": "어비스 - 가라앉은 유적"},
    {"id": "어비스_무너진_제단", "label": "어비스 - 무너진 제단"},
    {"id": "어비스_파멸의_전당", "label": "어비스 - 파멸의 전당"},
    {"id": "레이드_글라스기브넨", "label": "레이드 - 글라스기브넨"},
    {"id": "필드보스_페리", "label": "필드보스 - 페리"},
    {"id": "필드보스_크라브니흐", "label": "필드보스 - 크라브니흐"},
    {"id": "필드보스_크라마", "label": "필드보스 - 크라마"},
    {"id": "필드보스_재화_교환", "label": "필드보스 재화 교환"},
    {"id": "어비스_보상_수령", "label": "어비스 보상 수령"},
    {"id": "냥원랜드", "label": "냥원랜드"},
]

# -------------------------
# 상태 초기화
# -------------------------
def init_state():
    st.session_state.setdefault('characters', ['오덕왕의석궁병'])
    st.session_state.setdefault('selected_char', st.session_state.characters[0])
    if 'data' not in st.session_state:
        st.session_state.data = {
            char: {
                'daily': {t['id']: False for t in DAILY_TASKS},
                'weekly': {t['id']: False for t in WEEKLY_TASKS},
                'last_daily': None,
                'last_weekly': None,
            }
            for char in st.session_state.characters
        }

# -------------------------
# 로컬스토리지 연동: JS 초기 로드
# -------------------------
html(
    """
    <script>
      const data = localStorage.getItem('tasksData');
      const params = new URLSearchParams(window.location.search);
      if (data && !params.has('initialData')) {
        window.location.replace(window.location.pathname + '?initialData=' + encodeURIComponent(data));
      }
    </script>
    """,
    height=0,
)

# -------------------------
# Python: URL 파라미터 로드
# -------------------------
def load_persistent_data():
    try:
        param = st.query_params.get('initialData', [None])[0]
        if param:
            return json.loads(param)
    except Exception:
        pass
    return None

persist = load_persistent_data()
if persist is not None:
    # 방어 로직: 필수 구조 검사
    for char, info in persist.items():
        if not isinstance(info, dict) or 'daily' not in info or 'weekly' not in info:
            persist = None
            break

if persist:
    # characters 재설정
    chars = list(persist.keys()) or st.session_state.characters
    st.session_state.characters = chars
    st.session_state.selected_char = st.session_state.selected_char if st.session_state.selected_char in chars else chars[0]
    st.session_state.data = {}
    for char in chars:
        stored = persist.get(char, {})
        # 방어: missing keys
        daily = {t['id']: bool(stored.get('daily', {}).get(t['id'], False)) for t in DAILY_TASKS}
        weekly = {t['id']: bool(stored.get('weekly', {}).get(t['id'], False)) for t in WEEKLY_TASKS}
        st.session_state.data[char] = {'daily': daily, 'weekly': weekly, 'last_daily': None, 'last_weekly': None}
    st.experimental_set_query_params()
else:
    init_state()

# -------------------------
# 업데이트 및 방어 로직
# -------------------------
def get_persistent_snapshot():
    return {
        char: {'daily': info['daily'], 'weekly': info['weekly']}
        for char, info in st.session_state.data.items()
    }

# 저장: 날짜형 제거, 순수 bool 값만 저장
# 방어 로직: exceptions 감지
# -------------------------
def update_localstorage():
    try:
        snapshot = get_persistent_snapshot()
        data_str = json.dumps(snapshot, ensure_ascii=False)
        html(
            f"""
            <script>
              localStorage.setItem('tasksData', `{data_str}`);
            </script>
            """,
            height=0,
        )
    except Exception as e:
        st.error(f"저장 중 오류 발생: {e}")

# -------------------------
# 자동 리셋 로직 (매일 6시, 매주 월요일 6시)
# -------------------------
def get_monday(dt):
    return dt - datetime.timedelta(days=dt.weekday())

def reset_if_needed():
    now = datetime.datetime.now()
    for char, info in st.session_state.data.items():
        # 일일 리셋
        last = info.get('last_daily')
        if last is None or (now.date() > last and now.hour >= 6):
            for t in DAILY_TASKS:
                if not t['exclude']:
                    info['daily'][t['id']] = False
            info['last_daily'] = now.date()
        # 주간 리셋
        lastw = info.get('last_weekly')
        monday = get_monday(now)
        if lastw is None or (lastw < monday.date() and now.hour >= 6):
            for t in WEEKLY_TASKS:
                info['weekly'][t['id']] = False
            info['last_weekly'] = now.date()

# -------------------------
# 수동 초기화 함수
# -------------------------
def manual_daily_reset():
    for info in st.session_state.data.values():
        for t in DAILY_TASKS:
            if not t['exclude']:
                info['daily'][t['id']] = False
    update_localstorage()


def manual_weekly_reset():
    for info in st.session_state.data.values():
        for t in WEEKLY_TASKS:
            info['weekly'][t['id']] = False
    update_localstorage()

# -------------------------
# 메인 렌더링
# -------------------------
def main():
    reset_if_needed()

    st.title(f"{APP_NAME} {VERSION}")

    # 캐릭터 선택
    char = st.selectbox(
        "캐릭터 선택",
        st.session_state.characters,
        index=st.session_state.characters.index(st.session_state.selected_char),
        on_change=update_localstorage,
        key="selected_char"
    )
    info = st.session_state.data[char]

    # DAILY
    st.header("DAILY")
    cols = st.columns(2)
    for idx, t in enumerate(DAILY_TASKS):
        cb = st.checkbox(
            t['label'],
            value=info['daily'][t['id']],
            key=f"d_{t['id']}",
            on_change=update_localstorage
        )
        info['daily'][t['id']] = cb

    # WEEKLY
    st.header("WEEKLY")
    for t in WEEKLY_TASKS:
        cb = st.checkbox(
            t['label'],
            value=info['weekly'][t['id']],
            key=f"w_{t['id']}",
            on_change=update_localstorage
        )
        info['weekly'][t['id']] = cb

    # 데이터 관리
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("일일 숙제 수동 초기화"):
            manual_daily_reset()
    with c2:
        if st.button("주간 숙제 수동 초기화"):
            manual_weekly_reset()

    # 항상 저장
    update_localstorage()

if __name__ == '__main__':
    main()
