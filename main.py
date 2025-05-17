import streamlit as st
import json
import os
from datetime import datetime, timedelta

# 버전 정보
VERSION = "Mobinogi Task Management Ver0.001"

# 기본 JSON 파일 경로
DATA_FILE = "task_data.json"

# 초기 데이터 구조
def get_initial_data():
    return {
        "characters": [],
        "daily_tasks": {},
        "weekly_tasks": {},
        "guild_attendance": False,
        "mangryong": {"daily": False, "complete": False},
        "last_daily_reset": "",
        "last_weekly_reset": ""
    }

# JSON 데이터 로드 또는 초기화
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return get_initial_data()

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 초기화 함수들
def reset_daily_tasks(data):
    data["daily_tasks"] = {char: {k: False for k in ["불길한 소환의 결계1", "불길한 소환의 결계2", "검은 구멍1", "검은 구멍2", "검은 구멍3", "요일던전", "아르바이트"]} for char in data["characters"]}
    data["guild_attendance"] = False
    if not data["mangryong"]["complete"]:
        data["mangryong"]["daily"] = False
    data["last_daily_reset"] = datetime.now().isoformat()

def reset_weekly_tasks(data):
    data["weekly_tasks"] = {char: {k: False for k in [
        "어비스 - 가라앉은 유적", "어비스 - 무너진 제단", "어비스 - 파멸의 전당", "레이드 - 글라스기브넨",
        "필드보스 - 페리", "필드보스 - 크라브네흐", "필드보스 - 크라마", "필드보스 재화 교환", "어비스 보상 수령"]} for char in data["characters"]}
    data["last_weekly_reset"] = datetime.now().isoformat()

# 자동 초기화 로직
def check_and_reset(data):
    now = datetime.now()
    # 일일 초기화
    last_daily = datetime.fromisoformat(data["last_daily_reset"]) if data["last_daily_reset"] else now - timedelta(days=1)
    if now.date() > last_daily.date() and now.hour >= 6:
        reset_daily_tasks(data)
    # 주간 초기화
    last_weekly = datetime.fromisoformat(data["last_weekly_reset"]) if data["last_weekly_reset"] else now - timedelta(weeks=1)
    if now.isoweekday() == 1 and (now - last_weekly).days >= 7 and now.hour >= 6:
        reset_weekly_tasks(data)

# Streamlit UI
def main():
    st.set_page_config(layout="wide")
    st.title(VERSION)

    data = load_data()
    check_and_reset(data)

    # 캐릭터 선택 및 관리
    cols = st.columns([4, 1, 1, 1])
    with cols[0]:
        selected_character = st.selectbox("캐릭터 선택", data["characters"] if data["characters"] else ["캐릭터 없음"])
    with cols[1]:
        if st.button("캐릭터 추가"):
            name = st.text_input("새 캐릭터 이름 입력", key="add_char")
            if name and name not in data["characters"]:
                data["characters"].append(name)
                reset_daily_tasks(data)
                reset_weekly_tasks(data)
                save_data(data)
                st.experimental_rerun()
    with cols[2]:
        if st.button("캐릭터 수정"):
            new_name = st.text_input("새 이름", key="edit_char")
            if new_name and selected_character in data["characters"]:
                index = data["characters"].index(selected_character)
                data["characters"][index] = new_name
                save_data(data)
                st.experimental_rerun()
    with cols[3]:
        if st.button("캐릭터 삭제"):
            if selected_character in data["characters"]:
                data["characters"].remove(selected_character)
                data["daily_tasks"].pop(selected_character, None)
                data["weekly_tasks"].pop(selected_character, None)
                save_data(data)
                st.experimental_rerun()

    # TODO: 일일/주간 숙제 UI 및 데이터 관리 화면 구현

    # Footer
    with st.expander("데이터 관리"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("JSON 다운로드"):
                st.download_button("다운로드", json.dumps(data, ensure_ascii=False, indent=4), file_name="mobinogi_data.json")
        with col2:
            uploaded = st.file_uploader("JSON 업로드", type=["json"])
            if uploaded:
                loaded = json.load(uploaded)
                save_data(loaded)
                st.success("업로드 완료. 새로고침됩니다.")
                st.experimental_rerun()
        with col3:
            if st.button("일일 숙제 초기화"):
                reset_daily_tasks(data)
                save_data(data)
                st.experimental_rerun()
        with col4:
            if st.button("주간 숙제 초기화"):
                reset_weekly_tasks(data)
                save_data(data)
                st.experimental_rerun()

    save_data(data)

if __name__ == "__main__":
    main()
