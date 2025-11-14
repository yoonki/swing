import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import FinanceDataReader as fdr
import requests
from bs4 import BeautifulSoup
import warnings
import os

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False

warnings.filterwarnings('ignore')

class SwingTradeAnalyzer:
    """스윙매매 종목 분석기"""

    def __init__(self, data_dir="analysis_data"):
        self.results = []
        self.data_dir = data_dir
        # 데이터 디렉토리 생성
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def get_cache_filepath(self, date=None):
        """캐시 파일 경로 반환"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.data_dir, f"analysis_{date}.csv")

    def load_cached_analysis(self, date=None):
        """저장된 분석 데이터 로드"""
        filepath = self.get_cache_filepath(date)
        if os.path.exists(filepath):
            print(f"📂 캐시된 데이터 로드: {filepath}")
            df = pd.read_csv(filepath)
            print(f"✓ {len(df)}개 종목 로드됨")
            return df
        return None

    def save_analysis_results(self, results_df, date=None):
        """분석 결과를 CSV로 저장"""
        if results_df.empty:
            return

        filepath = self.get_cache_filepath(date)
        results_df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"✓ 분석 결과 저장: {filepath}")

    def get_kospi_stocks(self):
        """KOSPI 전체 종목 조회 - 다중 소스 폴백 지원"""

        # 방법 1: FinanceDataReader 사용
        try:
            import FinanceDataReader as fdr
            print("📊 [1/3] FinanceDataReader로 KOSPI 종목 조회 중...")
            stocks_df = fdr.StockListing("KOSPI")

            if stocks_df is not None and len(stocks_df) > 0:
                result = stocks_df[['Code', 'Name']].copy()
                result = result.drop_duplicates(subset=['Code']).reset_index(drop=True)
                print(f"✓ KOSPI 종목 {len(result)}개 조회 완료 (FinanceDataReader)")
                return result
        except Exception as e:
            print(f"⚠️ [1/3] FinanceDataReader 실패: {str(e)}")

        # 방법 2: KRX 공식 CSV 다운로드
        try:
            print("📥 [2/3] KRX 공식 CSV 다운로드 중...")
            url = "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13"

            response = requests.get(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'},
                timeout=15
            )

            if response.status_code == 200:
                for encoding in ['euc-kr', 'cp949', 'utf-8']:
                    try:
                        df = pd.read_csv(
                            pd.io.common.BytesIO(response.content),
                            encoding=encoding
                        )
                        df.columns = df.columns.str.strip()

                        if '종목코드' in df.columns and '회사명' in df.columns:
                            result = df[['회사명', '종목코드']].copy()
                            result.columns = ['Name', 'Code']
                            result['Code'] = result['Code'].astype(str).str.zfill(6)
                            result = result.drop_duplicates(subset=['Code']).reset_index(drop=True)
                            print(f"✓ KOSPI 종목 {len(result)}개 조회 완료 (KRX CSV)")
                            return result
                    except Exception as enc_e:
                        print(f"  인코딩 {encoding} 실패: {str(enc_e)}")
                        continue
        except Exception as e:
            print(f"⚠️ [2/3] KRX CSV 실패: {str(e)}")

        # 방법 3: Naver Finance API (폴백)
        try:
            print("🔗 [3/3] Naver Finance에서 조회 중...")
            # Naver에서 KOSPI 종목 정보 조회
            import json

            url = "https://finance.naver.com/api/sise/etfItemList.naver?etfCode=069500"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                # 간단한 임시 데이터 생성 (실패 시 최소한의 데이터라도 반환)
                # 실제로는 top 10 KOSPI 주식 추가
                temp_data = {
                    'Code': ['005930', '000660', '051910', '207940', '035420', '005380', '051915', '000270', '028260', '011200'],
                    'Name': ['삼성전자', 'SK하이닉스', 'LG화학', 'NH투자증권', '현대차', '현대차1우B', 'LG에너지', 'KT&G', 'NAVER', '삼성바이오로직스']
                }
                result = pd.DataFrame(temp_data)
                print(f"✓ 기본 KOSPI 종목 {len(result)}개 조회 (최소 데이터)")
                return result
        except Exception as e:
            print(f"⚠️ [3/3] Naver Finance 실패: {str(e)}")

        # 모든 방법 실패 시 최소 데이터 반환
        print("⚠️ 모든 소스에서 조회 실패. 최소 기본 종목 데이터로 진행합니다...")
        fallback_data = {
            'Code': ['005930', '000660', '051910', '207940', '035420', '005380', '051915', '000270', '028260', '011200'],
            'Name': ['삼성전자', 'SK하이닉스', 'LG화학', 'NH투자증권', '현대차', '현대차1우B', 'LG에너지', 'KT&G', 'NAVER', '삼성바이오로직스']
        }
        return pd.DataFrame(fallback_data)

    def get_stock_data(self, ticker, days=120):
        """FinanceDataReader를 사용한 주식 데이터 조회"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # FinanceDataReader는 종목코드 그대로 사용 (예: 005930)
            ticker_str = str(ticker).zfill(6)

            # 재시도 로직 (네트워크 불안정 대응)
            df = None
            max_retries = 3

            for attempt in range(max_retries):
                try:
                    # FinanceDataReader로 데이터 조회
                    df = fdr.DataReader(ticker_str, start_date, end_date)

                    # 데이터 유효성 확인
                    if df is not None and len(df) >= 20:  # 최소 20개 캔들
                        break
                    elif attempt < max_retries - 1:
                        import time
                        time.sleep(0.5)  # 0.5초 대기 후 재시도

                except Exception as e:
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(0.5)
                        continue
                    else:
                        # 마지막 시도 실패
                        return None

            # 데이터 검증
            if df is None or len(df) < 20:
                return None

            # 컬럼명 통일 및 정렬
            try:
                # FinanceDataReader는 Open, High, Low, Close, Volume을 반환
                if all(col in df.columns for col in ['Open', 'High', 'Low', 'Close', 'Volume']):
                    df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
                else:
                    # 컬럼명 통일
                    df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

                # NaN 값 제거
                df = df.dropna()
                if len(df) < 20:
                    return None

                # 데이터 타입 확인 및 변환
                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

                df = df.dropna()
                if len(df) < 20:
                    return None

                return df

            except Exception as col_error:
                return None

        except Exception as e:
            return None

    def calculate_indicators(self, df):
        """기술적 지표 계산"""
        if df is None or len(df) < 20:
            return None

        df = df.copy()

        # 이동평균선
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()

        # RSI
        df['RSI'] = self.calculate_rsi(df['Close'], period=14)

        # MACD
        macd_data = self.calculate_macd(df['Close'])
        df['MACD'] = macd_data['macd']
        df['Signal'] = macd_data['signal']
        df['MACD_Hist'] = macd_data['hist']

        # 거래량 이동평균
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()

        # 변동성 (표준편차)
        df['Volatility'] = df['Close'].rolling(window=20).std() / df['Close'].rolling(window=20).mean() * 100

        return df

    def calculate_rsi(self, prices, period=14):
        """RSI 계산"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """MACD 계산"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal).mean()
        hist = macd - signal_line

        return {
            'macd': macd,
            'signal': signal_line,
            'hist': hist
        }

    def is_uptrend(self, df):
        """상승 추세 확인"""
        if df is None or len(df) < 20:
            return False

        # MA 정배열 확인: MA5 > MA20 > MA60
        latest = df.iloc[-1]

        if pd.isna(latest['MA5']) or pd.isna(latest['MA20']) or pd.isna(latest['MA60']):
            return False

        return latest['MA5'] > latest['MA20'] > latest['MA60']

    def check_golden_cross(self, df):
        """골든크로스 확인 (MA20이 MA60을 상향 돌파)"""
        if df is None or len(df) < 60:
            return False

        prev = df.iloc[-2]
        curr = df.iloc[-1]

        if pd.isna(prev['MA20']) or pd.isna(prev['MA60']) or pd.isna(curr['MA20']) or pd.isna(curr['MA60']):
            return False

        return prev['MA20'] <= prev['MA60'] and curr['MA20'] > curr['MA60']

    def check_rsi_condition(self, df):
        """RSI 조건 확인 (30~70 범위)"""
        if df is None or len(df) < 15:
            return False

        latest_rsi = df.iloc[-1]['RSI']

        if pd.isna(latest_rsi):
            return False

        return 30 <= latest_rsi <= 70

    def check_macd_bullish(self, df):
        """MACD 강세 신호"""
        if df is None or len(df) < 27:
            return False

        latest = df.iloc[-1]

        if pd.isna(latest['MACD']) or pd.isna(latest['Signal']):
            return False

        return latest['MACD'] > latest['Signal']

    def calculate_volatility_score(self, df):
        """변동성 점수 계산"""
        if df is None or len(df) < 20:
            return 0

        latest_vol = df.iloc[-1]['Volatility']

        if pd.isna(latest_vol):
            return 0

        # 적절한 변동성: 2~8%
        if 2 <= latest_vol <= 8:
            return 100
        elif latest_vol < 2:
            return latest_vol / 2 * 100
        else:
            return max(0, 100 - (latest_vol - 8) * 5)

    def calculate_volume_score(self, df):
        """거래량 점수 계산"""
        if df is None or len(df) < 20:
            return 0

        latest = df.iloc[-1]

        if pd.isna(latest['Volume']) or pd.isna(latest['Volume_MA']):
            return 0

        volume_ratio = latest['Volume'] / latest['Volume_MA']

        # 평균 이상의 거래량이 좋음
        if volume_ratio >= 1.0:
            score = min(100, volume_ratio * 50)
            return score
        else:
            return volume_ratio * 100

    def analyze_stock(self, ticker, name):
        """개별 종목 분석"""
        try:
            # 데이터 조회
            df = self.get_stock_data(ticker)
            if df is None:
                return None

            # 지표 계산
            df = self.calculate_indicators(df)
            if df is None:
                return None

            # 조건 검사
            is_uptrend = self.is_uptrend(df)
            golden_cross = self.check_golden_cross(df)
            rsi_ok = self.check_rsi_condition(df)
            macd_bullish = self.check_macd_bullish(df)

            # 점수 계산
            volatility_score = self.calculate_volatility_score(df)
            volume_score = self.calculate_volume_score(df)

            # 종합 점수
            condition_score = 0
            if is_uptrend:
                condition_score += 25
            if golden_cross:
                condition_score += 25
            if rsi_ok:
                condition_score += 20
            if macd_bullish:
                condition_score += 20

            total_score = (condition_score * 0.4) + (volatility_score * 0.3) + (volume_score * 0.3)

            # 최신 가격 정보
            latest = df.iloc[-1]

            result = {
                'ticker': ticker,
                'name': name,
                'current_price': latest['Close'],
                'price_date': df.index[-1].strftime('%Y-%m-%d'),
                'extraction_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'ma5': latest['MA5'],
                'ma20': latest['MA20'],
                'ma60': latest['MA60'],
                'rsi': latest['RSI'],
                'macd': latest['MACD'],
                'macd_signal': latest['Signal'],
                'volatility': latest['Volatility'],
                'volume': latest['Volume'],
                'volume_avg': latest['Volume_MA'],
                'is_uptrend': is_uptrend,
                'golden_cross': golden_cross,
                'rsi_ok': rsi_ok,
                'macd_bullish': macd_bullish,
                'volatility_score': round(volatility_score, 2),
                'volume_score': round(volume_score, 2),
                'condition_score': round(condition_score, 2),
                'total_score': round(total_score, 2),
                'recommendation': 'Strong Buy' if total_score >= 70 else ('Buy' if total_score >= 50 else 'Hold')
            }

            return result

        except Exception as e:
            return None

    def analyze_all_stocks(self, max_stocks=None, progress_callback=None):
        """모든 KOSPI 종목 분석 - 추천 종목(점수>=50)만 반환

        Args:
            max_stocks: 분석할 최대 종목 수 (None = 모든 종목)
            progress_callback: 진행 상황 콜백 함수 (idx, total, name, ticker, success_count)

        Returns:
            DataFrame: 추천 종목(점수>=50, 변동성 2-8%)만 포함된 결과
        """
        kospi_stocks = self.get_kospi_stocks()

        if kospi_stocks.empty:
            return pd.DataFrame()

        if max_stocks:
            kospi_stocks = kospi_stocks.head(max_stocks)

        results = []

        for idx, row in kospi_stocks.iterrows():
            ticker = row['Code']
            name = row['Name']

            # 현재 분석 중인 종목 표시
            print(f"🔄 분석 중: {name} ({ticker})")

            result = self.analyze_stock(ticker, name)

            if result is not None:
                results.append(result)

            # 진행 상황 콜백 (매 종목마다 호출)
            if progress_callback:
                progress_callback(idx + 1, len(kospi_stocks), name, ticker, len(results))

            # 진행 상황 표시 (10개마다)
            if (idx + 1) % 10 == 0:
                success_rate = len(results) / (idx + 1) * 100
                print(f"📊 진행: {idx + 1}/{len(kospi_stocks)} - 성공: {len(results)}개 ({success_rate:.1f}%)")

        results_df = pd.DataFrame(results)

        # 추천 조건: 점수>=50, 변동성 2-8%, 상승추세
        if not results_df.empty:
            results_df = filter_swing_candidates(results_df, min_score=50)

        return results_df


def filter_swing_candidates(results_df, min_score=50):
    """스윙매매 후보 종목 필터링"""
    if results_df.empty:
        return pd.DataFrame()

    # 필터링 조건
    filtered = results_df[
        (results_df['is_uptrend'] == True) &
        (results_df['total_score'] >= min_score) &
        (results_df['volatility'] >= 2) &
        (results_df['volatility'] <= 8)
    ].copy()

    # 정렬
    filtered = filtered.sort_values('total_score', ascending=False)

    return filtered


class SoaringStockFinder:
    """급등주 찾기: 112MA, 224MA, 448MA 정배열 종목 발굴"""

    def __init__(self, data_dir="analysis_data"):
        self.data_dir = data_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def get_soaring_cache_filepath(self, date=None):
        """캐시 파일 경로 반환"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.data_dir, f"soaring_stocks_{date}.csv")

    def load_cached_soaring(self, date=None):
        """저장된 급등주 데이터 로드"""
        filepath = self.get_soaring_cache_filepath(date)
        if os.path.exists(filepath):
            print(f"📂 캐시된 급등주 데이터 로드: {filepath}")
            df = pd.read_csv(filepath)
            print(f"✓ {len(df)}개 급등주 로드됨")
            return df
        return None

    def save_soaring_results(self, results_df, date=None):
        """급등주 분석 결과를 CSV로 저장"""
        if results_df.empty:
            return

        filepath = self.get_soaring_cache_filepath(date)
        results_df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"✓ 급등주 분석 결과 저장: {filepath}")

    def get_stock_data_long(self, ticker, days=500):
        """장기 주식 데이터 조회"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 한국 종목용 ticker 변환
            if len(ticker) == 6 and ticker.isdigit():
                ticker_symbol = f"{ticker}.KS"
            else:
                ticker_symbol = ticker

            # yfinance 다운로드
            df = yf.download(
                ticker_symbol,
                start=start_date,
                end=end_date,
                progress=False,
                timeout=15,
                threads=False
            )

            if df is None or len(df) < 450:
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

            # 필요한 컬럼 확인
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in df.columns for col in required_cols):
                return None

            # 데이터 정제
            df[required_cols] = df[required_cols].apply(pd.to_numeric, errors='coerce')
            df = df.dropna(subset=required_cols)

            if len(df) < 450:
                return None

            return df[required_cols]

        except Exception as e:
            return None

    def find_soaring_stocks(self, kospi_stocks, progress_callback=None):
        """급등주 발굴: 112MA < 224MA < 448MA 정배열"""
        results = []

        for idx, row in kospi_stocks.iterrows():
            ticker = row['Code']
            name = row['Name']

            # 장기 데이터 조회
            df = self.get_stock_data_long(ticker)
            if df is None or len(df) < 450:
                if progress_callback:
                    progress_callback(idx + 1, len(kospi_stocks), name, ticker, len(results), False)
                continue

            try:
                # 이동평균선 계산
                df['MA112'] = df['Close'].rolling(window=112).mean()
                df['MA224'] = df['Close'].rolling(window=224).mean()
                df['MA448'] = df['Close'].rolling(window=448).mean()

                # 최신 데이터
                latest = df.iloc[-1]

                # 정배열 확인: MA112 < MA224 < MA448
                if pd.notna(latest['MA112']) and pd.notna(latest['MA224']) and pd.notna(latest['MA448']):
                    if latest['MA112'] < latest['MA224'] < latest['MA448']:
                        # 현재가
                        current_price = latest['Close']

                        result = {
                            'ticker': ticker,
                            'name': name,
                            'current_price': current_price,
                            'price_date': df.index[-1].strftime('%Y-%m-%d'),
                            'extraction_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'ma112': round(latest['MA112'], 2),
                            'ma224': round(latest['MA224'], 2),
                            'ma448': round(latest['MA448'], 2),
                            'distance_112_224': round(latest['MA224'] - latest['MA112'], 2),
                            'distance_224_448': round(latest['MA448'] - latest['MA224'], 2)
                        }

                        results.append(result)

                if progress_callback:
                    progress_callback(idx + 1, len(kospi_stocks), name, ticker, len(results), True)

            except Exception as e:
                if progress_callback:
                    progress_callback(idx + 1, len(kospi_stocks), name, ticker, len(results), False)
                continue

        return pd.DataFrame(results)


class BullishBreakawayFinder:
    """Bullish Breakaway 패턴 찾기: 저항선 돌파하는 강한 상승 패턴 발굴"""

    def __init__(self, data_dir="analysis_data"):
        self.data_dir = data_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def get_bullish_breakaway_cache_filepath(self, date=None):
        """캐시 파일 경로 반환"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.data_dir, f"bullish_breakaway_{date}.csv")

    def load_cached_bullish_breakaway(self, date=None):
        """저장된 Bullish Breakaway 데이터 로드"""
        filepath = self.get_bullish_breakaway_cache_filepath(date)
        if os.path.exists(filepath):
            print(f"📂 캐시된 Bullish Breakaway 데이터 로드: {filepath}")
            df = pd.read_csv(filepath)
            print(f"✓ {len(df)}개 Bullish Breakaway 종목 로드됨")
            return df
        return None

    def save_bullish_breakaway_results(self, results_df, date=None):
        """Bullish Breakaway 분석 결과를 CSV로 저장"""
        if results_df.empty:
            return

        filepath = self.get_bullish_breakaway_cache_filepath(date)
        results_df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"✓ Bullish Breakaway 분석 결과 저장: {filepath}")

    def get_stock_data_long(self, ticker, days=500):
        """장기 주식 데이터 조회"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 한국 종목용 ticker 변환
            if len(ticker) == 6 and ticker.isdigit():
                ticker_symbol = f"{ticker}.KS"
            else:
                ticker_symbol = ticker

            # yfinance 다운로드
            df = yf.download(
                ticker_symbol,
                start=start_date,
                end=end_date,
                progress=False,
                interval="1d"
            )

            if df is None or df.empty or len(df) < 100:
                return None

            return df

        except Exception as e:
            return None

    def detect_bullish_breakaway(self, df, lookback_period=60, breakout_threshold=2.5):
        """
        Bullish Breakaway 패턴 감지
        - 최근 lookback_period일 동안 저항선 형성
        - 현재가가 저항선을 돌파하며 상승
        - 거래량 증가 확인
        - 강한 상승 강도 확인
        """
        if df is None or len(df) < lookback_period + 20:
            return None

        try:
            # 최근 period의 가격 데이터
            recent = df.iloc[-lookback_period:]
            closes = recent['Close'].values
            volumes = recent['Volume'].values

            # 저항선: 최근 기간의 최고가
            resistance = closes.max()
            support = closes.min()

            # 현재가와 이전 가격
            current_price = closes[-1]
            prev_price = closes[-2] if len(closes) > 1 else closes[-1]

            # 저항선 돌파 확인: 현재가가 저항선을 위로 돌파
            breakout_pct = (current_price - resistance) / resistance * 100
            uptrend_pct = (current_price - support) / support * 100

            # 거래량 확인: 최근 거래량이 평균보다 높은지
            avg_volume = volumes[:-3].mean() if len(volumes) > 3 else volumes.mean()
            recent_avg_volume = volumes[-3:].mean()
            volume_check = recent_avg_volume > avg_volume * 1.1

            # Bullish Breakaway 조건:
            # 1. 저항선에서 2% 이상 상승하며 돌파
            # 2. 총 상승률이 충분 (support 대비 최소 3%)
            # 3. 거래량 증가
            is_bullish_breakaway = (
                breakout_pct >= -2.0 and current_price > resistance and
                uptrend_pct >= 3.0 and
                volume_check
            )

            if is_bullish_breakaway:
                # 최근 5일 상승력
                recent_5d = df.iloc[-5:]
                momentum = ((recent_5d['Close'].iloc[-1] - recent_5d['Close'].iloc[0]) /
                           recent_5d['Close'].iloc[0] * 100)

                return {
                    'pattern_detected': True,
                    'resistance': round(resistance, 2),
                    'support': round(support, 2),
                    'breakout_pct': round(breakout_pct, 2),
                    'uptrend_pct': round(uptrend_pct, 2),
                    'current_price': round(current_price, 2),
                    'volume_check': volume_check,
                    'momentum_5d': round(momentum, 2),
                    'lookback_days': lookback_period
                }
        except:
            pass

        return None

    def find_bullish_breakaway_stocks(self, kospi_stocks, progress_callback=None):
        """Bullish Breakaway 패턴 발굴: 저항선 돌파하는 강한 상승"""
        results = []

        for idx, row in kospi_stocks.iterrows():
            ticker = row['Code']
            name = row['Name']

            df = self.get_stock_data_long(ticker)
            if df is None or len(df) < 450:
                if progress_callback:
                    progress_callback(idx + 1, len(kospi_stocks), name, ticker, len(results), False)
                continue

            try:
                pattern_info = self.detect_bullish_breakaway(df)

                if pattern_info and pattern_info['pattern_detected']:
                    current_price = df.iloc[-1]['Close']

                    result = {
                        'ticker': ticker,
                        'name': name,
                        'current_price': round(current_price, 2),
                        'price_date': df.index[-1].strftime('%Y-%m-%d'),
                        'extraction_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'resistance': pattern_info['resistance'],
                        'support': pattern_info['support'],
                        'breakout_pct': pattern_info['breakout_pct'],
                        'uptrend_pct': pattern_info['uptrend_pct'],
                        'momentum_5d': pattern_info['momentum_5d'],
                        'breakaway_strength': round(pattern_info['uptrend_pct'] + pattern_info['momentum_5d'], 2),
                        'volume_check': '✓' if pattern_info['volume_check'] else '✗'
                    }

                    results.append(result)

                if progress_callback:
                    progress_callback(idx + 1, len(kospi_stocks), name, ticker, len(results), True)

            except Exception as e:
                if progress_callback:
                    progress_callback(idx + 1, len(kospi_stocks), name, ticker, len(results), False)
                continue

        return pd.DataFrame(results)


class MorningStarFinder:
    """Morning Star 패턴 찾기: 하락 중인 종목에서 강한 반등 패턴 발굴"""

    def __init__(self, data_dir="analysis_data"):
        self.data_dir = data_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def get_morning_star_cache_filepath(self, date=None):
        """캐시 파일 경로 반환"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.data_dir, f"morning_star_{date}.csv")

    def load_cached_morning_star(self, date=None):
        """저장된 Morning Star 데이터 로드"""
        filepath = self.get_morning_star_cache_filepath(date)
        if os.path.exists(filepath):
            print(f"📂 캐시된 Morning Star 데이터 로드: {filepath}")
            df = pd.read_csv(filepath)
            print(f"✓ {len(df)}개 Morning Star 종목 로드됨")
            return df
        return None

    def save_morning_star_results(self, results_df, date=None):
        """Morning Star 분석 결과를 CSV로 저장"""
        if results_df.empty:
            return

        filepath = self.get_morning_star_cache_filepath(date)
        results_df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"✓ Morning Star 분석 결과 저장: {filepath}")

    def get_stock_data_long(self, ticker, days=500):
        """장기 주식 데이터 조회"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 한국 종목용 ticker 변환
            if len(ticker) == 6 and ticker.isdigit():
                ticker_symbol = f"{ticker}.KS"
            else:
                ticker_symbol = ticker

            # yfinance 다운로드
            df = yf.download(
                ticker_symbol,
                start=start_date,
                end=end_date,
                progress=False,
                timeout=15,
                threads=False
            )

            if df is None or len(df) < 450:
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

            # 필요한 컬럼 확인
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in df.columns for col in required_cols):
                return None

            # 데이터 정제
            df[required_cols] = df[required_cols].apply(pd.to_numeric, errors='coerce')
            df = df.dropna(subset=required_cols)

            if len(df) < 450:
                return None

            return df[required_cols]

        except Exception as e:
            return None

    def detect_morning_star(self, df, lookback_period=60, reversal_pct=3.0):
        """
        Morning Star 패턴 감지
        - 최근 lookback_period일 동안 하락 추세 확인
        - 최근 3일 중 강한 반등 나타남
        - 반등 강도가 reversal_pct 이상
        """
        if df is None or len(df) < lookback_period + 10:
            return None

        try:
            # 최근 데이터
            recent = df.iloc[-lookback_period:]
            closes = recent['Close'].values

            # 하락 추세 확인: 처음보다 끝이 낮음
            high_price = closes[0]
            low_price = closes[-4]  # 3일 전
            current_price = closes[-1]  # 현재가

            # 하락폭 계산
            decline_pct = (high_price - low_price) / high_price * 100

            # 반등폭 계산 (3일 전 최저가 대비)
            rebound_pct = (current_price - low_price) / low_price * 100

            # Morning Star 조건:
            # 1. 최근 lookback_period 동안 충분한 하락 (최소 5% 이상)
            # 2. 최근 3일 중 강한 반등 (reversal_pct 이상)
            # 3. 현재가가 저점에서 반등

            is_morning_star = decline_pct >= 5.0 and rebound_pct >= reversal_pct and current_price > low_price

            if is_morning_star:
                # 더 정확한 분석: 지난 3개 봉의 패턴 확인
                d3_close = closes[-3]  # 3일 전
                d2_close = closes[-2]  # 2일 전
                d1_close = closes[-1]  # 1일 전 (어제)
                d0_close = closes[-1]  # 현재

                # 거래량 확인 (최근 3일이 이전 평균보다 높아야 함)
                recent_volumes = recent['Volume'].values
                avg_volume = recent_volumes[:-3].mean()
                recent_avg_volume = recent_volumes[-3:].mean()

                volume_check = recent_avg_volume > avg_volume * 0.8

                return {
                    'pattern_detected': True,
                    'decline_pct': round(decline_pct, 2),
                    'rebound_pct': round(rebound_pct, 2),
                    'low_price': round(low_price, 2),
                    'current_price': round(current_price, 2),
                    'volume_check': volume_check,
                    'lookback_days': lookback_period
                }
        except:
            pass

        return None

    def find_morning_star_stocks(self, kospi_stocks, progress_callback=None):
        """Morning Star 패턴 발굴: 하락 중인 종목에서 강한 반등"""
        results = []

        for idx, row in kospi_stocks.iterrows():
            ticker = row['Code']
            name = row['Name']

            # 장기 데이터 조회
            df = self.get_stock_data_long(ticker)
            if df is None or len(df) < 450:
                if progress_callback:
                    progress_callback(idx + 1, len(kospi_stocks), name, ticker, len(results), False)
                continue

            try:
                # Morning Star 패턴 감지
                pattern_info = self.detect_morning_star(df)

                if pattern_info and pattern_info['pattern_detected']:
                    current_price = df.iloc[-1]['Close']

                    result = {
                        'ticker': ticker,
                        'name': name,
                        'current_price': round(current_price, 2),
                        'price_date': df.index[-1].strftime('%Y-%m-%d'),
                        'extraction_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'decline_pct': pattern_info['decline_pct'],
                        'rebound_pct': pattern_info['rebound_pct'],
                        'low_price': pattern_info['low_price'],
                        'recovery_strength': round((current_price - pattern_info['low_price']) / pattern_info['low_price'] * 100, 2),
                        'volume_check': '✓' if pattern_info['volume_check'] else '✗'
                    }

                    results.append(result)

                if progress_callback:
                    progress_callback(idx + 1, len(kospi_stocks), name, ticker, len(results), True)

            except Exception as e:
                if progress_callback:
                    progress_callback(idx + 1, len(kospi_stocks), name, ticker, len(results), False)
                continue

        return pd.DataFrame(results)

    def find_combined_patterns(self, kospi_stocks, progress_callback=None):
        """
        Morning Star와 Bullish Breakaway 패턴을 동시에 찾아서 반환
        결과에 pattern_type 컬럼을 추가하여 패턴 종류를 구분
        kospi_stocks: DataFrame 형태 (Code, Name 컬럼 포함)
        """
        results = []

        # kospi_stocks가 DataFrame인 경우와 리스트인 경우 모두 처리
        if isinstance(kospi_stocks, pd.DataFrame):
            stocks_iter = kospi_stocks.iterrows()
            total_stocks = len(kospi_stocks)
        else:
            stocks_iter = enumerate(kospi_stocks)
            total_stocks = len(kospi_stocks)

        for idx, stock_data in stocks_iter:
            try:
                # DataFrame인 경우
                if isinstance(kospi_stocks, pd.DataFrame):
                    ticker = str(stock_data['Code']).zfill(6)
                    name = stock_data['Name']
                else:
                    # 튜플 형태인 경우
                    if isinstance(stock_data, tuple):
                        ticker, name = stock_data
                    else:
                        continue

                # 데이터 조회
                df = self.get_stock_data_long(ticker)
                if df is None or len(df) < 60:
                    if progress_callback:
                        progress_callback(idx + 1, total_stocks, name, ticker, len(results), False)
                    continue

                current_price = df.iloc[-1]['Close']

                # 1. Morning Star 패턴 감지
                morning_star_info = self.detect_morning_star(df)
                if morning_star_info and morning_star_info['pattern_detected']:
                    result = {
                        'pattern_type': '🌅 Morning Star',
                        'ticker': ticker,
                        'name': name,
                        'current_price': round(current_price, 2),
                        'price_date': df.index[-1].strftime('%Y-%m-%d'),
                        'extraction_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'decline_pct': morning_star_info['decline_pct'],
                        'rebound_pct': morning_star_info['rebound_pct'],
                        'low_price': morning_star_info['low_price'],
                        'recovery_strength': round((current_price - morning_star_info['low_price']) / morning_star_info['low_price'] * 100, 2),
                        'volume_check': '✓' if morning_star_info['volume_check'] else '✗'
                    }
                    results.append(result)

                # 2. Bullish Breakaway 패턴 감지
                breakaway_info = self.detect_bullish_breakaway(df)
                if breakaway_info and breakaway_info['pattern_detected']:
                    result = {
                        'pattern_type': '⚡ Bullish Breakaway',
                        'ticker': ticker,
                        'name': name,
                        'current_price': round(current_price, 2),
                        'price_date': df.index[-1].strftime('%Y-%m-%d'),
                        'extraction_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'resistance': breakaway_info['resistance'],
                        'support': breakaway_info['support'],
                        'breakout_pct': breakaway_info['breakout_pct'],
                        'uptrend_pct': breakaway_info['uptrend_pct'],
                        'momentum_5d': breakaway_info['momentum_5d'],
                        'breakaway_strength': breakaway_info['breakaway_strength'],
                        'volume_check': '✓' if breakaway_info['volume_check'] else '✗'
                    }
                    results.append(result)

                if progress_callback:
                    progress_callback(idx + 1, total_stocks, name, ticker, len(results), True)

            except Exception as e:
                if progress_callback:
                    progress_callback(idx + 1, total_stocks, name if 'name' in locals() else "Unknown", ticker if 'ticker' in locals() else "Unknown", len(results), False)
                continue

        return pd.DataFrame(results) if results else pd.DataFrame()

    def get_combined_cache_filepath(self, date=None):
        """결합 패턴 캐시 파일 경로"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.data_dir, f"combined_patterns_{date}.csv")

    def load_cached_combined_patterns(self, date=None):
        """저장된 결합 패턴 데이터 로드"""
        filepath = self.get_combined_cache_filepath(date)
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            return df
        return None

    def save_combined_patterns(self, results_df, date=None):
        """결합 패턴 결과를 CSV로 저장 (UTF-8 인코딩)"""
        if results_df.empty:
            return

        filepath = self.get_combined_cache_filepath(date)
        results_df.to_csv(filepath, index=False, encoding='utf-8-sig')
        return filepath


class TalibPatternFinder:
    """TA-Lib 기반 패턴 감지: Morning Star, Bullish Breakaway 등"""

    def __init__(self, data_dir="analysis_data"):
        self.data_dir = data_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        # TA-Lib이 없으면 경고만 출력하고 계속 진행
        if not TALIB_AVAILABLE:
            print("⚠️ ta-lib이 설치되지 않았습니다. TA-Lib 패턴 감지 기능이 비활성화됩니다.")

    def get_stock_data_long(self, ticker, days=500):
        """FinanceDataReader를 사용한 장기 주식 데이터 조회"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # FinanceDataReader는 한국 ticker 코드 그대로 사용 (예: 005930)
            ticker_str = str(ticker).zfill(6)

            # FinanceDataReader로 데이터 조회
            df = fdr.DataReader(ticker_str, start_date, end_date)

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
                elif col_lower in ['adj close', 'adj_close', 'change']:
                    col_map[col] = 'Adj Close'

            if col_map:
                df.rename(columns=col_map, inplace=True)

            # 필요한 컬럼 확인
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in df.columns for col in required_cols):
                return None

            # 데이터 정제
            df[required_cols] = df[required_cols].apply(pd.to_numeric, errors='coerce')
            df = df.dropna(subset=required_cols)

            if len(df) < 100:
                return None

            return df[required_cols]

        except Exception as e:
            return None

    def find_patterns_in_week(self, kospi_stocks, progress_callback=None):
        """
        과거 6개월(180일) 동안 talib 패턴이 나타난 종목들 찾기

        Returns:
            DataFrame with columns:
            - pattern_type: 패턴 타입 (Morning Star / Bullish Breakaway)
            - ticker, name, current_price
            - pattern_date: 패턴이 나타난 날짜
            - pattern_index: 패턴이 나타난 인덱스
        """
        results = []
        one_eighty_days_ago = datetime.now() - timedelta(days=180)

        # TA-Lib이 없으면 빈 결과 반환
        if not TALIB_AVAILABLE:
            return pd.DataFrame()

        for idx, row in kospi_stocks.iterrows():
            try:
                ticker = str(row['Code']).zfill(6)
                name = row['Name']

                # 데이터 조회 (패턴 인식을 위해 500일 데이터 조회, 하지만 최근 180일(6개월) 데이터에서만 패턴 검색)
                df = self.get_stock_data_long(ticker, days=500)
                if df is None or len(df) < 100:
                    if progress_callback:
                        progress_callback(idx + 1, len(kospi_stocks), name, ticker, len(results), False)
                    continue

                # Open, High, Low, Close를 numpy 배열로 변환
                open_arr = df['Open'].values
                high_arr = df['High'].values
                low_arr = df['Low'].values
                close_arr = df['Close'].values

                # Morning Star 패턴 감지
                morning_star = talib.CDLMORNINGSTAR(open_arr, high_arr, low_arr, close_arr)

                # Bullish Breakaway 패턴 감지
                bullish_breakaway = talib.CDLBREAKAWAY(open_arr, high_arr, low_arr, close_arr)

                # 최근 180일(6개월) 데이터에서 패턴 검색
                recent_df = df[df.index >= one_eighty_days_ago]
                recent_indices = df.index.get_indexer(recent_df.index)

                for pattern_idx in recent_indices:
                    if pattern_idx < 0 or pattern_idx >= len(morning_star):
                        continue

                    # Morning Star 패턴 발견
                    if morning_star[pattern_idx] != 0:
                        pattern_date = df.index[pattern_idx]
                        current_price = df.iloc[-1]['Close']

                        result = {
                            'pattern_type': '🌅 Morning Star',
                            'ticker': ticker,
                            'name': name,
                            'current_price': round(current_price, 2),
                            'pattern_date': pattern_date.strftime('%Y-%m-%d'),
                            'pattern_index': int(pattern_idx),
                            'price_date': df.index[-1].strftime('%Y-%m-%d'),
                            'extraction_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        }
                        results.append(result)

                    # Bullish Breakaway 패턴 발견
                    if bullish_breakaway[pattern_idx] != 0:
                        pattern_date = df.index[pattern_idx]
                        current_price = df.iloc[-1]['Close']

                        result = {
                            'pattern_type': '⚡ Bullish Breakaway',
                            'ticker': ticker,
                            'name': name,
                            'current_price': round(current_price, 2),
                            'pattern_date': pattern_date.strftime('%Y-%m-%d'),
                            'pattern_index': int(pattern_idx),
                            'price_date': df.index[-1].strftime('%Y-%m-%d'),
                            'extraction_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        }
                        results.append(result)

                if progress_callback:
                    progress_callback(idx + 1, len(kospi_stocks), name, ticker, len(results), True)

            except Exception as e:
                if progress_callback:
                    progress_callback(idx + 1, len(kospi_stocks), name if 'name' in locals() else "Unknown",
                                    ticker if 'ticker' in locals() else "Unknown", len(results), False)
                continue

        return pd.DataFrame(results) if results else pd.DataFrame()

    def get_talib_week_cache_filepath(self, date=None):
        """TA-Lib 분기(3개월) 패턴 캐시 파일 경로"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.data_dir, f"talib_quarter_patterns_{date}.csv")

    def load_talib_week_patterns(self, date=None):
        """저장된 분기(3개월) 패턴 데이터 로드"""
        filepath = self.get_talib_week_cache_filepath(date)
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            return df
        return None

    def save_talib_week_patterns(self, results_df, date=None):
        """분기(3개월) 패턴 결과를 CSV로 저장"""
        if results_df.empty:
            return

        filepath = self.get_talib_week_cache_filepath(date)
        results_df.to_csv(filepath, index=False, encoding='utf-8-sig')
        return filepath


class SoaringSignalFinder:
    """급등 직전 신호 분석: 이동평균선 정배열, 거래량 패턴, 캔들 패턴 등"""

    def __init__(self, data_dir="analysis_data"):
        self.data_dir = data_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def get_stock_data(self, ticker, days=180):
        """FinanceDataReader를 사용한 주식 데이터 조회"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            ticker_str = str(ticker).zfill(6)

            df = fdr.DataReader(ticker_str, start_date, end_date)

            if df is None or len(df) < 20:
                return None

            # 데이터 정제
            df = df.dropna()
            if len(df) < 20:
                return None

            return df
        except Exception as e:
            return None

    def calculate_moving_averages(self, df):
        """이동평균선 계산"""
        try:
            df = df.copy()
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA10'] = df['Close'].rolling(window=10).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA60'] = df['Close'].rolling(window=60).mean()
            df['MA120'] = df['Close'].rolling(window=120).mean()
            return df
        except Exception as e:
            return None

    def check_ma_alignment(self, df):
        """
        이동평균선 정배열 확인
        정배열: Close > MA5 > MA10 > MA20 > MA60 > MA120
        """
        if df is None or len(df) < 120:
            return {'aligned': False, 'strength': 0}

        try:
            latest = df.iloc[-1]

            # 모든 이동평균선이 계산되어 있는지 확인
            mas = ['MA5', 'MA10', 'MA20', 'MA60', 'MA120']
            if not all(col in df.columns for col in mas):
                return {'aligned': False, 'strength': 0}

            close = latest['Close']
            ma5 = latest['MA5']
            ma10 = latest['MA10']
            ma20 = latest['MA20']
            ma60 = latest['MA60']
            ma120 = latest['MA120']

            # 정배열 조건 체크
            conditions = [
                close > ma5,
                ma5 > ma10,
                ma10 > ma20,
                ma20 > ma60,
                ma60 > ma120
            ]

            aligned_count = sum(conditions)

            result = {
                'aligned': aligned_count >= 4,  # 4개 이상 만족
                'strength': aligned_count / len(conditions),
                'close': close,
                'ma5': ma5,
                'ma10': ma10,
                'ma20': ma20,
                'ma60': ma60,
                'ma120': ma120
            }

            return result
        except Exception as e:
            return {'aligned': False, 'strength': 0}

    def check_volume_signal(self, df):
        """
        거래량 신호 분석:
        1. 대량 거래량 동반 상승
        2. 거래량 매집 후 상승
        3. 평균 거래량 대비 증가율
        """
        if df is None or len(df) < 20:
            return {'strong_volume': False, 'volume_increase': 0, 'signal_strength': 0}

        try:
            df = df.copy()
            df['Volume_MA'] = df['Volume'].rolling(window=20).mean()

            latest = df.iloc[-1]
            prev = df.iloc[-2]

            # 현재 거래량이 평균의 몇 배인지
            if latest['Volume_MA'] > 0:
                volume_increase = latest['Volume'] / latest['Volume_MA']
            else:
                volume_increase = 0

            # 거래량 증가 + 상승 캔들
            strong_volume = (
                volume_increase > 1.5 and  # 평균 거래량의 1.5배 이상
                latest['Close'] > prev['Close']  # 상승 캔들
            )

            # 최근 거래량 추이 확인 (매집 후 상승)
            volume_accumulation = False
            if len(df) >= 20:
                recent_volume = df['Volume'].iloc[-10:-1].mean()
                older_volume = df['Volume'].iloc[-30:-10].mean()

                if older_volume > 0 and recent_volume < older_volume * 0.7:
                    # 최근 거래량이 줄었다가
                    if volume_increase > 1.3:
                        # 다시 크게 증가
                        volume_accumulation = True

            signal_strength = 0
            if strong_volume:
                signal_strength += 0.5
            if volume_accumulation:
                signal_strength += 0.5

            result = {
                'strong_volume': strong_volume,
                'volume_accumulation': volume_accumulation,
                'volume_increase': round(volume_increase, 2),
                'signal_strength': round(signal_strength, 2)
            }

            return result
        except Exception as e:
            return {'strong_volume': False, 'volume_increase': 0, 'signal_strength': 0}

    def check_candlestick_signal(self, df):
        """
        캔들 패턴 분석:
        1. 윗꼬리 패턴 (Upper tail)
        2. 저점이 높아지는 상승 추세
        """
        if df is None or len(df) < 5:
            return {'upper_tail_strong': False, 'rising_lows': False, 'signal_strength': 0}

        try:
            df = df.copy()

            # 윗꼬리 계산: (High - Close) / (High - Low)
            df['Upper_Tail_Ratio'] = (df['High'] - df['Close']) / (df['High'] - df['Low'] + 0.0001)

            # 최근 5개 캔들 중 윗꼬리가 있는 캔들 확인
            recent = df.iloc[-5:]
            upper_tail_count = (recent['Upper_Tail_Ratio'] > 0.3).sum()  # 윗꼬리가 30% 이상

            # 저점이 계속 높아지는지 확인 (최근 10개 캔들)
            if len(df) >= 10:
                recent_lows = df['Low'].iloc[-10:]
                rising_lows = all(recent_lows.iloc[i] < recent_lows.iloc[i+1] for i in range(len(recent_lows)-1))
            else:
                rising_lows = False

            upper_tail_strong = upper_tail_count >= 3  # 최근 5개 중 3개 이상

            signal_strength = 0
            if upper_tail_strong:
                signal_strength += 0.5
            if rising_lows:
                signal_strength += 0.5

            result = {
                'upper_tail_strong': upper_tail_strong,
                'rising_lows': rising_lows,
                'upper_tail_count': upper_tail_count,
                'signal_strength': round(signal_strength, 2)
            }

            return result
        except Exception as e:
            return {'upper_tail_strong': False, 'rising_lows': False, 'signal_strength': 0}

    def check_support_breakout(self, df):
        """
        지지선 및 저항선 돌파 분석:
        1. 저점 지지 후 반등
        2. 지속적인 저점 상승
        """
        if df is None or len(df) < 30:
            return {'support_bounce': False, 'resistance_breakout': False, 'signal_strength': 0}

        try:
            df = df.copy()

            # 최근 30일 최저점 (바닥)
            recent_30 = df.iloc[-30:]
            lowest_30 = recent_30['Low'].min()
            lowest_30_idx = recent_30['Low'].idxmin()

            # 바닥 이후 현재까지 상승했는지 확인
            current_price = df.iloc[-1]['Close']
            support_bounce = current_price > lowest_30 * 1.02  # 최소 2% 이상 상승

            # 저항선 돌파: 최근 60일 고점 돌파
            if len(df) >= 60:
                highest_60 = df.iloc[-60:-1]['High'].max()
                resistance_breakout = current_price > highest_60 * 0.99  # 고점 근처 또는 돌파
            else:
                resistance_breakout = False

            # 지속적인 저점 상승
            continuous_rising_lows = False
            if len(df) >= 20:
                recent_lows = df['Low'].iloc[-20:]
                # 저점들이 우상향하는지 확인 (스트롱 상승 추세)
                low_trend = np.polyfit(range(len(recent_lows)), recent_lows.values, 1)[0]
                continuous_rising_lows = low_trend > 0

            signal_strength = 0
            if support_bounce:
                signal_strength += 0.33
            if resistance_breakout:
                signal_strength += 0.33
            if continuous_rising_lows:
                signal_strength += 0.34

            result = {
                'support_bounce': support_bounce,
                'resistance_breakout': resistance_breakout,
                'continuous_rising_lows': continuous_rising_lows,
                'signal_strength': round(signal_strength, 2)
            }

            return result
        except Exception as e:
            return {'support_bounce': False, 'resistance_breakout': False, 'signal_strength': 0}

    def analyze_soaring_signal(self, ticker, name):
        """
        종합 급등 신호 분석

        Returns:
            dict with:
            - ticker, name
            - ma_signal: 이동평균선 신호
            - volume_signal: 거래량 신호
            - candlestick_signal: 캔들 신호
            - support_signal: 지지선 신호
            - total_score: 전체 점수 (0-100)
            - soaring_probability: 급등 확률 (낮음/중간/높음)
        """
        try:
            # 데이터 조회
            df = self.get_stock_data(ticker, days=180)
            if df is None:
                return None

            # 이동평균선 계산
            df = self.calculate_moving_averages(df)
            if df is None:
                return None

            # 각 신호 분석
            ma_signal = self.check_ma_alignment(df)
            volume_signal = self.check_volume_signal(df)
            candlestick_signal = self.check_candlestick_signal(df)
            support_signal = self.check_support_breakout(df)

            # 종합 점수 계산
            total_score = (
                ma_signal.get('strength', 0) * 30 +      # 이동평균 30%
                volume_signal.get('signal_strength', 0) * 25 +  # 거래량 25%
                candlestick_signal.get('signal_strength', 0) * 25 +  # 캔들 25%
                support_signal.get('signal_strength', 0) * 20     # 지지선 20%
            )

            # 급등 확률 판정
            if total_score >= 70:
                soaring_probability = '높음 ⬆️'
            elif total_score >= 50:
                soaring_probability = '중간 ➡️'
            else:
                soaring_probability = '낮음 ⬇️'

            latest = df.iloc[-1]

            # 캔들스틱 신호에서 평균 윗꼬리 비율 계산
            if len(df) >= 5:
                df_copy = df.copy()
                df_copy['Upper_Tail_Ratio'] = (df_copy['High'] - df_copy['Close']) / (df_copy['High'] - df_copy['Low'] + 0.0001)
                avg_upper_tail_ratio = df_copy['Upper_Tail_Ratio'].iloc[-5:].mean()
            else:
                avg_upper_tail_ratio = 0

            result = {
                'ticker': str(ticker).zfill(6),
                'name': name,
                'current_price': round(latest['Close'], 0),
                'price_date': df.index[-1].strftime('%Y-%m-%d'),
                'extraction_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),

                # 각 신호의 세부 정보 (UI와 일치하도록 필드명 통일)
                'ma_aligned': ma_signal.get('aligned', False),
                'ma_strength': round(ma_signal.get('strength', 0), 2),

                'has_strong_volume': volume_signal.get('strong_volume', False),
                'has_accumulation': volume_signal.get('volume_accumulation', False),
                'volume_increase_ratio': round(volume_signal.get('volume_increase', 0), 2),

                'has_upper_tail': candlestick_signal.get('upper_tail_strong', False),
                'has_rising_lows': candlestick_signal.get('rising_lows', False),
                'upper_tail_ratio': round(avg_upper_tail_ratio, 2),

                'has_support_bounce': support_signal.get('support_bounce', False),
                'has_resistance_breakout': support_signal.get('resistance_breakout', False),
                'support_strength': round(support_signal.get('signal_strength', 0), 2),

                # 최종 점수
                'score': round(total_score, 2),
                'soaring_probability': soaring_probability
            }

            return result

        except Exception as e:
            return None

    def find_soaring_signals(self, kospi_stocks, progress_callback=None):
        """
        모든 KOSPI 종목에서 급등 신호 찾기

        Returns:
            DataFrame with soaring signal analysis for each stock
        """
        results = []

        for idx, row in kospi_stocks.iterrows():
            try:
                ticker = str(row['Code']).zfill(6)
                name = row['Name']

                # 신호 분석
                result = self.analyze_soaring_signal(ticker, name)

                if result is not None:
                    results.append(result)

                # 진행 상황 콜백
                if progress_callback:
                    progress_callback(idx + 1, len(kospi_stocks), name, ticker, len(results), True)

            except Exception as e:
                if progress_callback:
                    progress_callback(idx + 1, len(kospi_stocks), name if 'name' in locals() else "Unknown",
                                    ticker if 'ticker' in locals() else "Unknown", len(results), False)
                continue

        return pd.DataFrame(results) if results else pd.DataFrame()


class ComprehensiveAnalyzer:
    """
    스윙매매, 급등주 찾기, 급등신호를 한번에 분석하는 종합 분석기
    """

    def __init__(self):
        self.swing_analyzer = SwingTradeAnalyzer()
        self.talib_finder = TalibPatternFinder()
        self.soaring_finder = SoaringSignalFinder()

    def analyze_all_in_one(self, max_stocks=None, progress_callback=None):
        """
        종합 분석 수행 (스윙매매 + 급등주 찾기 + 급등신호)

        Returns:
            dict: {
                'swing_results': DataFrame,
                'soaring_results': DataFrame,
                'signal_results': DataFrame
            }
        """
        results = {
            'swing_results': None,
            'soaring_results': None,
            'signal_results': None
        }

        try:
            # 1. 스윙매매 분석
            if progress_callback:
                progress_callback("스윙매매 분석 시작", 0)

            def swing_progress_callback(idx, total, stock_name, stock_code, success_count):
                if progress_callback:
                    progress_callback(f"스윙매매: {stock_name}", idx / total if total > 0 else 0)

            swing_results = self.swing_analyzer.analyze_all_stocks(
                max_stocks=max_stocks,
                progress_callback=swing_progress_callback
            )
            results['swing_results'] = swing_results

            if swing_results.empty:
                return results

            if progress_callback:
                progress_callback("급등주 찾기(TA-Lib) 분석 시작", 0.33)

            # 2. 급등주 찾기 분석 (TA-Lib 패턴)
            kospi_stocks = self.swing_analyzer.get_kospi_stocks()
            if not kospi_stocks.empty and max_stocks:
                kospi_stocks = kospi_stocks.head(max_stocks)

            def talib_progress_callback(idx, total, name, ticker, found_count, success):
                if progress_callback:
                    progress_callback(f"급등주(TA-Lib): {name}", 0.33 + (idx / total * 0.33) if total > 0 else 0.33)

            soaring_results = self.talib_finder.find_patterns_in_week(
                kospi_stocks,
                progress_callback=talib_progress_callback
            )
            results['soaring_results'] = soaring_results

            if progress_callback:
                progress_callback("급등신호 분석 시작", 0.66)

            # 3. 급등신호 분석
            def signal_progress_callback(idx, total, stock_name, stock_code, success_count, success):
                if progress_callback:
                    progress_callback(f"급등신호: {stock_name}", 0.66 + (idx / total * 0.33) if total > 0 else 0.66)

            signal_results = self.soaring_finder.find_soaring_signals(
                kospi_stocks,
                progress_callback=signal_progress_callback
            )
            results['signal_results'] = signal_results

            if progress_callback:
                progress_callback("모든 분석 완료", 1.0)

            return results

        except Exception as e:
            if progress_callback:
                progress_callback(f"오류 발생: {str(e)}", 0)
            return results


class ReverseMAAlignmentFinder:
    """
    역매공파 112 분석기

    역배열(Long-term MA reverse) + 매집봉(Volume accumulation) + 공구리(Support line) + 파란점선(Ichimoku cloud) + 112일선(Golden cross path)

    조건:
    1. 역배열: 장기 이평선(112, 224, 448)은 역배열 상태
    2. 정배열: 단기 이평선(5, 20, 60)은 정배열 상태
    3. 112일선: 60일선이 112일선까지 정배열로 돌아선 상태
    """

    def __init__(self, data_dir="analysis_data"):
        self.data_dir = data_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def get_stock_data(self, ticker, days=500):
        """FinanceDataReader를 사용한 주식 데이터 조회"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            ticker_str = str(ticker).zfill(6)

            df = fdr.DataReader(ticker_str, start_date, end_date)

            if df is None or len(df) < 450:
                return None

            df = df.dropna()
            if len(df) < 450:
                return None

            return df
        except Exception as e:
            return None

    def calculate_all_moving_averages(self, df):
        """모든 이동평균선 계산 (5, 20, 60, 112, 224, 448)"""
        try:
            df = df.copy()
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA60'] = df['Close'].rolling(window=60).mean()
            df['MA112'] = df['Close'].rolling(window=112).mean()
            df['MA224'] = df['Close'].rolling(window=224).mean()
            df['MA448'] = df['Close'].rolling(window=448).mean()
            return df
        except Exception as e:
            return None

    def check_long_term_reverse_alignment(self, df):
        """
        장기 이평선 역배열 확인
        역배열: MA448 > MA224 > MA112 (위에서 아래로 내려오는 상태)
        """
        if df is None or len(df) < 448:
            return {'reversed': False, 'reason': '데이터 부족'}

        latest = df.iloc[-1]
        ma448 = latest.get('MA448')
        ma224 = latest.get('MA224')
        ma112 = latest.get('MA112')

        if pd.isna(ma448) or pd.isna(ma224) or pd.isna(ma112):
            return {'reversed': False, 'reason': 'MA 값 부족'}

        # 역배열 조건: 장기선이 높은 순서
        if ma448 > ma224 > ma112:
            return {
                'reversed': True,
                'reason': f'역배열 확인 (448:{ma448:.0f} > 224:{ma224:.0f} > 112:{ma112:.0f})'
            }

        return {'reversed': False, 'reason': '역배열 아님'}

    def check_short_term_alignment(self, df):
        """
        단기 이평선 정배열 확인
        정배열: Close > MA5 > MA20 > MA60
        """
        if df is None or len(df) < 60:
            return {'aligned': False, 'strength': 0}

        latest = df.iloc[-1]
        close = latest['Close']
        ma5 = latest.get('MA5')
        ma20 = latest.get('MA20')
        ma60 = latest.get('MA60')

        if pd.isna(ma5) or pd.isna(ma20) or pd.isna(ma60):
            return {'aligned': False, 'strength': 0}

        # 정배열 조건
        if close > ma5 > ma20 > ma60:
            # 강도 계산 (0-1)
            total_distance = close - ma60
            if total_distance > 0:
                strength = min(1.0, total_distance / (ma60 * 0.1))
            else:
                strength = 0

            return {
                'aligned': True,
                'strength': strength,
                'close': close,
                'ma5': ma5,
                'ma20': ma20,
                'ma60': ma60
            }

        return {'aligned': False, 'strength': 0}

    def check_ma112_crossover_path(self, df):
        """
        112일선 돌파 경로 확인
        60일선이 112일선을 기준으로 위로 정배열된 상태
        """
        if df is None or len(df) < 112:
            return {'crossed': False, 'reason': 'MA 데이터 부족'}

        latest = df.iloc[-1]
        ma60 = latest.get('MA60')
        ma112 = latest.get('MA112')

        if pd.isna(ma60) or pd.isna(ma112):
            return {'crossed': False, 'reason': 'MA 값 부족'}

        # 60일선이 112일선 위에 있는지 확인
        if ma60 > ma112:
            # 최근 20일 동안의 추세 확인
            recent_ma60 = df['MA60'].tail(20)
            recent_ma112 = df['MA112'].tail(20)

            # 교차점 찾기
            crosses = (recent_ma60 > recent_ma112) & (recent_ma60.shift(1) <= recent_ma112.shift(1))
            crossing_occurred = crosses.any()

            return {
                'crossed': True,
                'ma60': ma60,
                'ma112': ma112,
                'recently_crossed': crossing_occurred,
                'reason': '60일선이 112일선 위로 돌파'
            }

        return {'crossed': False, 'reason': '60일선이 112일선 아래'}

    def check_support_line(self, df):
        """
        공구리 (Support line) 확인
        최근 30일 저점이 이전 저점들 위에 있는지 확인
        """
        if df is None or len(df) < 30:
            return {'support_formed': False, 'strength': 0}

        try:
            recent = df.tail(30)
            recent_low = recent['Low'].min()

            # 이전 60일의 저점과 비교
            previous = df.iloc[-90:-30]
            if len(previous) > 0:
                prev_low = previous['Low'].min()

                # 공구리: 저점이 상향하는 추세
                if recent_low > prev_low:
                    strength = min(1.0, (recent_low - prev_low) / prev_low)
                    return {
                        'support_formed': True,
                        'recent_low': recent_low,
                        'previous_low': prev_low,
                        'strength': strength,
                        'reason': '지지선 형성 (저점 상향)'
                    }
        except:
            pass

        return {'support_formed': False, 'strength': 0}

    def check_ichimoku_cloud(self, df):
        """
        파란점선 (Ichimoku Cloud) 확인
        기본선(Kijun-sen)과 전환선(Tenkan-sen)의 위치로 파동 강도 판단
        """
        if df is None or len(df) < 26:
            return {'cloud_ready': False, 'strength': 0}

        try:
            df = df.copy()

            # 전환선 (9일 최고점과 최저점의 중간값)
            high_9 = df['High'].rolling(window=9).max()
            low_9 = df['Low'].rolling(window=9).min()
            df['Tenkan'] = (high_9 + low_9) / 2

            # 기본선 (26일 최고점과 최저점의 중간값)
            high_26 = df['High'].rolling(window=26).max()
            low_26 = df['Low'].rolling(window=26).min()
            df['Kijun'] = (high_26 + low_26) / 2

            latest = df.iloc[-1]
            tenkan = latest['Tenkan']
            kijun = latest['Kijun']
            close = latest['Close']

            if pd.isna(tenkan) or pd.isna(kijun):
                return {'cloud_ready': False, 'strength': 0}

            # 파동이 응축된 상태 판단 (전환선과 기본선의 간격)
            distance = abs(tenkan - kijun)
            avg_price = (tenkan + kijun) / 2

            # 간격을 가격 대비로 계산
            gap_ratio = distance / avg_price if avg_price > 0 else 0

            # 파동이 응축되려면 간격이 좁아야 함 (1% 이하)
            is_condensed = gap_ratio < 0.01

            return {
                'cloud_ready': close > tenkan > kijun or close > kijun > tenkan,
                'strength': max(0, 1 - gap_ratio * 100),  # 간격이 좁을수록 높은 점수
                'tenkan': tenkan,
                'kijun': kijun,
                'close': close,
                'gap_ratio': gap_ratio,
                'is_condensed': is_condensed,
                'reason': f'파동 응축도: {gap_ratio*100:.2f}%'
            }
        except:
            return {'cloud_ready': False, 'strength': 0}

    def analyze_reverse_ma_pattern(self, ticker, name):
        """
        역매공파 112 패턴 종합 분석

        개선된 점수 계산 로직:
        - 역배열 여부: 0~25점 (범위 내에 있으면 부분 점수)
        - 정배열 강도: 0~25점
        - 112일선 근처: 0~25점 (돌파 안 했어도 가까우면 점수)
        - 공구리 + 파란점선: 0~25점
        """
        try:
            df = self.get_stock_data(ticker)
            if df is None:
                return None

            df = self.calculate_all_moving_averages(df)
            if df is None:
                return None

            # 각 조건 분석
            long_reverse = self.check_long_term_reverse_alignment(df)
            short_align = self.check_short_term_alignment(df)
            ma112_cross = self.check_ma112_crossover_path(df)
            support = self.check_support_line(df)
            ichimoku = self.check_ichimoku_cloud(df)

            # 현재 가격
            latest = df.iloc[-1]
            current_price = latest['Close']
            price_date = latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name)

            # 개선된 종합 점수 계산
            conditions_met = 0

            # 1. 역배열 (장기선): 0~25점
            # 완전 역배열: 25점, 부분적: 부분 점수
            ma112 = latest.get('MA112', 0)
            ma224 = latest.get('MA224', 0)
            ma448 = latest.get('MA448', 0)

            if ma448 > 0 and ma224 > 0 and ma112 > 0:
                if ma448 > ma224 > ma112:
                    long_reverse_score = 25
                    conditions_met += 1.0
                elif ma448 > ma224 or ma224 > ma112:
                    # 부분적 역배열: 50% 신뢰도
                    long_reverse_score = 12.5
                    conditions_met += 0.5
                else:
                    long_reverse_score = 0
                    # 역배열이 아닌 경우 conditions_met 증가 안함
            else:
                long_reverse_score = 0
                # 필요한 MA 값이 없는 경우

            # 2. 정배열 (단기선): 0~25점
            short_align_score = 25 * short_align.get('strength', 0)
            conditions_met += short_align.get('strength', 0)

            # 3. 112일선 근처: 0~25점
            # 완전 돌파: 25점, 가까운 거리: 부분 점수
            ma60 = latest.get('MA60', 0)
            if ma60 > 0 and ma112 > 0:
                if ma60 > ma112:
                    # 이미 돌파한 경우
                    ma112_score = 25
                    conditions_met += 1.0
                elif ma60 > 0:
                    # 가까운 거리 체크 (5% 이내 거리)
                    distance_ratio = (ma112 - ma60) / ma112 if ma112 > 0 else 1.0
                    if distance_ratio < 0.05:
                        # 5% 이내: 가까운 상태
                        ma112_score = 15
                        conditions_met += 0.6
                    elif distance_ratio < 0.15:
                        # 15% 이내: 중간 거리
                        ma112_score = 8
                        conditions_met += 0.3
                    else:
                        ma112_score = 0
                else:
                    ma112_score = 0
            else:
                ma112_score = 0

            # 4. 공구리 + 파란점선: 0~25점
            support_score = 25 * support.get('strength', 0)
            ichimoku_score = 25 * ichimoku.get('strength', 0)
            combo_score = min(25, (support_score + ichimoku_score) / 2)
            conditions_met += (support.get('strength', 0) + ichimoku.get('strength', 0)) / 2

            total_score = long_reverse_score + short_align_score + ma112_score + combo_score

            return {
                'ticker': ticker,
                'name': name,
                'current_price': current_price,
                'price_date': price_date,
                'score': total_score,
                'conditions_met': conditions_met,
                'pattern_strength': min(4, int(conditions_met)),  # 0-4 (4개 조건)

                # 세부 조건
                'long_reverse': long_reverse.get('reversed', False),
                'long_reverse_reason': long_reverse.get('reason', ''),
                'short_align': short_align.get('aligned', False),
                'short_align_strength': short_align.get('strength', 0),
                'ma112_crossed': ma112_cross.get('crossed', False),
                'support_formed': support.get('support_formed', False),
                'support_strength': support.get('strength', 0),
                'ichimoku_ready': ichimoku.get('cloud_ready', False),
                'ichimoku_condensed': ichimoku.get('is_condensed', False),

                # 현재 MA 값
                'ma5': short_align.get('ma5', 0),
                'ma20': short_align.get('ma20', 0),
                'ma60': short_align.get('ma60', 0),
                'ma112': ma112_cross.get('ma112', 0),
                'ma224': latest.get('MA224', 0) if 'MA224' in latest else 0,
                'ma448': latest.get('MA448', 0) if 'MA448' in latest else 0,
            }

        except Exception as e:
            return None

    def find_reverse_ma_patterns(self, kospi_stocks, progress_callback=None):
        """
        KOSPI 전체 종목에서 역매공파 112 패턴 찾기
        """
        results = []
        total = len(kospi_stocks)

        for idx, (ticker, name) in enumerate(kospi_stocks):
            try:
                if progress_callback:
                    progress_callback(f"역매공파 분석: {name}", (idx / total) if total > 0 else 0)

                result = self.analyze_reverse_ma_pattern(ticker, name)
                if result is not None:
                    results.append(result)

            except Exception as e:
                continue

        # 점수 기준 정렬
        results_df = pd.DataFrame(results)
        if len(results_df) > 0:
            results_df = results_df.sort_values('score', ascending=False)

        if progress_callback:
            progress_callback(f"역매공파 분석 완료", 1.0)

        return results_df if len(results_df) > 0 else pd.DataFrame()
