import streamlit as st
import json
from datetime import datetime

# 초기 데이터 설정
daily_tasks = {
    "불길한 소환의 결계": {"count": 2, "completed": False},
    "검은 구멍": {"count": 3, "completed": False},
    "요일던전": {"count": 1, "completed": False},
    "아르바이트[오후]": {"count": 1, "completed": False},
    "길드 출석": {"count": 1, "completed": False},
    "망령의 탑": {"daily": False, "completed": False}
}

weekly_tasks = {
    "어비스 - 가라앉은 유적": {"count": 1, "completed": False},
    "어비스 - 무너진 제단": {"count": 1, "completed": False},
    "어비스 - 파멸의 전당": {"count": 1, "completed": False},
    "레이드 - 글라스기브넨": {"count": 1, "completed": False},
    "필드보스 - 페리": {"count": 1, "completed": False},
    "필드보스 - 크라브네흐": {"count": 1, "completed": False},
    "필드보스 - 크라마": {"count": 1, "completed": False},
    "필드보스 재화 교환": {"count": 1, "completed": False},
    "어비스 보상 수령": {"count": 1, "completed": False}
}

characters = []

# 캐릭터 추가/수정/삭제 기능
def add_character(name):
    characters.append(name)

def remove_character(name):
    characters.remove(name)

# JSON 파일 다운로드 및 업로드 기능
def download_json(data):
    json_data = json.dumps(data, ensure_ascii=False)
    st.download_button("JSON 다운로드", json_data, "data.json", "application/json")

def upload_json():
    uploaded_file = st.file_uploader("JSON 파일 업로드", type=["json"])
    if uploaded_file is not None:
        data = json.load(uploaded_file)
        return data

# 숙제 초기화 기능
def reset_daily_tasks():
    for task in daily_tasks:
        daily_tasks[task]["completed"] = False

def reset_weekly_tasks():
    for task in weekly_tasks:
        weekly_tasks[task]["completed"] = False

# UI 구성
st.title("마비노기 모바일 숙제 관리 프로그램")

# 캐릭터 선택
selected_character = st.selectbox("캐릭터 선택", characters)

# 일일 숙제 체크박스
st.header("DAILY")
for task in daily_tasks:
    daily_tasks[task]["completed"] = st.checkbox(task, value=daily_tasks[task]["completed"])

# 주간 숙제 체크박스
st.header("WEEKLY")
for task in weekly_tasks:
    weekly_tasks[task]["completed"] = st.checkbox(task, value=weekly_tasks[task]["completed"])

# 데이터 관리 버튼
if st.button("데이터 관리"):
    st.subheader("데이터 관리")
    download_json({"daily_tasks": daily_tasks, "weekly_tasks": weekly_tasks, "characters": characters})
    upload_data = upload_json()
    if upload_data:
        daily_tasks.update(upload_data.get("daily_tasks", {}))
        weekly_tasks.update(upload_data.get("weekly_tasks", {}))
        characters.extend(upload_data.get("characters", []))

# 숙제 초기화 버튼
if st.button("일일 숙제 초기화"):
    reset_daily_tasks()

if st.button("주간 숙제 초기화"):
    reset_weekly_tasks()
