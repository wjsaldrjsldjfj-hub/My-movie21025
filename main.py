# My-movie21025
import datetime
import pandas as pd
import pytz
import requests
import streamlit as st

# 페이지 기본 설정
st.set_page_config(page_title="일별 박스오피스 조회", page_icon="🎬", layout="wide")


# 캐싱 설정: 동일한 날짜 요청 시 API를 다시 호출하지 않고 1시간(3600초) 동안 결과를 기억합니다.
@st.cache_data(ttl=3600)
def fetch_box_office_data(api_key: str, target_date: str):
    """KOBIS API를 호출하여 해당 날짜의 박스오피스 데이터를 가져오는 함수"""
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {"key": api_key, "targetDt": target_date}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.RequestException as e:
        return None, str(e)


# 1. 배포 서버 시계와 무관하게 한국 시간(KST) 기준 '어제' 날짜 계산
kst_tz = pytz.timezone("Asia/Seoul")
now_kst = datetime.datetime.now(kst_tz)
yesterday_kst = (now_kst - datetime.timedelta(days=1)).date()

st.title("🎬 일별 박스오피스 조회")

# 2. 달력(Date Input)으로 조회할 날짜 선택
# 오늘 데이터는 아직 집계 전이므로 가장 늦게 선택할 수 있는 날짜는 '어제(yesterday_kst)'로 제한합니다.
selected_date = st.date_input(
    "조회할 날짜를 선택하세요 📅",
    value=yesterday_kst,
    max_value=yesterday_kst,
    min_value=datetime.date(2004, 1, 1),  # KOBIS 데이터 제공 시작 시점
    help="오늘 날짜는 아직 집계 전이므로 어제 날짜까지 선택할 수 있습니다.",
)

# API 요청용 날짜 문자열 변환 (YYYYMMDD)
target_dt = selected_date.strftime("%Y%m%d")
# 화면 표시용 날짜 문자열 변환
formatted_date = selected_date.strftime("%Y년 %m월 %d일")

st.markdown(f"### 📅 **{formatted_date}** 박스오피스 결과")

# 3. Streamlit Cloud Secrets에서 API 키 검증 및 가져오기
if "KOBIS_KEY" not in st.secrets:
    st.error(
        """
    🔑 **API 키(KOBIS_KEY)가 설정되지 않았습니다.**

    **확인 사항:**
    1. Streamlit Cloud Dashboard에서 해당 앱의 **Settings -> Secrets** 메뉴로 이동하세요.
    2. 아래와 같이 API 키를 등록했는지 확인해 주세요:
       
```toml
       KOBIS_KEY = "발급받은_인증키_문자열"
