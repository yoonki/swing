"""
TA-Lib 기반 급등주 찾기 UI 모듈
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import FinanceDataReader as fdr
from swing_analyzer import TalibPatternFinder, SwingTradeAnalyzer

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False


def get_stock_data_for_chart(ticker, days=500):
    """차트용 주식 데이터 조회"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # FinanceDataReader는 한국 ticker 코드 그대로 사용 (예: 005930)
        ticker_symbol = str(ticker).zfill(6)

        df = fdr.DataReader(
            ticker_symbol,
            start_date,
            end_date
        )

        if df is None or len(df) < 100:
            return None

        # MultiIndex 처리
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 컬럼명 정리
        df.columns = [str(col).strip() for col in df.columns]
        df.columns = [col[0].upper() + col[1:].lower() if len(col) > 0 else col for col in df.columns]

        # 컬럼 매핑
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
            elif col_lower in ['adj close', 'adj_close']:
                col_map[col] = 'Adj Close'

        if col_map:
            df.rename(columns=col_map, inplace=True)

        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in required_cols):
            return None

        df[required_cols] = df[required_cols].apply(pd.to_numeric, errors='coerce')
        df = df.dropna(subset=required_cols)

        if len(df) < 100:
            return None

        return df[required_cols]

    except Exception as e:
        return None


def detect_patterns_in_dataframe(df):
    """
    데이터프레임에서 패턴 감지 및 인덱스 반환

    Returns:
        {
            'morning_star_indices': [인덱스들],
            'breakaway_indices': [인덱스들],
            'morning_star_values': [값들],
            'breakaway_values': [값들]
        }
    """
    if df is None or len(df) < 100:
        return None

    try:
        open_arr = df['Open'].values
        high_arr = df['High'].values
        low_arr = df['Low'].values
        close_arr = df['Close'].values

        # 패턴 감지
        morning_star = talib.CDLMORNINGSTAR(open_arr, high_arr, low_arr, close_arr)
        breakaway = talib.CDLBREAKAWAY(open_arr, high_arr, low_arr, close_arr)

        # 패턴이 감지된 인덱스 찾기
        morning_star_indices = np.where(morning_star != 0)[0]
        breakaway_indices = np.where(breakaway != 0)[0]

        return {
            'morning_star_indices': morning_star_indices.tolist(),
            'breakaway_indices': breakaway_indices.tolist(),
            'morning_star_array': morning_star,
            'breakaway_array': breakaway
        }

    except Exception as e:
        return None


def create_pattern_chart(df, ticker, name, pattern_info, pattern_type='morning_star'):
    """
    패턴이 표시된 차트 생성

    Args:
        df: 가격 데이터
        ticker: 종목코드
        name: 종목명
        pattern_info: 패턴 정보 (인덱스 등)
        pattern_type: 'morning_star' 또는 'breakaway'
    """
    if df is None or pattern_info is None:
        return None

    try:
        # 이동평균선 계산
        df = df.copy()
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()

        # 캔들스틱 차트 생성
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='가격'
        )])

        # 이동평균선 추가
        fig.add_trace(go.Scatter(
            x=df.index, y=df['MA5'],
            name='MA5',
            line=dict(color='red', width=1),
            opacity=0.7
        ))
        fig.add_trace(go.Scatter(
            x=df.index, y=df['MA20'],
            name='MA20',
            line=dict(color='blue', width=1),
            opacity=0.7
        ))
        fig.add_trace(go.Scatter(
            x=df.index, y=df['MA60'],
            name='MA60',
            line=dict(color='green', width=1),
            opacity=0.7
        ))

        # 패턴이 감지된 위치에 표시 추가
        if pattern_type == 'morning_star':
            indices = pattern_info.get('morning_star_indices', [])
            pattern_label = '🌅 Morning Star'
            marker_color = 'yellow'
        else:
            indices = pattern_info.get('breakaway_indices', [])
            pattern_label = '⚡ Breakaway'
            marker_color = 'orange'

        # 패턴 인덱스에 수직선과 마커 추가
        for idx in indices:
            if idx < len(df):
                pattern_date = df.index[idx]
                pattern_high = df.iloc[idx]['High']

                # 수직선 추가
                fig.add_vline(
                    x=pattern_date,
                    line_dash="dash",
                    line_color=marker_color,
                    opacity=0.7,
                    annotation_text=pattern_label,
                    annotation_position="top"
                )

                # 마커 추가
                fig.add_trace(go.Scatter(
                    x=[pattern_date],
                    y=[pattern_high],
                    mode='markers+text',
                    marker=dict(size=15, color=marker_color, symbol='diamond'),
                    text=[pattern_label],
                    textposition='top center',
                    showlegend=False,
                    hovertemplate=f'{pattern_label}<br>날짜: %{{x|%Y-%m-%d}}<extra></extra>'
                ))

        fig.update_layout(
            title=f'{name} ({ticker}) - {pattern_label} 패턴',
            yaxis_title='가격 (원)',
            xaxis_title='날짜',
            template='plotly_white',
            height=600,
            xaxis_rangeslider_visible=False,
            hovermode='x unified'
        )

        return fig

    except Exception as e:
        return None


def render_talib_soaring_tab():
    """TA-Lib 기반 급등주 찾기 탭 렌더링"""

    st.header("🚀 급등주 찾기 (TA-Lib 기반)")
    st.subheader("과거 6개월 동안 Morning Star와 Bullish Breakaway 패턴이 나타난 종목")
    st.caption("TA-Lib의 캔들스틱 패턴 인식 기능을 사용하여 정확한 패턴 감지")

    if not TALIB_AVAILABLE:
        st.error("❌ ta-lib이 설치되지 않았습니다.")
        st.info("설치 방법: `pip install ta-lib` 또는 `conda install -c conda-forge ta-lib`")
        return

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        find_talib_patterns = st.button(
            "🔍 새로운 스캔 실행",
            use_container_width=True,
            type="primary",
            help="TA-Lib을 사용하여 패턴 스캔을 실행합니다"
        )

    with col2:
        refresh_talib_cache = st.button(
            "🔄 캐시 삭제",
            use_container_width=True,
            help="저장된 캐시를 삭제합니다"
        )

    with col3:
        talib_scan_mode = st.selectbox(
            "스캔 범위",
            options=["전체 (958개)", "빠른 스캔 (200개)", "테스트 (50개)"],
            help="스캔할 종목의 수를 선택합니다",
            key="talib_scan_mode"
        )

    # 진행 상황 표시 영역
    talib_progress_placeholder = st.empty()
    talib_status_placeholder = st.empty()
    talib_current_placeholder = st.empty()
    talib_progress_bar_placeholder = st.empty()

    # 캐시 삭제
    if refresh_talib_cache:
        finder = TalibPatternFinder()
        cache_path = finder.get_talib_week_cache_filepath()
        import os
        if os.path.exists(cache_path):
            os.remove(cache_path)
            st.session_state.talib_results = None
            with talib_status_placeholder.container():
                st.info("✅ 캐시가 삭제되었습니다.")

    # 앱 로드 시 자동으로 캐시된 데이터 검색 및 로드
    if st.session_state.talib_results is None and 'talib_historical_cache_checked' not in st.session_state:
        st.session_state.talib_historical_cache_checked = True
        finder = TalibPatternFinder()

        # 지난 7일간의 캐시 파일 검색
        import glob
        from pathlib import Path

        today = datetime.now().date()
        cached_results = None

        for days_back in range(8):
            check_date = today - timedelta(days=days_back)
            cached_data = finder.load_talib_week_patterns(date=check_date)

            if cached_data is not None and len(cached_data) > 0:
                cached_results = cached_data
                break

        if cached_results is not None and len(cached_results) > 0:
            st.session_state.talib_results = cached_results
            with talib_status_placeholder.container():
                ms_count = len(cached_results[cached_results['pattern_type'].str.contains('Morning Star', na=False)])
                ba_count = len(cached_results[cached_results['pattern_type'].str.contains('Breakaway', na=False)])
                st.info(f"💾 캐시 데이터 로드됨 - Morning Star {ms_count}개, Bullish Breakaway {ba_count}개 (총 {len(cached_results)}개)")

    if find_talib_patterns:
        # 스캔 범위 설정
        talib_mode_map = {
            "전체 (958개)": None,
            "빠른 스캔 (200개)": 200,
            "테스트 (50개)": 50
        }
        max_talib_stocks = talib_mode_map.get(talib_scan_mode, None)

        try:
            finder = TalibPatternFinder()
            analyzer = SwingTradeAnalyzer()
            kospi_stocks = analyzer.get_kospi_stocks()

            if not kospi_stocks.empty:
                if max_talib_stocks:
                    kospi_stocks = kospi_stocks.head(max_talib_stocks)

                with talib_status_placeholder.container():
                    st.info(f"📊 {len(kospi_stocks)}개 종목 스캔 중 (TA-Lib 패턴 감지)...")

                # 진행 상황 콜백
                def talib_progress_callback(idx, total, name, ticker, found_count, success):
                    with talib_progress_bar_placeholder.container():
                        progress = idx / total
                        st.progress(progress, text=f"진행: {idx}/{total} ({progress*100:.0f}%)")

                    with talib_current_placeholder.container():
                        status_text = "✓" if success else "✗"
                        st.caption(f"{status_text} 검사 중: {name} ({ticker}) | 발견: {found_count}개")

                # 패턴 스캔
                results = finder.find_patterns_in_week(kospi_stocks, progress_callback=talib_progress_callback)

                if not results.empty:
                    # 결과 저장
                    finder.save_talib_week_patterns(results)
                    st.session_state.talib_results = results
                    # 차트 데이터 초기화
                    st.session_state.talib_chart_data = {}

                    with talib_status_placeholder.container():
                        ms_count = len(results[results['pattern_type'].str.contains('Morning Star', na=False)])
                        ba_count = len(results[results['pattern_type'].str.contains('Breakaway', na=False)])
                        st.success(f"✅ 스캔 완료! Morning Star {ms_count}개, Bullish Breakaway {ba_count}개 발견 (캐시 저장됨)")
                else:
                    with talib_status_placeholder.container():
                        st.warning(f"⚠️ 조건을 만족하는 패턴이 없습니다.")

        except Exception as e:
            with talib_status_placeholder.container():
                st.error(f"스캔 중 오류 발생: {str(e)}")

    # 결과 표시
    if st.session_state.talib_results is not None and len(st.session_state.talib_results) > 0:
        talib_df = st.session_state.talib_results

        # 패턴별 필터링
        morning_star_df = talib_df[talib_df['pattern_type'].str.contains('Morning Star', na=False)]
        bullish_breakaway_df = talib_df[talib_df['pattern_type'].str.contains('Breakaway', na=False)]

        # 통계
        st.subheader("📊 검색 결과 요약")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🌅 Morning Star", len(morning_star_df))
        with col2:
            st.metric("⚡ Bullish Breakaway", len(bullish_breakaway_df))
        with col3:
            st.metric("📈 전체 발견", len(talib_df))

        st.divider()

        # 탭 생성
        tab_all, tab_ms, tab_ba, tab_chart = st.tabs(["📊 전체 결과", "🌅 Morning Star", "⚡ Bullish Breakaway", "📈 차트 분석"])

        # ============ TAB: 전체 결과 ============
        with tab_all:
            if len(talib_df) > 0:
                # CSV 다운로드
                csv_data = talib_df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 전체 결과 CSV 다운로드",
                    data=csv_data,
                    file_name=f"talib_patterns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                st.divider()

                # 데이터 추출 시간
                if 'extraction_time' in talib_df.columns:
                    extraction_time = talib_df.iloc[0]['extraction_time']
                    st.caption(f"📊 데이터 추출: {extraction_time}")

                # 테이블 표시
                display_df = talib_df[['pattern_type', 'name', 'ticker', 'current_price', 'pattern_date']].copy()
                display_df.columns = ['패턴', '종목명', '티커', '현재가', '패턴 발생일']
                display_df['순위'] = range(1, len(display_df) + 1)
                display_df = display_df[['순위', '패턴', '종목명', '티커', '현재가', '패턴 발생일']]

                # 티커 포맷 (네이버증권 링크)
                display_df['티커_temp'] = display_df['티커'].astype(str).str.zfill(6)
                display_df['티커'] = display_df['티커_temp'].apply(
                    lambda ticker: f'<a href="https://finance.naver.com/item/main.naver?code={str(ticker)}" target="_blank">{str(ticker)}</a>'
                )
                display_df = display_df.drop('티커_temp', axis=1)

                # 가격 포맷
                display_df['현재가'] = display_df['현재가'].apply(lambda x: f'₩{x:,.0f}')

                st.markdown(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)
                st.caption("💡 팁: 티커를 클릭하면 네이버 증권에서 종목 정보를 확인할 수 있습니다")

        # ============ TAB: Morning Star ============
        with tab_ms:
            if len(morning_star_df) > 0:
                # CSV 다운로드
                csv_data = morning_star_df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 Morning Star CSV 다운로드",
                    data=csv_data,
                    file_name=f"morning_star_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                st.divider()

                # 테이블 표시
                display_ms_df = morning_star_df[['name', 'ticker', 'current_price', 'pattern_date']].copy()
                display_ms_df.columns = ['종목명', '티커', '현재가', '패턴 발생일']
                display_ms_df['순위'] = range(1, len(display_ms_df) + 1)
                display_ms_df = display_ms_df[['순위', '종목명', '티커', '현재가', '패턴 발생일']]

                # 티커 포맷
                display_ms_df['티커_temp'] = display_ms_df['티커'].astype(str).str.zfill(6)
                display_ms_df['티커'] = display_ms_df['티커_temp'].apply(
                    lambda ticker: f'<a href="https://finance.naver.com/item/main.naver?code={str(ticker)}" target="_blank">{str(ticker)}</a>'
                )
                display_ms_df = display_ms_df.drop('티커_temp', axis=1)

                # 가격 포맷
                display_ms_df['현재가'] = display_ms_df['현재가'].apply(lambda x: f'₩{x:,.0f}')

                st.markdown(display_ms_df.to_html(escape=False, index=False), unsafe_allow_html=True)
            else:
                st.info("🌅 Morning Star 패턴이 발견되지 않았습니다.")

        # ============ TAB: Bullish Breakaway ============
        with tab_ba:
            if len(bullish_breakaway_df) > 0:
                # CSV 다운로드
                csv_data = bullish_breakaway_df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 Bullish Breakaway CSV 다운로드",
                    data=csv_data,
                    file_name=f"bullish_breakaway_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                st.divider()

                # 테이블 표시
                display_ba_df = bullish_breakaway_df[['name', 'ticker', 'current_price', 'pattern_date']].copy()
                display_ba_df.columns = ['종목명', '티커', '현재가', '패턴 발생일']
                display_ba_df['순위'] = range(1, len(display_ba_df) + 1)
                display_ba_df = display_ba_df[['순위', '종목명', '티커', '현재가', '패턴 발생일']]

                # 티커 포맷
                display_ba_df['티커_temp'] = display_ba_df['티커'].astype(str).str.zfill(6)
                display_ba_df['티커'] = display_ba_df['티커_temp'].apply(
                    lambda ticker: f'<a href="https://finance.naver.com/item/main.naver?code={str(ticker)}" target="_blank">{str(ticker)}</a>'
                )
                display_ba_df = display_ba_df.drop('티커_temp', axis=1)

                # 가격 포맷
                display_ba_df['현재가'] = display_ba_df['현재가'].apply(lambda x: f'₩{x:,.0f}')

                st.markdown(display_ba_df.to_html(escape=False, index=False), unsafe_allow_html=True)
            else:
                st.info("⚡ Bullish Breakaway 패턴이 발견되지 않았습니다.")

        # ============ TAB: 차트 분석 ============
        with tab_chart:
            if len(talib_df) > 0:
                # 초기 선택 설정
                if st.session_state.selected_talib_stock is None:
                    stock_list = talib_df['name'].tolist()
                    if stock_list:
                        st.session_state.selected_talib_stock = stock_list[0]

                stock_list = talib_df['name'].tolist()

                # 네비게이션 콜백
                def on_prev_talib():
                    if st.session_state.selected_talib_stock in stock_list:
                        current_idx = stock_list.index(st.session_state.selected_talib_stock)
                        if current_idx > 0:
                            st.session_state.selected_talib_stock = stock_list[current_idx - 1]

                def on_next_talib():
                    if st.session_state.selected_talib_stock in stock_list:
                        current_idx = stock_list.index(st.session_state.selected_talib_stock)
                        if current_idx < len(stock_list) - 1:
                            st.session_state.selected_talib_stock = stock_list[current_idx + 1]

                def on_select_talib():
                    st.session_state.selected_talib_stock = st.session_state.talib_stock_select

                # 네비게이션 UI
                col1, col2, col3, col4 = st.columns([0.8, 2, 1, 1])

                with col1:
                    st.button("◀ 이전", key="prev_talib_btn", on_click=on_prev_talib, use_container_width=True)

                with col2:
                    if st.session_state.selected_talib_stock in stock_list:
                        current_idx = stock_list.index(st.session_state.selected_talib_stock)
                        st.selectbox(
                            "종목 선택",
                            options=stock_list,
                            index=current_idx,
                            key="talib_stock_select",
                            on_change=on_select_talib,
                            label_visibility="collapsed"
                        )

                with col3:
                    st.button("다음 ▶", key="next_talib_btn", on_click=on_next_talib, use_container_width=True)

                if st.session_state.selected_talib_stock:
                    # 선택한 종목의 정보
                    stock_info = talib_df[
                        talib_df['name'] == st.session_state.selected_talib_stock
                    ].iloc[0]

                    ticker = str(stock_info['ticker']).zfill(6)

                    # 헤더
                    st.markdown(f"""
                    ### 📈 [{st.session_state.selected_talib_stock} ({ticker})](https://finance.naver.com/item/main.naver?code={ticker})
                    **패턴**: {stock_info['pattern_type']} | **발생일**: {stock_info['pattern_date']}
                    """)

                    st.divider()

                    # 차트 데이터 조회
                    with st.spinner("📊 차트 데이터 로드 중..."):
                        if ticker not in st.session_state.talib_chart_data:
                            chart_df = get_stock_data_for_chart(ticker, days=500)
                            if chart_df is not None:
                                st.session_state.talib_chart_data[ticker] = chart_df
                            else:
                                st.error(f"❌ {stock_info['name']} ({ticker})의 데이터를 찾을 수 없습니다.")
                                chart_df = None
                        else:
                            chart_df = st.session_state.talib_chart_data[ticker]

                    if chart_df is not None and len(chart_df) > 0:
                        # 패턴 정보 감지
                        pattern_info = detect_patterns_in_dataframe(chart_df)

                        # 차트 생성
                        if pattern_info:
                            if stock_info['pattern_type'].startswith('🌅'):
                                fig = create_pattern_chart(chart_df, ticker, stock_info['name'], pattern_info, 'morning_star')
                            else:
                                fig = create_pattern_chart(chart_df, ticker, stock_info['name'], pattern_info, 'breakaway')

                            if fig:
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.error("차트를 생성할 수 없습니다.")
                        else:
                            st.error("패턴 정보를 감지할 수 없습니다.")

                        # 거래량 차트
                        st.subheader("📊 거래량")
                        colors = ['green' if chart_df['Close'].iloc[i] >= chart_df['Open'].iloc[i] else 'red'
                                  for i in range(len(chart_df))]

                        fig_volume = go.Figure()
                        fig_volume.add_trace(go.Bar(
                            x=chart_df.index,
                            y=chart_df['Volume'],
                            name='거래량',
                            marker=dict(color=colors),
                            showlegend=False
                        ))

                        fig_volume.update_layout(
                            title=f'{stock_info["name"]} ({ticker}) - 거래량',
                            yaxis_title='거래량',
                            xaxis_title='날짜',
                            template='plotly_white',
                            height=350,
                            xaxis_rangeslider_visible=False,
                            hovermode='x unified'
                        )

                        st.plotly_chart(fig_volume, use_container_width=True)
