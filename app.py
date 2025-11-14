import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import FinanceDataReader as fdr
from swing_analyzer import SwingTradeAnalyzer, filter_swing_candidates, SoaringStockFinder, MorningStarFinder, BullishBreakawayFinder, TalibPatternFinder, SoaringSignalFinder, ComprehensiveAnalyzer, ReverseMAAlignmentFinder
from talib_ui import render_talib_soaring_tab
import warnings
import sys
from io import StringIO
import os

# TA-Lib 임포트 (패턴 감지용)
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False

# 패턴 타입 상수
MORNING_STAR = "🌅 Morning Star"
BULLISH_BREAKAWAY = "⚡ Bullish Breakaway"

warnings.filterwarnings('ignore')

# 페이지 설정
st.set_page_config(
    page_title="스윙매매 종목 추천",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 스타일 설정
st.markdown("""
    <style>
    .title-style {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .subtitle-style {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .progress-container {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-style {
        text-align: center;
        padding: 1rem;
        background-color: #f8f9fa;
        border-radius: 0.5rem;
    }
    .current-stock {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        font-size: 1.1rem;
    }
    </style>
""", unsafe_allow_html=True)

# =============== 일목균형표 계산 함수 ===============

def calculate_ichimoku(df, conversion_period=9, base_period=26, leading_span_b_period=52):
    """
    일목균형표(Ichimoku Cloud) 지표 계산 (미래 구간 포함)

    Parameters:
    - conversion_period: 전환선 기간 (기본값: 9일)
    - base_period: 기준선 기간 (기본값: 26일)
    - leading_span_b_period: 선행스팬B 기간 (기본값: 52일)

    Returns:
    - DataFrame with ichimoku indicators including future dates
    """
    high = df['High']
    low = df['Low']
    close = df['Close']

    # 전환선 (Tenkan-sen): 9일간 최고가와 최저가의 중간값
    tenkan_sen = (high.rolling(window=conversion_period).max() + low.rolling(window=conversion_period).min()) / 2

    # 기준선 (Kijun-sen): 26일간 최고가와 최저가의 중간값
    kijun_sen = (high.rolling(window=base_period).max() + low.rolling(window=base_period).min()) / 2

    # 선행 스팬 A (Senkou Span A): 전환선과 기준선의 중간값을 26일 앞으로 이동
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(base_period)

    # 선행 스팬 B (Senkou Span B): 52일간 최고가와 최저가의 중간값을 26일 앞으로 이동
    senkou_span_b = ((high.rolling(window=leading_span_b_period).max() + low.rolling(window=leading_span_b_period).min()) / 2).shift(base_period)

    # 지행 스팬 (Chikou Span): 현재 종가를 26일 뒤로 이동 (과거로 표시)
    chikou_span = close.shift(-base_period)

    # 미래 날짜까지 인덱스 확장 (선행스팬 표시용)
    last_date = df.index[-1]
    future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=base_period, freq='D')

    # 마지막 값으로 미래 구간 채우기 (선행스팬은 미래 값을 표시하기 위해)
    # reindex로 날짜 확장 후 forward fill로 마지막 값 확장
    senkou_span_a_extended = senkou_span_a.reindex(senkou_span_a.index.union(future_dates))
    senkou_span_a_extended = senkou_span_a_extended.fillna(method='ffill')  # 마지막 값으로 미래 채우기

    senkou_span_b_extended = senkou_span_b.reindex(senkou_span_b.index.union(future_dates))
    senkou_span_b_extended = senkou_span_b_extended.fillna(method='ffill')  # 마지막 값으로 미래 채우기

    return {
        'tenkan_sen': tenkan_sen,
        'kijun_sen': kijun_sen,
        'senkou_span_a': senkou_span_a_extended,
        'senkou_span_b': senkou_span_b_extended,
        'chikou_span': chikou_span,
        'extended_index': senkou_span_a_extended.index
    }

# =============== 패턴 감지 함수 ===============

def detect_bullish_patterns(df):
    """
    TA-Lib을 사용하여 상승 패턴 감지

    Returns:
        list: 패턴 정보 리스트 [{'date': 날짜, 'pattern': 패턴명, 'price': 종가}, ...]
    """
    if not TALIB_AVAILABLE or df is None or len(df) < 30:
        return []

    patterns = []

    try:
        # Convert to float64 for TA-Lib compatibility
        open_arr = np.asarray(df['Open'].values, dtype=np.float64)
        high_arr = np.asarray(df['High'].values, dtype=np.float64)
        low_arr = np.asarray(df['Low'].values, dtype=np.float64)
        close_arr = np.asarray(df['Close'].values, dtype=np.float64)

        # 1. Morning Star (아침별) - 강한 상승 신호
        morningstar = talib.CDLMORNINGSTAR(open_arr, high_arr, low_arr, close_arr)
        for idx, val in enumerate(morningstar):
            if val != 0 and idx < len(df):
                patterns.append({
                    'date': df.index[idx].strftime('%Y-%m-%d'),
                    'pattern': '🌅 Morning Star (아침별)',
                    'price': close_arr[idx],
                    'strength': 'Strong'
                })

        # 2. Bullish Engulfing (강세 포함) - 상승 신호
        engulfing = talib.CDLENGULFING(open_arr, high_arr, low_arr, close_arr)
        for idx, val in enumerate(engulfing):
            if val > 0 and idx < len(df):  # 양수만 강세 신호
                patterns.append({
                    'date': df.index[idx].strftime('%Y-%m-%d'),
                    'pattern': '📈 Bullish Engulfing (강세 포함)',
                    'price': close_arr[idx],
                    'strength': 'Strong'
                })

        # 3. Piercing (관통) - 상승 신호
        piercing = talib.CDLPIERCING(open_arr, high_arr, low_arr, close_arr)
        for idx, val in enumerate(piercing):
            if val != 0 and idx < len(df):
                patterns.append({
                    'date': df.index[idx].strftime('%Y-%m-%d'),
                    'pattern': '⬆️ Piercing (관통)',
                    'price': close_arr[idx],
                    'strength': 'Medium'
                })

        # 4. Three White Soldiers (세 개의 흰 병사) - 강한 상승 신호
        three_white = talib.CDL3WHITESOLDIERS(open_arr, high_arr, low_arr, close_arr)
        for idx, val in enumerate(three_white):
            if val != 0 and idx < len(df):
                patterns.append({
                    'date': df.index[idx].strftime('%Y-%m-%d'),
                    'pattern': '⚪⚪⚪ Three White Soldiers (세 병사)',
                    'price': close_arr[idx],
                    'strength': 'Strong'
                })

        # 5. Bullish Harami (강세 하라미) - 반전 신호
        harami = talib.CDLHARAMI(open_arr, high_arr, low_arr, close_arr)
        for idx, val in enumerate(harami):
            if val > 0 and idx < len(df):  # 양수만 강세
                patterns.append({
                    'date': df.index[idx].strftime('%Y-%m-%d'),
                    'pattern': '💫 Bullish Harami (강세 하라미)',
                    'price': close_arr[idx],
                    'strength': 'Medium'
                })

        # 6. Hammer (망치) - 반전 신호 (저점에서)
        hammer = talib.CDLHAMMER(open_arr, high_arr, low_arr, close_arr)
        for idx, val in enumerate(hammer):
            if val != 0 and idx < len(df):
                patterns.append({
                    'date': df.index[idx].strftime('%Y-%m-%d'),
                    'pattern': '🔨 Hammer (망치)',
                    'price': close_arr[idx],
                    'strength': 'Medium'
                })

        # 중복 제거 및 날짜순 정렬
        unique_patterns = {}
        for p in patterns:
            key = (p['date'], p['pattern'])
            if key not in unique_patterns:
                unique_patterns[key] = p

        patterns = list(unique_patterns.values())
        patterns.sort(key=lambda x: x['date'], reverse=True)  # 최신순 정렬

    except Exception as e:
        st.warning(f"패턴 감지 중 오류: {str(e)}")
        return []

    return patterns

# 세션 상태 초기화
# ===== 통합 캐시 데이터 =====
if 'cached_kospi_stocks' not in st.session_state:
    st.session_state.cached_kospi_stocks = None
if 'cached_analysis_date' not in st.session_state:
    st.session_state.cached_analysis_date = None
if 'cached_swing_results' not in st.session_state:
    st.session_state.cached_swing_results = None
if 'cached_soaring_results' not in st.session_state:
    st.session_state.cached_soaring_results = None
if 'cached_signal_results' not in st.session_state:
    st.session_state.cached_signal_results = None
if 'cached_reverse_ma_results' not in st.session_state:
    st.session_state.cached_reverse_ma_results = None

# ===== 개별 분석 결과 (필터링용) =====
if 'analyzer_results' not in st.session_state:
    st.session_state.analyzer_results = None
if 'filtered_results' not in st.session_state:
    st.session_state.filtered_results = None
if 'is_analyzing' not in st.session_state:
    st.session_state.is_analyzing = False
if 'current_stock' not in st.session_state:
    st.session_state.current_stock = None
if 'progress_text' not in st.session_state:
    st.session_state.progress_text = ""
if 'soaring_results' not in st.session_state:
    st.session_state.soaring_results = None
if 'is_finding_soaring' not in st.session_state:
    st.session_state.is_finding_soaring = False
if 'talib_results' not in st.session_state:
    st.session_state.talib_results = None
if 'selected_talib_stock' not in st.session_state:
    st.session_state.selected_talib_stock = None
if 'talib_chart_data' not in st.session_state:
    st.session_state.talib_chart_data = {}
if 'soaring_signal_results' not in st.session_state:
    st.session_state.soaring_signal_results = None
if 'selected_stock_ticker' not in st.session_state:
    st.session_state.selected_stock_ticker = None
if 'selected_stock_name' not in st.session_state:
    st.session_state.selected_stock_name = None
if 'stock_detail_view_date' not in st.session_state:
    st.session_state.stock_detail_view_date = datetime.now().date()
if 'reverse_ma_results' not in st.session_state:
    st.session_state.reverse_ma_results = None

# 제목
col1, col2, col3 = st.columns([0.5, 2, 0.5])
with col2:
    st.markdown('<h1 class="title-style">📈 스윙매매 종목 추천 시스템</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle-style">기술적 분석 기반 KOSPI 전체 종목 분석</p>', unsafe_allow_html=True)

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 분석 설정")

    min_score = st.slider(
        "최소 점수 필터",
        min_value=0,
        max_value=100,
        value=50,
        step=5,
        help="이 점수 이상의 종목만 표시",
        key="min_score_sidebar"
    )

    st.divider()
    st.subheader("📊 분석 기준")
    st.markdown("""
    - **MA 정배열**: 5MA > 20MA > 60MA (상승추세)
    - **골든크로스**: 20MA > 60MA (강세신호)
    - **RSI**: 30~70 범위 (과매수/과매도 회피)
    - **MACD**: MACD > Signal (상승 신호)
    - **변동성**: 2~8% (스윙에 적합)
    - **거래량**: 평균 이상 (유동성 확보)
    """)

# 메인 콘텐츠
tabs = st.tabs(["🎯 추천 종목", "📈 차트 분석", "🚀 급등주 찾기", "📊 데이터 테이블", "ℹ️ 정보"])

with tabs[0]:
    st.header("KOSPI 전체 종목 분석")

    col1, col2 = st.columns([2, 1])

    with col1:
        run_analysis = st.button(
            "🔍 추천 종목 분석 시작",
            use_container_width=True,
            type="primary"
        )

    with col2:
        use_cached = st.checkbox("캐시된 데이터 사용", value=True, help="같은 날 저장된 데이터가 있으면 사용합니다", key="use_cached_swing")

    # 진행 상황 표시 영역
    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    current_stock_placeholder = st.empty()
    progress_bar_placeholder = st.empty()

    if run_analysis:
        st.session_state.is_analyzing = True

        # 추천 종목만 분석 (점수 >= 50점)
        max_stocks = None  # 모든 종목을 검토하되, 점수 필터링으로 추천 종목만 반환

        # 통합 분석기 (스윙매매 + 급등주 + 급등신호)
        comprehensive_analyzer = ComprehensiveAnalyzer()

        # 캐시된 데이터 우선 사용
        cached_results = None
        if use_cached:
            analyzer = SwingTradeAnalyzer()
            cached_results = analyzer.load_cached_analysis()

        # 캐시 체크박스가 켜져있고 캐시가 있으면 사용, 없으면 새로 분석
        if use_cached and cached_results is not None:
            # 캐시 데이터 사용
            results = cached_results
            # 캐시 데이터도 max_stocks에 따라 필터링
            if max_stocks is not None:
                results = results.head(max_stocks)
            with status_placeholder.container():
                st.info(f"📂 캐시된 데이터 사용: {len(results)}개 종목")
            st.session_state.analyzer_results = results
            st.session_state.filtered_results = filter_swing_candidates(results, min_score=min_score)

            # ===== 캐시 데이터를 통합 캐시에도 저장 (다른 탭에서 사용 가능) =====
            st.session_state.cached_swing_results = results
            st.session_state.cached_analysis_date = datetime.now().date()

            st.session_state.is_analyzing = False
        elif not use_cached:
            # 캐시 체크박스가 꺼져있으면 새로 분석
            # 진행 상황 콜백 함수
            def update_progress(status_text, progress_ratio):
                """통합 분석 진행 상황을 Streamlit UI에 표시"""
                # 진행 상황 표시
                with progress_placeholder.container():
                    st.markdown(f"**진행 상황**: {status_text}")
                    st.progress(progress_ratio)

                # 현재 상태 표시
                with current_stock_placeholder.container():
                    st.markdown(f"""
                    <div class="current-stock">
                        <strong>분석 단계:</strong> {status_text}<br/>
                        <strong>진행률:</strong> {progress_ratio*100:.0f}%
                    </div>
                    """, unsafe_allow_html=True)

            try:
                with status_placeholder.container():
                    st.info(f"📊 추천 종목 분석 중 (스윙매매 기반)...")

                # 통합 분석 실행
                all_results = comprehensive_analyzer.analyze_all_in_one(
                    max_stocks=max_stocks,
                    progress_callback=update_progress
                )

                # 스윙매매 결과
                swing_results = all_results['swing_results']
                soaring_results = all_results['soaring_results']
                signal_results = all_results['signal_results']

                if swing_results is not None and not swing_results.empty:
                    # CSV로 저장
                    analyzer = SwingTradeAnalyzer()
                    analyzer.save_analysis_results(swing_results)

                    st.session_state.analyzer_results = swing_results
                    st.session_state.filtered_results = filter_swing_candidates(swing_results, min_score=min_score)

                    # ===== 통합 캐시에 모든 분석 결과 저장 =====
                    st.session_state.cached_swing_results = swing_results
                    st.session_state.cached_soaring_results = soaring_results
                    st.session_state.cached_signal_results = signal_results
                    st.session_state.cached_analysis_date = datetime.now().date()

                    # 급등주 결과 저장
                    if soaring_results is not None and not soaring_results.empty:
                        st.session_state.talib_results = soaring_results

                    # 급등신호 결과 저장
                    if signal_results is not None and not signal_results.empty:
                        st.session_state.soaring_signal_results = signal_results

                    # 완료 메시지
                    with status_placeholder.container():
                        col_swing, col_soaring, col_signal = st.columns(3)
                        with col_swing:
                            st.success(f"✅ 스윙매매\n{len(swing_results)}개 종목")
                        with col_soaring:
                            soaring_count = len(soaring_results) if soaring_results is not None and not soaring_results.empty else 0
                            st.info(f"✅ 급등주(TA-Lib)\n{soaring_count}개 종목")
                        with col_signal:
                            signal_count = len(signal_results) if signal_results is not None and not signal_results.empty else 0
                            st.success(f"✅ 급등신호\n{signal_count}개 종목")

                    # 자동 탭 네비게이션 안내
                    st.divider()
                    st.markdown("""
                    ### 📊 분석 결과 보기

                    각 탭에서 상세한 결과를 확인할 수 있습니다:
                    - **📈 차트 분석**: 개별 종목 차트 및 기술적 지표
                    - **🚀 급등주 찾기**: TA-Lib 기반 패턴 (Morning Star, Bullish Breakaway)
                    - **⚡ 급등신호**: 신호 기반 급등 예정 종목
                    """)

                    st.session_state.is_analyzing = False
                else:
                    with status_placeholder.container():
                        st.error("""
                        ❌ 분석 결과가 없습니다.

                        **원인:**
                        - KOSPI 종목 데이터를 조회할 수 없거나 인터넷 연결이 불안정함
                        - FinanceDataReader에서 주가 데이터를 받지 못함

                        **해결 방법:**
                        1. 인터넷 연결 상태를 확인해주세요
                        2. 잠시 후 다시 시도해주세요
                        3. 분석 범위를 '테스트 (50개)'로 줄여서 시도해보세요
                        """)
                    st.session_state.is_analyzing = False

            except Exception as e:
                with status_placeholder.container():
                    st.error(f"""
                    ⚠️ 분석 중 오류 발생했습니다.

                    **오류 정보:** {str(e)}

                    **해결 방법:**
                    1. 인터넷 연결을 확인해주세요
                    2. 분석 범위를 줄여서 다시 시도해보세요
                    3. 계속 오류가 발생하면 '테스트 (50개)'로 시도해보세요
                    """)
                st.session_state.is_analyzing = False
        else:
            # 캐시 체크박스가 켜져있는데 캐시가 없는 경우
            with status_placeholder.container():
                st.warning("⚠️ 캐시된 데이터가 없습니다. 새로운 분석을 시작하려면 '캐시된 데이터 사용' 체크박스를 끄세요.")
            st.session_state.is_analyzing = False

    # 결과 표시
    if st.session_state.filtered_results is not None and len(st.session_state.filtered_results) > 0:
        filtered_df = st.session_state.filtered_results

        # 등급별 종목 수
        col1, col2, col3, col4 = st.columns(4)

        strong_buy = len(filtered_df[filtered_df['total_score'] >= 70])
        buy = len(filtered_df[(filtered_df['total_score'] >= 50) & (filtered_df['total_score'] < 70)])

        with col1:
            st.metric("Strong Buy ⭐⭐⭐", strong_buy, delta="적극 추천")
        with col2:
            st.metric("Buy ⭐⭐", buy, delta="추천")
        with col3:
            st.metric("총 추천 종목", len(filtered_df), delta="개")
        with col4:
            avg_score = filtered_df['total_score'].mean()
            st.metric("평균 점수", f"{avg_score:.1f}", delta="점")

        st.divider()

        # CSV 다운로드 버튼
        csv_data = filtered_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 분석 결과 CSV 다운로드 (UTF-8)",
            data=csv_data,
            file_name=f"swing_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

        # 점수 분포 차트
        fig_score_dist = px.histogram(
            filtered_df,
            x='total_score',
            nbins=15,
            title='점수 분포',
            labels={'total_score': '총 점수', 'count': '종목 수'},
            color_discrete_sequence=['#1f77b4']
        )
        fig_score_dist.update_layout(
            showlegend=False,
            height=300,
            xaxis_title='총 점수',
            yaxis_title='종목 수'
        )
        st.plotly_chart(fig_score_dist, use_container_width=True)

        st.divider()

        # 추천 종목 목록
        st.subheader("🏆 추천 종목 순위")

        # 데이터 추출 시간 표시
        if 'extraction_time' in filtered_df.columns and len(filtered_df) > 0:
            extraction_time = filtered_df.iloc[0]['extraction_time']
            if 'price_date' in filtered_df.columns:
                price_date = filtered_df.iloc[0]['price_date']
                st.caption(f"📊 현재가(Close): {price_date} | 데이터 추출: {extraction_time}")
            else:
                st.caption(f"📊 데이터 추출: {extraction_time}")

        display_df = filtered_df[[
            'name', 'ticker', 'current_price', 'volatility', 'total_score', 'recommendation'
        ]].head(20).copy()

        display_df.columns = ['종목명', '티커', '현재가', '변동성(%)', '점수', '추천']
        display_df['순위'] = range(1, len(display_df) + 1)

        # 티커를 문자열로 변환 및 6자리로 패딩 (leading zero 보존)
        display_df['티커_temp'] = display_df['티커'].astype(str).str.zfill(6)

        # 티커를 네이버 증권 링크로 변환 (0이 생략되지 않도록 텍스트로 표시)
        display_df['티커'] = display_df['티커_temp'].apply(
            lambda ticker: f'<a href="https://finance.naver.com/item/main.naver?code={str(ticker)}" target="_blank">{str(ticker)}</a>'
        )
        display_df = display_df.drop('티커_temp', axis=1)

        display_df = display_df[['순위', '종목명', '티커', '현재가', '변동성(%)', '점수', '추천']]

        # 조건부 스타일
        def color_recommendation(val):
            if val == 'Strong Buy':
                return 'background-color: #ffff99'
            elif val == 'Buy':
                return 'background-color: #c2f0c2'
            return 'background-color: #ffe6e6'

        st.markdown(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)
        st.caption("💡 팁: 종목명을 아래 입력창에 입력하면 모든 분석 정보를 한 화면에서 확인할 수 있습니다")

        st.divider()

        # 🆕 통합 정보 조회 섹션
        st.subheader("🔍 종목 통합 정보 조회")
        st.markdown("같은 종목의 추천, 급등주, 급등신호 정보를 한 화면에서 확인하세요!")

        col_stock_select, col_date_select = st.columns([2, 1])

        with col_stock_select:
            # 추천 종목 목록에서 종목 선택
            selected_name = st.selectbox(
                "조회할 종목을 선택하세요",
                options=filtered_df['name'].tolist(),
                key="unified_stock_select",
                help="추천된 종목 중에서 선택"
            )

        with col_date_select:
            # 분석 날짜 선택
            selected_date = st.date_input(
                "분석 기준일",
                value=st.session_state.stock_detail_view_date,
                key="unified_date_select",
                help="차트 분석의 기준 날짜를 선택하세요"
            )
            st.session_state.stock_detail_view_date = selected_date

        if selected_name:
            # 선택된 종목 정보
            stock_info = filtered_df[filtered_df['name'] == selected_name].iloc[0]
            ticker = str(stock_info['ticker']).zfill(6)

            st.divider()

            # 종목 기본 정보
            col_info1, col_info2, col_info3, col_info4 = st.columns(4)

            with col_info1:
                st.metric(
                    "종목명",
                    f"{selected_name}",
                    f"({ticker})"
                )

            with col_info2:
                st.metric(
                    "현재가",
                    f"₩{stock_info['current_price']:,.0f}",
                    help="종목의 현재 주가"
                )

            with col_info3:
                st.metric(
                    "변동성",
                    f"{stock_info['volatility']:.2f}%",
                    help="20일 기준 변동성"
                )

            with col_info4:
                st.metric(
                    "추천 점수",
                    f"{stock_info['total_score']:.1f}",
                    f"{stock_info['recommendation']}"
                )

            st.divider()

            # 3개 탭으로 정보 표시
            detail_tab1, detail_tab2, detail_tab3 = st.tabs([
                "📊 추천 종목 상세",
                "🚀 급등주 패턴",
                "⚡ 급등신호"
            ])

            # Tab 1: 추천 종목 상세 정보
            with detail_tab1:
                st.markdown("### 📊 스윙매매 분석 결과")

                col_detail1, col_detail2 = st.columns(2)

                with col_detail1:
                    st.markdown("**기술적 지표**")
                    st.write(f"🔹 RSI: {stock_info.get('rsi', 'N/A'):.1f}")
                    st.write(f"🔹 MACD: {stock_info.get('macd', 'N/A')}")
                    if 'golden_cross' in stock_info and stock_info['golden_cross']:
                        st.success("✅ 골든크로스 발생")
                    else:
                        st.info("⚪ 골든크로스 미발생")

                with col_detail2:
                    st.markdown("**추세 분석**")
                    if stock_info.get('ma_aligned', False):
                        st.success("✅ MA 정배열 (상승추세)")
                    else:
                        st.warning("⚠️ MA 정배열 아님")

                    if stock_info.get('volume_strong', False):
                        st.success("✅ 거래량 증가")
                    else:
                        st.info("⚪ 거래량 정상")

                st.markdown("**평가 이유**")
                st.info(f"점수: {stock_info['total_score']:.1f} | 추천: {stock_info['recommendation']}")

            # Tab 2: 급등주 패턴
            with detail_tab2:
                st.markdown("### 🚀 급등주 패턴 분석")

                # 급등주 결과에서 해당 종목 찾기
                soaring_matched = None
                if st.session_state.talib_results is not None and not st.session_state.talib_results.empty:
                    soaring_matched = st.session_state.talib_results[
                        st.session_state.talib_results['ticker'] == ticker
                    ]

                if soaring_matched is not None and len(soaring_matched) > 0:
                    st.success("✅ 급등 패턴 감지됨!")
                    for idx, row in soaring_matched.iterrows():
                        col_pattern1, col_pattern2 = st.columns([2, 1])
                        with col_pattern1:
                            st.write(f"**패턴**: {row.get('pattern_type', 'N/A')}")
                        with col_pattern2:
                            st.caption(f"발생일: {row.get('pattern_date', 'N/A')}")
                else:
                    st.info("⚪ 최근 6개월 내 급등 패턴 미감지")
                    st.markdown("""
                    **Morning Star**: 저점 > 중간 > 종가 패턴으로 강력한 상승신호
                    **Bullish Breakaway**: 저점 돌파로 상승 추세 시작
                    """)

            # Tab 3: 급등신호
            with detail_tab3:
                st.markdown("### ⚡ 급등신호 분석")

                # 급등신호 결과에서 해당 종목 찾기
                signal_matched = None
                if st.session_state.soaring_signal_results is not None and not st.session_state.soaring_signal_results.empty:
                    signal_matched = st.session_state.soaring_signal_results[
                        st.session_state.soaring_signal_results['ticker'] == ticker
                    ]

                if signal_matched is not None and len(signal_matched) > 0:
                    signal_data = signal_matched.iloc[0]
                    st.success(f"급등신호 점수: {signal_data.get('score', 0):.1f}/100")
                    st.write(f"확률: {signal_data.get('soaring_probability', 'N/A')}")

                    # 신호별 상세 정보
                    col_sig1, col_sig2, col_sig3 = st.columns(3)

                    with col_sig1:
                        st.markdown("**📈 거래량 신호**")
                        if signal_data.get('has_strong_volume', False):
                            st.success("✅ 대량 거래량")
                        else:
                            st.info("⚪ 정상 거래량")

                        if signal_data.get('has_accumulation', False):
                            st.success("✅ 거래량 매집")
                        else:
                            st.info("⚪ 정상")

                    with col_sig2:
                        st.markdown("**🕯️ 캔들 신호**")
                        if signal_data.get('has_upper_tail', False):
                            st.success("✅ 윗꼬리 패턴")
                        else:
                            st.info("⚪ 미감지")

                        if signal_data.get('has_rising_lows', False):
                            st.success("✅ 저점 상승")
                        else:
                            st.info("⚪ 미감지")

                    with col_sig3:
                        st.markdown("**💪 지지선 신호**")
                        if signal_data.get('has_support_bounce', False):
                            st.success("✅ 지지 반등")
                        else:
                            st.info("⚪ 미감지")

                        if signal_data.get('has_resistance_breakout', False):
                            st.success("✅ 매물대 돌파")
                        else:
                            st.info("⚪ 미감지")
                else:
                    st.info("⚪ 급등신호 데이터 없음")
                    st.markdown("먼저 종합 분석을 실행하여 급등신호를 분석해주세요")

            st.divider()

            # 네이버 증권 링크
            st.markdown(f"""
            [📊 네이버 증권에서 {selected_name} 보기](https://finance.naver.com/item/main.naver?code={ticker})
            """)

    elif st.session_state.filtered_results is not None and len(st.session_state.filtered_results) == 0:
        st.warning("⚠️ 조건을 만족하는 추천 종목이 없습니다.")
    else:
        st.info("📌 '🔍 추천 종목 분석 시작' 버튼을 클릭하여 분석을 시작하세요.")

with tabs[1]:
    st.header("📈 차트 분석")

    if st.session_state.filtered_results is not None and len(st.session_state.filtered_results) > 0:
        # Initialize chart selection in session state
        if 'selected_chart_stock' not in st.session_state:
            # Initialize with the first stock name directly
            stock_list = st.session_state.filtered_results['name'].tolist()
            if stock_list:
                st.session_state.selected_chart_stock = stock_list[0]
            else:
                st.session_state.selected_chart_stock = None

        # Get list of stocks (전체 추천종목)
        stock_list = st.session_state.filtered_results['name'].tolist()

        # Define callback functions for buttons
        def on_prev_click():
            if st.session_state.selected_chart_stock in stock_list:
                current_idx = stock_list.index(st.session_state.selected_chart_stock)
                if current_idx > 0:
                    st.session_state.selected_chart_stock = stock_list[current_idx - 1]

        def on_next_click():
            if st.session_state.selected_chart_stock in stock_list:
                current_idx = stock_list.index(st.session_state.selected_chart_stock)
                if current_idx < len(stock_list) - 1:
                    st.session_state.selected_chart_stock = stock_list[current_idx + 1]

        def on_selectbox_change():
            # This callback updates session state when selectbox changes
            st.session_state.selected_chart_stock = st.session_state.chart_stock_select

        col1, col2, col3, col4 = st.columns([0.8, 2, 1, 1])

        with col1:
            # Previous button - navigate backwards with callback
            st.button("◀", key="prev_stock_btn", help="이전 종목", on_click=on_prev_click)

        with col2:
            # Selectbox with callback (not using index to avoid conflicts)
            st.selectbox(
                "종목 선택",
                options=stock_list,
                index=stock_list.index(st.session_state.selected_chart_stock) if st.session_state.selected_chart_stock in stock_list else 0,
                help="차트를 보고 싶은 종목을 선택하세요",
                key="chart_stock_select",
                on_change=on_selectbox_change
            )

        with col3:
            # Next button - navigate forwards with callback
            st.button("▶", key="next_stock_btn", help="다음 종목", on_click=on_next_click)

        with col4:
            chart_period = st.selectbox(
                "기간",
                options=["1개월", "3개월", "6개월", "1년"],
                index=3
            )

        if st.session_state.selected_chart_stock:
            # 선택한 종목의 정보
            stock_info = st.session_state.filtered_results[
                st.session_state.filtered_results['name'] == st.session_state.selected_chart_stock
            ].iloc[0]

            ticker = str(stock_info['ticker']).zfill(6)

            # 종목명과 티커를 클릭 가능하게 표시
            col_ticker_left, col_ticker_right = st.columns([3, 1])
            with col_ticker_left:
                st.markdown(f"""
                ### 📈 [{st.session_state.selected_chart_stock} ({ticker})](https://finance.naver.com/item/main.naver?code={ticker})
                """, unsafe_allow_html=True)

            st.divider()

            # 기간 설정
            period_days = {'1개월': 30, '3개월': 90, '6개월': 180, '1년': 365}[chart_period]

            try:
                # 데이터 조회
                end_date = datetime.now()
                start_date = end_date - timedelta(days=period_days)

                # FinanceDataReader는 한국 ticker 코드 그대로 사용 (예: 005930)
                ticker_symbol = ticker

                # 재시도 로직이 있는 데이터 다운로드
                df = None
                for attempt in range(3):
                    try:
                        # FinanceDataReader로 데이터 조회
                        df = fdr.DataReader(
                            ticker_symbol,
                            start_date,
                            end_date
                        )
                        if df is not None and len(df) > 0:
                            break
                    except Exception as e:
                        if attempt < 2:
                            import time
                            time.sleep(0.5)
                        else:
                            st.error(f"❌ 데이터 조회 실패: {str(e)}")

                # 데이터 확인 및 처리
                if df is None or len(df) == 0:
                    st.error(f"❌ {st.session_state.selected_chart_stock} ({ticker})의 데이터를 찾을 수 없습니다.")
                else:
                    # MultiIndex 처리 (경우에 따라 MultiIndex를 반환할 수 있음)
                    if isinstance(df.columns, pd.MultiIndex):
                        # MultiIndex인 경우 첫 번째 레벨만 취함
                        df.columns = df.columns.get_level_values(0)

                    # 컬럼명 정리 - 첫 글자 대문자 변환
                    df.columns = [str(col).strip() for col in df.columns]
                    df.columns = [col[0].upper() + col[1:].lower() if len(col) > 0 else col for col in df.columns]

                    # 필요한 컬럼 확인
                    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']

                    # 컬럼 매핑 (대소문자 무시)
                    col_map = {}
                    for col in df.columns:
                        col_lower = col.lower().strip()
                        if col_lower == 'open':
                            col_map[col] = 'Open'
                        elif col_lower == 'high':
                            col_map[col] = 'High'
                        elif col_lower == 'low':
                            col_map[col] = 'Low'
                        elif col_lower == 'close':
                            col_map[col] = 'Close'
                        elif col_lower == 'volume':
                            col_map[col] = 'Volume'
                        elif 'adj' in col_lower:
                            col_map[col] = 'Adj Close'

                    if col_map:
                        df = df.rename(columns=col_map)

                    # 필요한 컬럼만 선택
                    available_cols = [col for col in required_cols if col in df.columns]
                    if len(available_cols) >= 5:
                        df = df[required_cols].copy()
                    else:
                        st.error(f"❌ 필요한 컬럼이 부족합니다. 발견된 컬럼: {list(df.columns)}")
                        df = None

                    # 데이터 타입 변환
                    if df is not None:
                        df['Open'] = pd.to_numeric(df['Open'], errors='coerce')
                        df['High'] = pd.to_numeric(df['High'], errors='coerce')
                        df['Low'] = pd.to_numeric(df['Low'], errors='coerce')
                        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
                        df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')

                        # NaN 값 제거
                        df = df.dropna()

                        if len(df) == 0:
                            st.error(f"❌ 유효한 데이터가 없습니다.")
                            df = None

                    if df is not None and len(df) > 0:
                        # 이동평균선 계산
                        df['MA5'] = df['Close'].rolling(window=5).mean()
                        df['MA20'] = df['Close'].rolling(window=20).mean()
                        df['MA60'] = df['Close'].rolling(window=60).mean()
                        df['MA112'] = df['Close'].rolling(window=112).mean()
                        df['MA224'] = df['Close'].rolling(window=224).mean()

                        # 캔들스틱 차트 생성 (Plotly - 최신 버전 호환)
                        fig = go.Figure()

                        # 캔들스틱 추가
                        fig.add_trace(go.Candlestick(
                            x=df.index,
                            open=df['Open'],
                            high=df['High'],
                            low=df['Low'],
                            close=df['Close'],
                            name='가격',
                            increasing_line_color='#FF3131',      # 상승봉
                            decreasing_line_color='#0047AB',      # 하락봉
                            increasing_fillcolor='#FF3131',
                            decreasing_fillcolor='#0047AB'
                        ))

                        # 이동평균선 추가
                        fig.add_trace(go.Scatter(
                            x=df.index,
                            y=df['MA5'],
                            name='MA5 (5일)',
                            mode='lines',
                            line=dict(color='#FFB400', width=2),
                            hovertemplate='<b>MA5</b><br>%{x|%Y-%m-%d}<br>₩%{y:,.0f}<extra></extra>'
                        ))

                        fig.add_trace(go.Scatter(
                            x=df.index,
                            y=df['MA20'],
                            name='MA20 (20일)',
                            mode='lines',
                            line=dict(color='#FF6B9D', width=2),
                            hovertemplate='<b>MA20</b><br>%{x|%Y-%m-%d}<br>₩%{y:,.0f}<extra></extra>'
                        ))

                        fig.add_trace(go.Scatter(
                            x=df.index,
                            y=df['MA60'],
                            name='MA60 (60일)',
                            mode='lines',
                            line=dict(color='#00D084', width=3),
                            hovertemplate='<b>MA60</b><br>%{x|%Y-%m-%d}<br>₩%{y:,.0f}<extra></extra>'
                        ))

                        fig.add_trace(go.Scatter(
                            x=df.index,
                            y=df['MA112'],
                            name='MA112 (112일)',
                            mode='lines',
                            line=dict(color='#FF9500', width=2),
                            hovertemplate='<b>MA112</b><br>%{x|%Y-%m-%d}<br>₩%{y:,.0f}<extra></extra>'
                        ))

                        fig.add_trace(go.Scatter(
                            x=df.index,
                            y=df['MA224'],
                            name='MA224 (224일)',
                            mode='lines',
                            line=dict(color='#9C27B0', width=2),
                            hovertemplate='<b>MA224</b><br>%{x|%Y-%m-%d}<br>₩%{y:,.0f}<extra></extra>'
                        ))

                        # 차트 레이아웃 설정 (일목균형표용 x축 확장: 26일 앞)
                        # 현재 날짜 기준으로 26일 뒤까지 x축 범위 확장
                        end_date_extended = df.index[-1] + pd.Timedelta(days=26)

                        fig.update_layout(
                            title=f'{st.session_state.selected_chart_stock} ({ticker}) - {chart_period}',
                            yaxis=dict(
                                title='가격 (원)',
                                showgrid=True,
                                gridwidth=1,
                                gridcolor='#E5E5E5'
                            ),
                            xaxis=dict(
                                title='날짜',
                                rangeslider=dict(visible=False),
                                range=[df.index[0], end_date_extended]  # 26일 앞까지 표시
                            ),
                            template='plotly_white',
                            height=750,
                            xaxis_rangeslider_visible=False,
                            hovermode='x unified',
                            font=dict(size=12, family='Arial'),
                            plot_bgcolor='rgba(240,240,240,0.3)',
                            paper_bgcolor='white',
                            showlegend=True,
                            legend=dict(
                                bgcolor='rgba(255,255,255,0.9)',
                                bordercolor='#000000',
                                borderwidth=1,
                                x=0.02,
                                y=0.98,
                                xanchor='left',
                                yanchor='top',
                                font=dict(size=11)
                            ),
                            margin=dict(l=60, r=40, t=60, b=60)
                        )

                        # ===== 차트 옵션 설정 (토글) =====
                        detected_patterns = detect_bullish_patterns(df)

                        # 패턴 표시 토글 및 일목균형표 토글
                        col1, col2, col3 = st.columns([1, 1, 2])
                        with col1:
                            show_patterns = st.checkbox(
                                "패턴 표시",
                                value=False,
                                help="차트에 감지된 상승 패턴을 별 모양으로 표시합니다"
                            )
                        with col2:
                            show_ichimoku = st.checkbox(
                                "일목균형표",
                                value=True,
                                help="Ichimoku Cloud 지표를 표시합니다"
                            )

                        # 패턴을 차트에 마커로 표시 (토글이 켜져있을 때만)
                        if show_patterns and detected_patterns:
                            for pattern in detected_patterns:
                                pattern_date_str = pattern['date']
                                pattern_price = pattern['price']

                                # 차트에 마커 추가
                                fig.add_trace(go.Scatter(
                                    x=[pattern_date_str],
                                    y=[pattern_price],
                                    mode='markers',
                                    name=pattern['pattern'],
                                    marker=dict(
                                        size=15,
                                        color='gold' if pattern['strength'] == 'Strong' else 'orange',
                                        symbol='star',
                                        line=dict(color='darkred', width=2)
                                    ),
                                    hovertemplate=f"<b>{pattern['pattern']}</b><br>날짜: {pattern_date_str}<br>가격: ₩{pattern_price:,.0f}<extra></extra>",
                                    showlegend=False
                                ))

                        # 일목균형표 추가 (토글이 켜져있을 때만)
                        if show_ichimoku:
                            ichimoku = calculate_ichimoku(df)

                            # 선행 스팬 B (먼저 추가) - 미래 구간 포함
                            fig.add_trace(go.Scatter(
                                x=ichimoku['extended_index'],
                                y=ichimoku['senkou_span_b'],
                                name='선행스팬 B',
                                mode='lines',
                                line=dict(color='rgba(255, 152, 0, 0.3)', width=1),
                                showlegend=True,
                                hovertemplate='<b>선행스팬 B</b><br>%{x|%Y-%m-%d}<br>₩%{y:,.0f}<extra></extra>'
                            ))

                            # 선행 스팬 A (클라우드 배경 채우기) - 미래 구간 포함
                            fig.add_trace(go.Scatter(
                                x=ichimoku['extended_index'],
                                y=ichimoku['senkou_span_a'],
                                name='선행스팬 A (클라우드)',
                                mode='lines',
                                line=dict(color='rgba(0, 150, 136, 0.3)', width=1),
                                fillcolor='rgba(100, 200, 150, 0.15)',
                                fill='tonexty',
                                showlegend=True,
                                hovertemplate='<b>선행스팬 A</b><br>%{x|%Y-%m-%d}<br>₩%{y:,.0f}<extra></extra>'
                            ))

                            # 전환선 (Tenkan-sen)
                            fig.add_trace(go.Scatter(
                                x=df.index,
                                y=ichimoku['tenkan_sen'],
                                name='전환선',
                                mode='lines',
                                line=dict(color='#FF6B6B', width=1, dash='solid'),
                                showlegend=True,
                                hovertemplate='<b>전환선</b><br>%{x|%Y-%m-%d}<br>₩%{y:,.0f}<extra></extra>'
                            ))

                            # 기준선 (Kijun-sen)
                            fig.add_trace(go.Scatter(
                                x=df.index,
                                y=ichimoku['kijun_sen'],
                                name='기준선',
                                mode='lines',
                                line=dict(color='#4ECDC4', width=1, dash='solid'),
                                showlegend=True,
                                hovertemplate='<b>기준선</b><br>%{x|%Y-%m-%d}<br>₩%{y:,.0f}<extra></extra>'
                            ))

                            # 지행 스팬 (Chikou Span)
                            fig.add_trace(go.Scatter(
                                x=df.index,
                                y=ichimoku['chikou_span'],
                                name='지행스팬',
                                mode='lines',
                                line=dict(color='#95E1D3', width=1, dash='dot'),
                                showlegend=True,
                                hovertemplate='<b>지행스팬</b><br>%{x|%Y-%m-%d}<br>₩%{y:,.0f}<extra></extra>'
                            ))

                        # 차트는 한 번만 표시
                        st.plotly_chart(fig, use_container_width=True)

                        # ===== 상승 패턴 정보 표시 =====
                        st.subheader("🎯 감지된 상승 패턴")

                        if detected_patterns:
                            # 패턴 리스트 테이블
                            st.markdown("#### 📋 상승 패턴 상세 정보")

                            # DataFrame으로 변환
                            patterns_df = pd.DataFrame([
                                {
                                    '날짜': p['date'],
                                    '패턴명': p['pattern'],
                                    '종가': f"₩{p['price']:,.0f}",
                                    '강도': '⭐⭐⭐ 강함' if p['strength'] == 'Strong' else '⭐⭐ 중간'
                                }
                                for p in detected_patterns
                            ])

                            # 스타일링된 테이블 표시
                            st.dataframe(
                                patterns_df,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    '날짜': st.column_config.TextColumn(width='medium'),
                                    '패턴명': st.column_config.TextColumn(width='large'),
                                    '종가': st.column_config.TextColumn(width='medium'),
                                    '강도': st.column_config.TextColumn(width='small')
                                }
                            )

                            # 패턴 통계
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("📊 총 패턴 수", len(detected_patterns))
                            with col2:
                                strong_count = len([p for p in detected_patterns if p['strength'] == 'Strong'])
                                st.metric("⭐⭐⭐ 강한 신호", strong_count)
                            with col3:
                                medium_count = len([p for p in detected_patterns if p['strength'] == 'Medium'])
                                st.metric("⭐⭐ 중간 신호", medium_count)
                        else:
                            st.info("📌 현재 기간에 감지된 상승 패턴이 없습니다.")

                        # 거래량 차트 (기간 동일, 별도 표시)
                        st.subheader("📊 거래량")

                        # 거래량 바 차트 (양수/음수로 색상 구분)
                        colors = ['green' if df['Close'].values[i] >= df['Open'].values[i] else 'red'
                                  for i in range(len(df))]

                        fig_volume = go.Figure()

                        fig_volume.add_trace(go.Bar(
                            x=df.index,
                            y=df['Volume'],
                            name='거래량',
                            marker=dict(color=colors),
                            showlegend=False,
                            hovertemplate='<b>%{x|%Y-%m-%d}</b><br>거래량: %{y:,.0f}<extra></extra>'
                        ))

                        fig_volume.update_layout(
                            title=f'{st.session_state.selected_chart_stock} ({ticker}) - 거래량',
                            yaxis=dict(
                                title='거래량',
                                showgrid=True,
                                gridwidth=1,
                                gridcolor='#E5E5E5'
                            ),
                            xaxis_title='날짜',
                            template='plotly_white',
                            height=400,
                            xaxis_rangeslider_visible=False,
                            hovermode='x unified',
                            font=dict(size=12, family='Arial'),
                            plot_bgcolor='rgba(240,240,240,0.5)',
                            paper_bgcolor='white',
                            margin=dict(l=60, r=40, t=60, b=60)
                        )

                        st.plotly_chart(fig_volume, use_container_width=True)

                        # MACD 차트
                        st.subheader("📊 MACD (Moving Average Convergence Divergence)")

                        # MACD 계산
                        ema_fast = df['Close'].ewm(span=12).mean()
                        ema_slow = df['Close'].ewm(span=26).mean()
                        df['MACD'] = ema_fast - ema_slow
                        df['Signal'] = df['MACD'].ewm(span=9).mean()
                        df['MACD_Hist'] = df['MACD'] - df['Signal']

                        fig_macd = go.Figure()

                        # MACD 라인
                        fig_macd.add_trace(go.Scatter(
                            x=df.index,
                            y=df['MACD'],
                            name='MACD',
                            line=dict(color='blue', width=2),
                            hovertemplate='<b>%{x|%Y-%m-%d}</b><br>MACD: %{y:.4f}<extra></extra>'
                        ))

                        # Signal 라인
                        fig_macd.add_trace(go.Scatter(
                            x=df.index,
                            y=df['Signal'],
                            name='Signal',
                            line=dict(color='red', width=2),
                            hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Signal: %{y:.4f}<extra></extra>'
                        ))

                        # MACD Histogram
                        colors = ['green' if df['MACD_Hist'].values[i] >= 0 else 'red'
                                  for i in range(len(df))]

                        fig_macd.add_trace(go.Bar(
                            x=df.index,
                            y=df['MACD_Hist'],
                            name='Histogram',
                            marker=dict(color=colors, opacity=0.3),
                            hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Histogram: %{y:.4f}<extra></extra>'
                        ))

                        fig_macd.update_layout(
                            title=f'{st.session_state.selected_chart_stock} ({ticker}) - MACD',
                            yaxis=dict(
                                title='MACD',
                                showgrid=True,
                                gridwidth=1,
                                gridcolor='#E5E5E5'
                            ),
                            xaxis_title='날짜',
                            template='plotly_white',
                            height=420,
                            xaxis_rangeslider_visible=False,
                            hovermode='x unified',
                            font=dict(size=12, family='Arial'),
                            plot_bgcolor='rgba(240,240,240,0.5)',
                            paper_bgcolor='white',
                            showlegend=True,
                            legend=dict(
                                bgcolor='rgba(255,255,255,0.9)',
                                bordercolor='#000000',
                                borderwidth=1,
                                x=0.02,
                                y=0.98,
                                xanchor='left',
                                yanchor='top',
                                font=dict(size=11)
                            ),
                            margin=dict(l=60, r=40, t=60, b=60)
                        )

                        st.plotly_chart(fig_macd, use_container_width=True)

                        # 변동성 차트
                        st.subheader("📈 변동성 (Volatility)")

                        df['Volatility'] = df['Close'].rolling(window=20).std() / df['Close'].rolling(window=20).mean() * 100

                        fig_volatility = go.Figure()

                        fig_volatility.add_trace(go.Scatter(
                            x=df.index,
                            y=df['Volatility'],
                            name='변동성',
                            fill='tozeroy',
                            line=dict(color='orange', width=2),
                            hovertemplate='<b>%{x|%Y-%m-%d}</b><br>변동성: %{y:.2f}%<extra></extra>'
                        ))

                        # 변동성 범위 표시 (2~8% 적정 범위)
                        fig_volatility.add_hline(y=2, line_dash="dash", line_color="green", annotation_text="최소 (2%)", annotation_position="right")
                        fig_volatility.add_hline(y=8, line_dash="dash", line_color="green", annotation_text="최대 (8%)", annotation_position="right")

                        fig_volatility.update_layout(
                            title=f'{st.session_state.selected_chart_stock} ({ticker}) - 변동성',
                            yaxis=dict(
                                title='변동성 (%)',
                                showgrid=True,
                                gridwidth=1,
                                gridcolor='#E5E5E5'
                            ),
                            xaxis_title='날짜',
                            template='plotly_white',
                            height=420,
                            xaxis_rangeslider_visible=False,
                            hovermode='x unified',
                            font=dict(size=12, family='Arial'),
                            plot_bgcolor='rgba(240,240,240,0.5)',
                            paper_bgcolor='white',
                            showlegend=True,
                            legend=dict(
                                bgcolor='rgba(255,255,255,0.9)',
                                bordercolor='#000000',
                                borderwidth=1,
                                x=0.02,
                                y=0.98,
                                xanchor='left',
                                yanchor='top',
                                font=dict(size=11)
                            ),
                            margin=dict(l=60, r=40, t=60, b=60)
                        )

                        st.plotly_chart(fig_volatility, use_container_width=True)

                        # 주요 지표 표시
                        st.divider()
                        st.subheader("📊 기술적 지표")

                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            st.metric("현재가", f"₩{stock_info['current_price']:,.0f}")
                        with col2:
                            st.metric("변동성", f"{stock_info['volatility']:.2f}%")
                        with col3:
                            st.metric("RSI", f"{stock_info['rsi']:.1f}")
                        with col4:
                            st.metric("총 점수", f"{stock_info['total_score']:.1f}", delta=stock_info['recommendation'])

                    else:
                        st.error("차트 데이터를 조회할 수 없습니다.")

            except Exception as e:
                st.error(f"차트 조회 실패: {str(e)}")

    else:
        st.info("📌 먼저 '추천 종목' 탭에서 분석을 실행해주세요.")


with tabs[2]:
    # TA-Lib 기반 급등주 찾기 UI 렌더링
    render_talib_soaring_tab()

with tabs[3]:
    st.header("📊 데이터 테이블")

    # ===== 헬퍼 함수: 데이터프레임을 HTML로 변환 (클릭 가능한 링크 포함) =====
    def create_clickable_dataframe(df, tab_name):
        """
        데이터프레임에서 ticker와 name 컬럼을 클릭 가능한 링크로 변환
        """
        if df is None or len(df) == 0:
            return None

        df_display = df.copy()

        # 원본 ticker 값을 먼저 저장 (HTML 변환 전)
        original_ticker = df_display['ticker'].copy() if 'ticker' in df_display.columns else None

        # Name 컬럼이 있는 경우 네이버 차트 페이지 링크로 변환 (ticker 변환 전에 처리)
        if 'name' in df_display.columns and original_ticker is not None:
            name_links = []
            for pos, (idx, row) in enumerate(df_display.iterrows()):
                if pd.notna(row.get('ticker')):
                    ticker_code = str(row['ticker']).zfill(6)
                    name = row['name']
                    link = f'<a href="https://finance.naver.com/item/fchart.naver?code={ticker_code}" target="_blank">{name}</a>'
                    name_links.append(link)
                else:
                    name_links.append(row['name'])

            df_display['name'] = name_links

        # Ticker 컬럼이 있는 경우 네이버 주식 페이지 링크로 변환
        if 'ticker' in df_display.columns:
            df_display['ticker'] = df_display['ticker'].apply(
                lambda x: f'<a href="https://finance.naver.com/item/main.naver?code={str(x).zfill(6)}" target="_blank">{str(x).zfill(6)}</a>'
                if pd.notna(x) else x
            )

        return df_display

    # ===== 엑셀 내보내기 헬퍼 함수 =====
    def get_excel_download_link(df, filename):
        """
        xlsxwriter를 사용하여 HYPERLINK 수식으로 클릭 가능한 링크 생성
        원본 데이터프레임에서 ticker/name으로 직접 URL 생성
        """
        try:
            from io import BytesIO

            # xlsxwriter 자동 설치
            try:
                import xlsxwriter
            except ImportError:
                import subprocess
                subprocess.check_call(['pip', 'install', 'xlsxwriter', '-q'])
                import xlsxwriter

            # 원본 데이터프레임 복사
            df_for_excel = df.copy()

            # Ticker 컬럼: 6자리 zero-pad된 코드로 URL 생성
            if 'ticker' in df_for_excel.columns:
                def create_ticker_hyperlink(val):
                    if pd.isna(val):
                        return val
                    ticker_code = str(val).zfill(6)
                    url = f"https://finance.naver.com/item/main.naver?code={ticker_code}"
                    return f'=HYPERLINK("{url}", "{ticker_code}")'

                df_for_excel['ticker'] = df_for_excel['ticker'].apply(create_ticker_hyperlink)

            # Name 컬럼: ticker 값을 사용하여 URL 생성
            if 'name' in df_for_excel.columns and 'ticker' in df_for_excel.columns:
                # 원본 df의 ticker를 참조하기 위해 먼저 계산
                original_ticker = df['ticker'].copy().reset_index(drop=True)

                # 반복문에서 위치 인덱스(position) 사용
                for pos, (idx, row) in enumerate(df_for_excel.iterrows()):
                    if pd.notna(row.get('name')) and pos < len(original_ticker) and pd.notna(original_ticker.iloc[pos]):
                        ticker_code = str(original_ticker.iloc[pos]).zfill(6)
                        url = f"https://finance.naver.com/item/fchart.naver?code={ticker_code}"
                        df_for_excel.loc[idx, 'name'] = f'=HYPERLINK("{url}", "{row["name"]}")'

            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_for_excel.to_excel(writer, sheet_name='데이터', index=False)

                # xlsxwriter 포맷 정의
                workbook = writer.book
                worksheet = writer.sheets['데이터']

                # Ticker 컬럼: 파란색 폰트
                ticker_format = workbook.add_format({
                    'font_color': '#0563C1',  # 파란색
                    'underline': True,
                })

                # Name 컬럼: 검은색 Bold
                name_format = workbook.add_format({
                    'font_color': '#000000',  # 검은색
                    'bold': True,
                })

                # Ticker 컬럼에 포맷 적용
                if 'ticker' in df_for_excel.columns:
                    ticker_col_idx = list(df_for_excel.columns).index('ticker')
                    for row_idx in range(1, len(df_for_excel) + 1):
                        worksheet.write(row_idx, ticker_col_idx,
                                      df_for_excel.iloc[row_idx - 1, ticker_col_idx],
                                      ticker_format)

                # Name 컬럼에 포맷 적용
                if 'name' in df_for_excel.columns:
                    name_col_idx = list(df_for_excel.columns).index('name')
                    for row_idx in range(1, len(df_for_excel) + 1):
                        worksheet.write(row_idx, name_col_idx,
                                      df_for_excel.iloc[row_idx - 1, name_col_idx],
                                      name_format)

            excel_data = output.getvalue()
            return excel_data
        except Exception as e:
            st.error(f"엑셀 생성 실패: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
            return None

    tab_data1, tab_data2 = st.tabs(["추천 종목", "급등주"])

    # ===== 탭 1: 추천 종목 =====
    with tab_data1:
        if 'filtered_results' in st.session_state and st.session_state.filtered_results is not None:
            results_df = st.session_state.filtered_results

            # 다운로드 버튼
            col1, col2 = st.columns([4, 1])
            with col2:
                excel_data = get_excel_download_link(results_df, '추천종목.xlsx')
                if excel_data:
                    st.download_button(
                        label="📥 엑셀 다운로드",
                        data=excel_data,
                        file_name=f"추천종목_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

            # 클릭 가능한 링크가 포함된 테이블
            display_df = create_clickable_dataframe(results_df, "tab_data1")
            if display_df is not None:
                st.markdown(display_df.to_html(escape=False), unsafe_allow_html=True)
                st.caption(f"총 {len(results_df)}개 종목")
            else:
                st.info("표시할 데이터가 없습니다.")
        else:
            st.info("데이터가 없습니다. 먼저 분석을 실행해주세요.")

    # ===== 탭 2: 급등주 =====
    with tab_data2:
        if 'talib_results' in st.session_state and st.session_state.talib_results is not None:
            talib_df = st.session_state.talib_results

            # 다운로드 버튼
            col1, col2 = st.columns([4, 1])
            with col2:
                excel_data = get_excel_download_link(talib_df, '급등주.xlsx')
                if excel_data:
                    st.download_button(
                        label="📥 엑셀 다운로드",
                        data=excel_data,
                        file_name=f"급등주_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

            # 클릭 가능한 링크가 포함된 테이블
            display_df = create_clickable_dataframe(talib_df, "tab_data2")
            if display_df is not None:
                st.markdown(display_df.to_html(escape=False), unsafe_allow_html=True)
                st.caption(f"총 {len(talib_df)}개 종목")
            else:
                st.info("표시할 데이터가 없습니다.")
        else:
            st.info("데이터가 없습니다. 먼저 분석을 실행해주세요.")

with tabs[4]:
    st.header("ℹ️ 정보")

    st.markdown("""
    ## 🎯 스윙매매 종목 추천 시스템

    ### 📚 기술적 분석 방법

    #### 1. 추천 종목 (SwingTradeAnalyzer)
    - **이동평균선**: 5, 10, 20, 60, 120일 정배열 확인
    - **RSI**: 과매수/과매도 구간 피하기 (30~70)
    - **MACD**: 매수/매도 신호 확인
    - **변동성**: 적절한 변동성 (2~8%)
    - **거래량**: 평균 이상의 유동성

    #### 2. 급등주 찾기 (TA-Lib)
    - **Morning Star**: 저점 > 중간 > 종가 패턴
    - **Bullish Breakaway**: 저점 돌파 상승 추세
    - **기간**: 최근 6개월 데이터 분석


    ### ⚙️ 사용 방법

    1. **🎯 추천 종목 탭**
       - "🔍 추천 종목 분석 시작" 버튼으로 분석 시작
       - 자동으로 점수 50점 이상의 추천 종목만 분석
       - 분석 완료 후 추천 종목 목록 확인
       - 각 종목의 상세 정보 조회

    2. **📈 차트 분석 탭**
       - 추천된 종목 선택
       - 기술적 지표와 이동평균선 차트 분석
       - 추세 변화 모니터링

    3. **🚀 급등주 찾기 탭**
       - "🔍 새로운 급등주 스캔" 버튼으로 분석
       - TA-Lib 패턴 종목 확인
       - Morning Star, Bullish Breakaway 패턴 분석

    4. **📊 데이터 테이블 탭**
       - 분석 결과를 테이블로 조회
       - CSV 다운로드 가능

    ### 📊 분석 지표 설명

    **이동평균선 (Moving Average)**
    - 일정 기간의 평균 종가
    - 추세 판단의 기본 지표
    - 정배열: 상승추세 / 역배열: 하락추세

    **RSI (Relative Strength Index)**
    - 0~100 사이의 값
    - 70 이상: 과매수 / 30 이하: 과매도
    - 30~70 범위: 정상 범위

    **MACD (Moving Average Convergence Divergence)**
    - 12일 EMA - 26일 EMA
    - Signal line: 9일 EMA
    - MACD > Signal: 매수신호 / MACD < Signal: 매도신호

    **거래량 (Volume)**
    - 주식의 거래 수량
    - 높은 거래량: 추세 신뢰도 증가
    - 평균 이상의 거래량: 유동성 확보

    ### ⚠️ 주의사항

    1. **투자 판단**: 본 시스템은 참고 자료일 뿐, 투자 판단은 개인의 책임입니다.
    2. **시장 변동성**: 기술적 분석만으로는 수익을 보장할 수 없습니다.
    3. **손실 관리**: 충분한 검토 후 적절한 매매 규칙으로 거래하세요.
    4. **리스크 관리**: 자산의 일정 비율만 투자하고 손절매 설정을 권장합니다.

    ### 📞 피드백

    - 시스템 개선 사항이나 버그 리포트는 언제든지 환영합니다.
    - 분석 기법 개선, 새로운 지표 추가 등의 제안도 받습니다.

    ---

    **마지막 업데이트**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """)

# 푸터
st.divider()
st.markdown("""
<div style='text-align: center; color: #999; font-size: 0.8rem; margin-top: 2rem;'>
    📊 스윙매매 종목 추천 시스템 | 기술적 분석 기반 |
    ⚠️ 투자 판단은 본인의 책임입니다. 충분한 검토 후 투자하세요.
</div>
""", unsafe_allow_html=True)
