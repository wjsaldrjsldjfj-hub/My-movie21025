# My-movie21025
```python
# ============================================
# 어제의 박스오피스 앱
# KOBIS Open API + Streamlit
# ============================================

import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# --------------------------------------------
# 1. 기본 페이지 설정
# --------------------------------------------

st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide"
)


# --------------------------------------------
# 2. 제목과 설명
# --------------------------------------------

st.title("🎬 어제의 박스오피스")

st.caption(
    "한국영화진흥위원회(KOBIS) 일별 박스오피스 데이터를 "
    "한국 시간 기준 '어제' 날짜로 조회합니다."
)


# --------------------------------------------
# 3. 한국 시간 기준으로 '어제' 날짜 계산
# --------------------------------------------
# Streamlit Cloud 서버가 한국 시간이 아닐 수도 있기 때문에
# 서버의 현재 시간을 그대로 사용하지 않습니다.
#
# ZoneInfo를 사용해서 현재 시간을 한국 시간(KST)으로 바꾼 뒤
# 하루를 빼서 '어제'를 계산합니다.

KST = ZoneInfo("Asia/Seoul")

now_kst = datetime.now(KST)
yesterday_kst = now_kst - timedelta(days=1)

# KOBIS API가 요구하는 날짜 형식: YYYYMMDD
target_date = yesterday_kst.strftime("%Y%m%d")

# 화면에 보여줄 날짜 형식: YYYY년 MM월 DD일
display_date = yesterday_kst.strftime("%Y년 %m월 %d일")


# --------------------------------------------
# 4. KOBIS API 주소
# --------------------------------------------

API_URL = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
    "boxoffice/searchDailyBoxOfficeList.json"
)


# --------------------------------------------
# 5. KOBIS API 호출 함수
# --------------------------------------------
# @st.cache_data를 사용하면 같은 날짜의 API 결과를
# 1시간 동안 저장해 둡니다.
#
# 따라서 사용자가 새로고침하거나 같은 날짜를 다시 조회해도
# 매번 KOBIS API를 다시 요청하지 않습니다.

@st.cache_data(ttl=3600)
def get_boxoffice(target_dt):
    """
    KOBIS API에서 해당 날짜의 일별 박스오피스를 가져옵니다.

    캐시 시간:
    3600초 = 1시간
    """

    # Streamlit의 비밀 금고에서 인증키를 가져옵니다.
    # 실제 인증키를 코드에 직접 작성하지 않습니다.
    try:
        api_key = st.secrets["KOBIS_KEY"]
    except Exception:
        return {
            "success": False,
            "error_type": "secret",
            "message": (
                "KOBIS_KEY를 찾을 수 없습니다. "
                "Streamlit Cloud의 Secrets에 KOBIS_KEY가 등록되어 있는지 확인하세요."
            ),
            "data": None
        }

    # KOBIS API에 보낼 요청값
    params = {
        "key": api_key,
        "targetDt": target_dt
    }

    try:
        # API 요청
        response = requests.get(
            API_URL,
            params=params,
            timeout=10
        )

        # HTTP 오류가 있는 경우 처리
        response.raise_for_status()

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error_type": "network",
            "message": (
                "KOBIS API 요청 시간이 초과되었습니다. "
                "잠시 후 다시 실행해 보세요."
            ),
            "data": None
        }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error_type": "network",
            "message": (
                "KOBIS API에 접속하지 못했습니다. "
                "인터넷 연결이나 KOBIS API 서버 상태를 확인하세요."
            ),
            "data": None
        }

    # JSON으로 변환
    try:
        result = response.json()
    except ValueError:
        return {
            "success": False,
            "error_type": "json",
            "message": (
                "KOBIS API가 올바른 JSON 데이터를 반환하지 않았습니다. "
                "API 주소나 KOBIS 서버 상태를 확인하세요."
            ),
            "data": None
        }

    # ----------------------------------------
    # 인증키 오류 확인
    # ----------------------------------------
    # KOBIS는 인증키가 틀려도 HTTP 상태코드가 200일 수 있습니다.
    # 대신 faultInfo가 들어오기 때문에 반드시 확인해야 합니다.

    if "faultInfo" in result:
        fault_info = result["faultInfo"]

        # 오류 메시지를 최대한 읽기 쉽게 가져옵니다.
        if isinstance(fault_info, dict):
            fault_code = fault_info.get("faultCode", "")
            fault_string = fault_info.get("message", "")

            if not fault_string:
                fault_string = fault_info.get("faultString", "")

            error_message = "KOBIS API 오류가 발생했습니다."

            if fault_code:
                error_message += f"\n\n오류 코드: {fault_code}"

            if fault_string:
                error_message += f"\n\n오류 내용: {fault_string}"

        else:
            error_message = (
                "KOBIS API에서 오류(faultInfo)를 반환했습니다.\n\n"
                f"{fault_info}"
            )

        return {
            "success": False,
            "error_type": "fault",
            "message": error_message,
            "data": None
        }

    # ----------------------------------------
    # boxOfficeResult 확인
    # ----------------------------------------

    boxoffice_result = result.get("boxOfficeResult")

    if not boxoffice_result:
        return {
            "success": False,
            "error_type": "empty_result",
            "message": (
                "API 응답에 boxOfficeResult가 없습니다. "
                "KOBIS API 응답 형식을 확인하세요."
            ),
            "data": None
        }

    # ----------------------------------------
    # 영화 목록 가져오기
    # ----------------------------------------

    movie_list = boxoffice_result.get("dailyBoxOfficeList", [])

    # 영화 목록이 비어 있는 경우
    if not movie_list:
        return {
            "success": False,
            "error_type": "empty",
            "message": (
                "해당 날짜의 박스오피스 영화 목록이 비어 있습니다.\n\n"
                "조회 날짜가 정상적인지, KOBIS에서 해당 날짜의 "
                "일별 박스오피스 데이터가 집계되었는지 확인하세요."
            ),
            "data": None
        }

    return {
        "success": True,
        "error_type": None,
        "message": None,
        "data": movie_list
    }


# --------------------------------------------
# 6. API 호출
# --------------------------------------------

result = get_boxoffice(target_date)


# --------------------------------------------
# 7. API 오류 처리
# --------------------------------------------

if not result["success"]:

    st.error("박스오피스 데이터를 불러오지 못했습니다.")

    st.warning(result["message"])

    # 오류 종류에 따라 초보자가 확인할 내용을 추가로 표시
    if result["error_type"] == "secret":
        st.info(
            """
            **확인할 것**

            1. Streamlit Cloud의 앱 화면에서 **Settings**로 들어갑니다.
            2. **Secrets** 메뉴를 엽니다.
            3. 아래처럼 인증키가 등록되어 있는지 확인합니다.

            `KOBIS_KEY = "발급받은_KOBIS_인증키"`

            인증키를 `main.py`에 직접 넣을 필요는 없습니다.
            """
        )

    elif result["error_type"] == "fault":
        st.info(
            """
            **확인할 것**

            KOBIS API는 인증키가 잘못되어도 HTTP 상태코드가 200으로
            올 수 있습니다.

            따라서 위에 표시된 `faultInfo`의 오류 내용을 확인하세요.

            특히 인증키가 정확하게 등록되어 있는지 확인하세요.
            """
        )

    elif result["error_type"] == "empty":
        st.info(
            f"""
            **확인할 것**

            현재 조회 날짜는 **{display_date}**입니다.

            KOBIS에서 해당 날짜의 일별 박스오피스 데이터가
            아직 제공되지 않았거나 데이터가 없을 수 있습니다.
            """
        )

    elif result["error_type"] == "network":
        st.info(
            """
            **확인할 것**

            - 인터넷 연결 상태
            - KOBIS API 서버 상태
            - KOBIS API 주소
            - 잠시 후 다시 실행

            등을 확인해 보세요.
            """
        )

    # 오류가 있으면 아래의 정상 화면은 표시하지 않습니다.
    st.stop()


# --------------------------------------------
# 8. 데이터를 표 형태로 변환
# --------------------------------------------

movie_list = result["data"]

df = pd.DataFrame(movie_list)


# --------------------------------------------
# 9. 숫자 데이터를 실제 숫자로 변환
# --------------------------------------------
# KOBIS API에서는 rank, audiCnt, audiAcc, scrnCnt 등이
# 문자열로 들어옵니다.
#
# 그래프와 정렬을 제대로 사용하기 위해 숫자로 변환합니다.

numeric_columns = [
    "rank",
    "rankInten",
    "audiCnt",
    "audiAcc",
    "scrnCnt",
    "showCnt"
]

for column in numeric_columns:
    if column in df.columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        ).fillna(0).astype(int)


# --------------------------------------------
# 10. 순위 기준으로 다시 정렬
# --------------------------------------------

df = df.sort_values(
    by="rank",
    ascending=True
).reset_index(drop=True)


# --------------------------------------------
# 11. 1위 영화 정보
# --------------------------------------------

first_movie = df.iloc[0]

first_movie_name = first_movie["movieNm"]

first_audience = int(first_movie["audiCnt"])
first_total_audience = int(first_movie["audiAcc"])
first_screen_count = int(first_movie["scrnCnt"])


# --------------------------------------------
# 12. 조회 날짜 표시
# --------------------------------------------

st.subheader(f"📅 {display_date} 박스오피스")

st.caption(
    f"KOBIS 조회 날짜: {target_date} · "
    f"현재 한국 시간: {now_kst.strftime('%Y-%m-%d %H:%M')}"
)


# --------------------------------------------
# 13. 1위 영화 크게 보여주기
# --------------------------------------------

st.markdown(
    f"## 🏆 1위 · {first_movie_name}"
)


# 지표 카드 3개
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="🎟️ 일일 관객수",
        value=f"{first_audience:,}명"
    )

with col2:
    st.metric(
        label="👥 누적 관객수",
        value=f"{first_total_audience:,}명"
    )

with col3:
    st.metric(
        label="🎞️ 스크린수",
        value=f"{first_screen_count:,}개"
    )


st.divider()


# --------------------------------------------
# 14. 관객수 상위 5편 그래프
# --------------------------------------------

st.subheader("📊 관객수 상위 5편")

# 관객수 기준으로 내림차순 정렬
top5 = (
    df.sort_values(
        by="audiCnt",
        ascending=False
    )
    .head(5)
    .copy()
)

# 그래프에 표시하기 편하도록 영화명을 인덱스로 사용
chart_data = top5[
    ["movieNm", "audiCnt"]
].set_index("movieNm")

# Streamlit 기본 막대그래프
st.bar_chart(
    chart_data,
    x_label="영화",
    y_label="관객수"
)


# --------------------------------------------
# 15. 전체 박스오피스 표
# --------------------------------------------

st.subheader("🎬 전체 박스오피스")

# 화면에 표시할 컬럼과 이름을 정리합니다.
table_df = df[
    [
        "rank",
        "movieNm",
        "openDt",
        "audiCnt",
        "audiAcc",
        "scrnCnt"
    ]
].copy()

table_df = table_df.rename(
    columns={
        "rank": "순위",
        "movieNm": "영화명",
        "openDt": "개봉일",
        "audiCnt": "관객수",
        "audiAcc": "누적관객",
        "scrnCnt": "스크린수"
    }
)


# --------------------------------------------
# 16. 숫자를 보기 좋은 형태로 표시
# --------------------------------------------
# 내부 데이터는 숫자(int) 상태를 유지하면서
# 화면에서는 1,234처럼 천 단위 구분기호를 넣습니다.

st.dataframe(
    table_df.style.format(
        {
            "순위": "{:,.0f}",
            "관객수": "{:,.0f}",
            "누적관객": "{:,.0f}",
            "스크린수": "{:,.0f}"
        }
    ),
    use_container_width=True,
    hide_index=True
)


# --------------------------------------------
# 17. 데이터 안내
# --------------------------------------------

st.caption(
    "※ 관객수·누적관객·스크린수 등의 숫자는 KOBIS API에서 "
    "문자열로 받은 값을 숫자로 변환하여 사용합니다."
)

st.caption(
    "※ 같은 날짜의 API 결과는 약 1시간 동안 캐시됩니다."
)
```
