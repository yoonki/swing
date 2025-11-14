# 스윙매매 종목 추천 시스템 - 코드베이스 완전 분석

## 1. 프로젝트 개요

**프로젝트명**: 스윙매매 종목 추천 시스템  
**경로**: `/Users/yoonkilee/Documents/코딩/이윤기/스윙매매`  
**프레임워크**: Streamlit (웹 UI)  
**언어**: Python 3.8+  
**주요 라이브러리**: pandas, FinanceDataReader, TA-Lib, Plotly

---

## 2. 디렉토리 구조 및 파일 목록

```
스윙매매/
├── app.py                          # 메인 Streamlit 애플리케이션 (1,326줄)
├── swing_analyzer.py               # 분석 엔진 (2,167줄) - 핵심 로직
├── talib_ui.py                    # TA-Lib 기반 UI 모듈 (25,258줄)
├── requirements.txt               # 의존성 패키지
├── start.sh                       # 실행 스크립트
├── analysis_data/                 # 분석 결과 캐시 저장 디렉토리
├── venv/                          # Python 가상 환경
└── *.md                           # 문서 파일들
```

---

## 3. 핵심 Python 파일 상세 분석

### 3.1 app.py - 메인 애플리케이션 (1,326줄)

**목적**: Streamlit 웹 대시보드로 사용자 인터페이스 제공

**주요 기능**:
1. **세션 상태 관리** (라인 67-112)
   - `st.session_state`를 이용한 캐시 데이터 관리
   - 분석 결과, 차트 데이터, 선택된 종목 등 추적

2. **레이아웃 및 스타일** (라인 21-65)
   - CSS 스타일 정의 (제목, 서브타이틀, 진행률, 메트릭)
   - 반응형 레이아웃 구성

3. **사이드바 설정** (라인 120-143)
   - 최소 점수 필터 슬라이더 (0-100, 기본값 50)
   - 분석 기준 설명 (MA, RSI, MACD, 변동성, 거래량)

4. **탭 구조** (라인 146)
   - 🎯 추천 종목
   - 📈 차트 분석
   - 🚀 급등주 찾기
   - 📊 데이터 테이블
   - ℹ️ 정보

#### 탭 1: 추천 종목 (라인 148-605)

**데이터 흐름**:
```
[버튼 클릭] → analyze() → SwingTradeAnalyzer.analyze_all_stocks() 
→ filter_swing_candidates() → DataFrame 반환 → UI 표시
```

**주요 기능**:
- 캐시 데이터 우선 사용 (같은 날 데이터)
- 통합 분석기(ComprehensiveAnalyzer) 실행
- 스윙매매 + 급등주 + 급등신호 병렬 분석
- 진행률 콜백으로 실시간 UI 업데이트

**결과 표시**:
- 등급별 종목 수 (Strong Buy, Buy)
- 점수 분포 히스토그램 (Plotly)
- 추천 종목 순위 테이블 (1-20위)
- CSV 다운로드 버튼
- 종목 통합 정보 조회 섹션

**통합 정보 조회** (라인 409-601):
- 선택된 종목의 추천, 급등주, 급등신호 정보 한화면 표시
- 3개 세부 탭으로 정보 분류

#### 탭 2: 차트 분석 (라인 607-1045)

**주요 기능**:
- 종목 선택 드롭다운 + 이전/다음 버튼
- 기간 선택 (1개월, 3개월, 6개월)
- FinanceDataReader로 가격 데이터 조회
- 차트 렌더링:
  - 캔들스틱 (상승: 적색, 하락: 청색)
  - 이동평균선 (MA5, MA20, MA60)
  - 거래량 바 차트
  - MACD 차트
  - 변동성 추이 차트

**데이터 처리** (라인 688-773):
```python
# MultiIndex 처리
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

# 컬럼명 정리 및 매핑
col_map = {'open': 'Open', 'high': 'High', ...}
df = df.rename(columns=col_map)

# 데이터 타입 변환
df[required_cols] = df[required_cols].apply(pd.to_numeric, errors='coerce')
df = df.dropna()
```

**차트 생성** (라인 780-1021):
- Plotly Figure 객체 생성
- Candlestick 트레이스 추가
- 이동평균선 트레이스 추가
- 커스텀 색상 및 레이아웃 설정

#### 탭 3: 급등주 찾기 (라인 1048-1050)

- `talib_ui.render_talib_soaring_tab()` 함수 호출
- TA-Lib 기반 패턴 감지 UI

#### 탭 4: 데이터 테이블 (라인 1052-1234)

**하위 탭**:
1. 추천 종목: 필터링된 스윙매매 결과
2. 급등주: TA-Lib 패턴 감지 결과

**기능**:
- HTML 테이블로 표시 (Naver 증권 링크 포함)
- Excel 다운로드 기능
  - xlsxwriter를 이용한 HYPERLINK 수식
  - 파란색 포맷된 티커, Bold 종목명

**주요 함수**:
- `create_clickable_dataframe()`: 링크 포함 HTML 테이블 생성
- `get_excel_download_link()`: Excel 파일 생성

#### 탭 5: 정보 (라인 1236-1316)

- 기술적 분석 방법 설명
- 사용법 가이드
- 지표 설명
- 주의사항

---

### 3.2 swing_analyzer.py - 분석 엔진 (2,167줄)

**구조**: 9개의 클래스 + 1개의 필터링 함수

#### 클래스 1: SwingTradeAnalyzer (라인 18-460)

**목적**: KOSPI 전체 종목을 스윙매매 기준으로 분석

**주요 메서드**:

1. **`get_kospi_stocks()`** (라인 53-131)
   - 3단계 폴백 메커니즘으로 KOSPI 종목 조회
   - 1️⃣ FinanceDataReader (fdr.StockListing)
   - 2️⃣ KRX 공식 CSV 다운로드
   - 3️⃣ Naver Finance API (최소 데이터)
   - 결과: Code, Name 컬럼의 DataFrame

2. **`get_stock_data()`** (라인 133-200)
   - FinanceDataReader로 개별 종목 데이터 조회
   - 재시도 로직 (최대 3회, 0.5초 간격)
   - 필수 컬럼: Open, High, Low, Close, Volume
   - 최소 요구사항: 20개 캔들 이상

3. **`calculate_indicators()`** (라인 202-229)
   - **이동평균선**: MA5, MA20, MA60 (rolling window)
   - **RSI**: 14일 기준 상대강도지수
   - **MACD**: 12-26-9 설정
     - MACD = EMA12 - EMA26
     - Signal = EMA9 of MACD
     - Histogram = MACD - Signal
   - **거래량 MA**: 20일 평균
   - **변동성**: 20일 표준편차 / 평균 * 100

4. **`calculate_rsi()`** (라인 231-239)
   ```python
   delta = prices.diff()
   gain = delta[delta > 0].rolling(period).mean()
   loss = -delta[delta < 0].rolling(period).mean()
   rs = gain / loss
   rsi = 100 - (100 / (1 + rs))
   ```

5. **`calculate_macd()`** (라인 241-253)
   ```python
   ema_fast = prices.ewm(span=12).mean()
   ema_slow = prices.ewm(span=26).mean()
   macd = ema_fast - ema_slow
   signal_line = macd.ewm(span=9).mean()
   hist = macd - signal_line
   ```

6. **`is_uptrend()`** (라인 255-266)
   - 조건: MA5 > MA20 > MA60
   - 상승 추세 확인

7. **`check_golden_cross()`** (라인 268-279)
   - MA20이 MA60을 상향 돌파하는 시점 감지
   - 골든크로스 = 강세 신호

8. **`check_rsi_condition()`** (라인 281-291)
   - 조건: 30 ≤ RSI ≤ 70
   - 과매수/과매도 회피

9. **`check_macd_bullish()`** (라인 293-303)
   - 조건: MACD > Signal
   - 상승 신호 확인

10. **`calculate_volatility_score()`** (라인 305-321)
    ```
    변동성 2-8% = 100점
    변동성 < 2% = (변동성 / 2) * 100
    변동성 > 8% = max(0, 100 - (변동성 - 8) * 5)
    ```

11. **`calculate_volume_score()`** (라인 323-340)
    ```
    거래량비 = 현재 거래량 / 20일 평균
    점수 = min(100, 거래량비 * 50)  if 비 >= 1.0
    점수 = 거래량비 * 100           if 비 < 1.0
    ```

12. **`analyze_stock()`** (라인 342-410)
    **종합 점수 계산 (중요!)**:
    ```python
    condition_score = 0
    if is_uptrend: condition_score += 25
    if golden_cross: condition_score += 25
    if rsi_ok: condition_score += 20
    if macd_bullish: condition_score += 20
    # 최대 90점
    
    total_score = (condition_score * 0.4) + 
                  (volatility_score * 0.3) + 
                  (volume_score * 0.3)
    # 최대 100점
    
    가중치: 조건 40%, 변동성 30%, 거래량 30%
    ```
    
    **추천 등급**:
    - Strong Buy (⭐⭐⭐): 총점 ≥ 70
    - Buy (⭐⭐): 50 ≤ 총점 < 70
    - Hold: 총점 < 50

13. **`analyze_all_stocks()`** (라인 412-459)
    - 모든 KOSPI 종목 순회 분석
    - 진행 콜백으로 UI 업데이트
    - 필터링: 점수 ≥ 50, 변동성 2-8%, 상승추세
    - 점수 내림차순 정렬

---

#### 필터링 함수: filter_swing_candidates() (라인 462-478)

```python
filtered = results_df[
    (is_uptrend == True) &
    (total_score >= min_score) &  # 기본값 50
    (volatility >= 2) &
    (volatility <= 8)
].sort_values('total_score', ascending=False)
```

---

#### 클래스 2: SoaringStockFinder (라인 481-639)

**목적**: 112MA, 224MA, 448MA 정배열 종목 발굴 (장기 급등주)

**분석 주기**: 120일 이상 장기 데이터 기반

---

#### 클래스 3-5: BullishBreakawayFinder, MorningStarFinder, TalibPatternFinder

**목적**: TA-Lib 캔들스틱 패턴 감지

**주요 패턴**:
- **Morning Star**: 저점 > 중간 > 종가 패턴 (강력한 상승신호)
- **Bullish Breakaway**: 저항선 돌파 (상승 추세 시작)

**데이터**: 최근 6개월 (180일) + 500일 장기

---

#### 클래스 6: SoaringSignalFinder (라인 1323-1694)

**목적**: 급등 직전 신호 분석 (4가지 신호)

**1. 이동평균선 신호** `check_ma_alignment()` (라인 1365-1412)
```
정배열 조건: Close > MA5 > MA10 > MA20 > MA60 > MA120
강도: 조건 만족 개수 / 총 5개
점수 배분: 이동평균 30%
```

**2. 거래량 신호** `check_volume_signal()` (라인 1414-1470)
```
대량 거래량: 거래량 > 평균 * 1.5 && 상승 캔들
거래량 매집: 최근 거래량 < 이전 거래량 * 0.7 && 현재 > 평균 * 1.3
점수 배분: 거래량 25%
```

**3. 캔들스틱 신호** `check_candlestick_signal()` (라인 1472-1515)
```
윗꼬리 패턴: 최근 5개 캔들 중 3개 이상 윗꼬리 > 30%
저점 상승: 최근 10개 캔들 저점이 우상향
점수 배분: 캔들 25%
```

**4. 지지선/저항선 신호** `check_support_breakout()` (라인 1517-1570)
```
지지 반등: 현재가 > 최근 30일 최저 * 1.02
매물대 돌파: 현재가 > 최근 60일 고점 * 0.99
저점 상승 추세: polyfit으로 저점 트렌드 계산
점수 배분: 지지선 20%
```

**종합 점수** (라인 1603-1609):
```python
total_score = (MA강도 * 30) + (거래량강도 * 25) + 
              (캔들강도 * 25) + (지지강도 * 20)
# 최대 100점

급등 확률:
- 높음 ⬆️: 점수 ≥ 70
- 중간 ➡️: 50 ≤ 점수 < 70
- 낮음 ⬇️: 점수 < 50
```

---

#### 클래스 7: ComprehensiveAnalyzer (라인 1695-1780)

**목적**: 3가지 분석을 통합 실행

```python
def analyze_all_in_one(max_stocks, progress_callback):
    # 1. 스윙매매 분석 (0-33%)
    swing_results = swing_analyzer.analyze_all_stocks()
    
    # 2. 급등주 찾기 (33-66%)
    soaring_results = talib_finder.find_patterns_in_week()
    
    # 3. 급등신호 분석 (66-100%)
    signal_results = soaring_finder.find_soaring_signals()
    
    return {
        'swing_results': swing_results,
        'soaring_results': soaring_results,
        'signal_results': signal_results
    }
```

---

#### 클래스 8: ReverseMAAlignmentFinder (라인 1783-2166)

**목적**: 역배열 + 정배열 조합 분석 (선택적 기능)

---

### 3.3 talib_ui.py - TA-Lib UI 모듈

**목적**: TA-Lib 기반 급등주 찾기 탭 UI

**주요 함수**:

1. **`get_stock_data_for_chart()`** (라인 19-78)
   - 차트용 데이터 조회 (최소 100개 캔들)
   - MultiIndex 처리
   - 데이터 정제

2. **`detect_patterns_in_dataframe()`** (라인 81-118)
   ```python
   if TALIB_AVAILABLE:
       morning_star = talib.CDLMORNINGSTAR(open, high, low, close)
       breakaway = talib.CDLBREAKAWAY(open, high, low, close)
   ```
   - 패턴 감지된 인덱스 반환

3. **`create_pattern_chart()`** (라인 121-?)
   - 패턴이 표시된 Plotly 차트 생성
   - MA 트레이스 추가

4. **`render_talib_soaring_tab()`**
   - 급등주 찾기 탭 전체 UI

---

## 4. 주요 데이터 처리 흐름

### 분석 프로세스 (전체 흐름)

```
사용자 [분석 시작] 버튼 클릭
    ↓
ComprehensiveAnalyzer.analyze_all_in_one()
    ├─ [1/3] SwingTradeAnalyzer.analyze_all_stocks()
    │   ├─ get_kospi_stocks()           → KOSPI 종목 목록
    │   └─ analyze_stock() (루프)        → 각 종목 분석
    │       ├─ get_stock_data()         → 120일 데이터
    │       ├─ calculate_indicators()   → MA, RSI, MACD, 변동성, 거래량
    │       ├─ [조건 확인] is_uptrend, golden_cross, rsi_ok, macd_bullish
    │       └─ [점수 계산] condition(40%) + volatility(30%) + volume(30%)
    │   └─ filter_swing_candidates()    → 필터링 (점수≥50, 변동성 2-8%)
    │
    ├─ [2/3] TalibPatternFinder.find_patterns_in_week()
    │   ├─ get_stock_data_long()        → 500일 데이터
    │   └─ talib.CDLMORNINGSTAR, CDLBREAKAWAY (최근 7일만)
    │
    └─ [3/3] SoaringSignalFinder.find_soaring_signals()
        ├─ get_stock_data()             → 180일 데이터
        ├─ calculate_moving_averages()  → MA5/10/20/60/120
        ├─ [신호 분석]
        │   ├─ check_ma_alignment()     (이동평균 30%)
        │   ├─ check_volume_signal()    (거래량 25%)
        │   ├─ check_candlestick_signal() (캔들 25%)
        │   └─ check_support_breakout()  (지지선 20%)
        └─ [종합 점수] MA*30 + Volume*25 + Candle*25 + Support*20

결과 저장 → analysis_data/analysis_YYYY-MM-DD.csv
   ↓
UI 표시
├─ 추천 종목 테이블 (점수 내림차순)
├─ 급등주 패턴 테이블
├─ 급등신호 종목 테이블
└─ 차트 분석 (Plotly)
```

---

## 5. 점수 분포 및 추천 시스템

### 5.1 점수 계산 구조

**스윙매매 점수** (최대 100점):
- 조건 점수 (40%):
  - MA 정배열: +25점
  - 골든크로스: +25점
  - RSI 30-70: +20점
  - MACD 상승: +20점
  - 최대 90점

- 변동성 점수 (30%):
  - 2-8%: 100점
  - <2%: (변동성/2)*100
  - >8%: max(0, 100-(변동성-8)*5)

- 거래량 점수 (30%):
  - 거래량비 ≥ 1.0: min(100, 거래량비*50)
  - 거래량비 < 1.0: 거래량비*100

**최종 계산**:
```python
total_score = (condition_score * 0.4) + 
              (volatility_score * 0.3) + 
              (volume_score * 0.3)
```

### 5.2 추천 등급

| 등급 | 점수 | 심볼 | 의미 |
|------|------|------|------|
| Strong Buy | ≥70 | ⭐⭐⭐ | 적극 추천 |
| Buy | 50-69 | ⭐⭐ | 추천 |
| Hold | <50 | ⚪ | 관망 |

---

## 6. 캐시 시스템

### 캐시 파일 관리

```python
cache_filepath = f"analysis_data/analysis_{date}.csv"

# 캐시 저장
analyzer.save_analysis_results(results_df)

# 캐시 로드
cached_results = analyzer.load_cached_analysis()

# 캐시 유효성: 같은 날짜만 사용
```

**세션 캐시** (Streamlit session_state):
- `cached_swing_results`: 스윙매매 분석 결과
- `cached_soaring_results`: TA-Lib 급등주
- `cached_signal_results`: 급등신호 분석 결과
- `cached_analysis_date`: 분석 날짜

---

## 7. 오류 처리 및 에러 관리

### 7.1 데이터 조회 에러

**재시도 로직**:
```python
for attempt in range(3):  # 최대 3회 시도
    try:
        df = fdr.DataReader(ticker, start_date, end_date)
        if df is not None and len(df) >= 20:
            break
    except:
        if attempt < 2:
            time.sleep(0.5)  # 0.5초 대기 후 재시도
        else:
            return None
```

### 7.2 None 값 처리

```python
# dropna() 사용
df = df.dropna()

# 필드 유효성 확인
if pd.isna(latest['MA5']):
    return False

# 분모 0 방지
df['Upper_Tail_Ratio'] = ... / (df['High'] - df['Low'] + 0.0001)
```

### 7.3 TA-Lib 의존성

```python
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    
if not TALIB_AVAILABLE:
    raise ImportError("ta-lib이 설치되지 않았습니다...")
```

---

## 8. 발견된 잠재적 문제점 및 주의사항

### 8.1 주요 이슈

1. **네트워크 의존성**
   - FinanceDataReader와 Naver Finance API 의존
   - 인터넷 끊김 시 전체 분석 실패 가능
   - 해결책: 더 견고한 재시도 로직 추가 검토

2. **TA-Lib 필수 패키지**
   - 설치가 복잡할 수 있음 (C 컴파일 필요)
   - 미설치 시 급등주 찾기 기능 불가
   - 현재는 try-except로 처리

3. **데이터 타입 일관성**
   - MultiIndex 컬럼 처리 필요
   - 컬럼명 대소문자 일관성 필요
   - 여러 곳에서 컬럼 매핑 코드 반복

4. **부동소수점 연산**
   - RSI 계산에서 gain/loss가 0일 수 있음
   - 분모 0 방지는 되어 있으나, NaN 처리 필요

5. **메모리 사용**
   - 전체 KOSPI 종목 (약 900개) 분석 시 메모리 많이 사용
   - 개선 가능: 배치 처리, 병렬 처리

### 8.2 점수 계산 관련

1. **조건 점수의 최대값 불일치**
   - 최대 조건 점수: 90점 (25+25+20+20)
   - 40% 가중치 적용 후: 36점 최대
   - 의도적인 설계인지 확인 필요

2. **변동성 점수 경계값**
   - 정확히 2%일 때: 100점
   - 1.99%일 때: 99.5점
   - 8%일 때: 100점
   - 8.01%일 때: 99.95점
   - 부드러운 곡선 필요 검토

3. **거래량 점수의 상한**
   - `min(100, 거래량비 * 50)`
   - 거래량비 2배일 때만 100점 도달
   - 높은 거래량이 점수에 덜 반영됨

### 8.3 함수 설계

1. **중복 코드**
   - 데이터 조회, 컬럼 매핑 등이 여러 파일/클래스에 반복됨
   - 유틸리티 함수로 통합 가능

2. **매직 넘버**
   - 하드코딩된 숫자들 (5, 20, 60, 120, 14, 12, 26, 9, 2, 8 등)
   - 상수로 정의하면 유지보수 용이

3. **예외 처리**
   - 일부 함수는 예외를 swallow하고 None 반환
   - 로깅 추가 검토

---

## 9. 주요 함수 및 메서드 요약

### SwingTradeAnalyzer (스윙매매 분석)

| 함수 | 입력 | 출력 | 역할 |
|------|------|------|------|
| `get_kospi_stocks()` | - | DataFrame | KOSPI 종목 조회 |
| `get_stock_data()` | ticker, days | DataFrame | 가격 데이터 조회 |
| `calculate_indicators()` | DataFrame | DataFrame | 기술적 지표 계산 |
| `analyze_stock()` | ticker, name | dict | 개별 종목 분석 |
| `analyze_all_stocks()` | max_stocks | DataFrame | 전체 종목 분석 |

### SoaringSignalFinder (급등신호 분석)

| 함수 | 입력 | 출력 | 역할 |
|------|------|------|------|
| `check_ma_alignment()` | DataFrame | dict | 이동평균선 신호 |
| `check_volume_signal()` | DataFrame | dict | 거래량 신호 |
| `check_candlestick_signal()` | DataFrame | dict | 캔들 신호 |
| `check_support_breakout()` | DataFrame | dict | 지지선 신호 |
| `analyze_soaring_signal()` | ticker, name | dict | 종합 급등신호 |

### ComprehensiveAnalyzer (통합 분석)

| 함수 | 역할 |
|------|------|
| `analyze_all_in_one()` | 3가지 분석 동시 실행 |

---

## 10. 차트 렌더링

### Plotly 차트 종류

1. **캔들스틱 차트** (app.py 라인 784-795)
   - Open/High/Low/Close로 캔들 표시
   - 상승봉: 적색, 하락봉: 청색

2. **이동평균선** (라인 798-823)
   - MA5: 황색
   - MA20: 핑크색
   - MA60: 녹색

3. **거래량 바 차트** (라인 867-873)
   - 상승일: 녹색
   - 하락일: 빨강색

4. **MACD 차트** (라인 907-969)
   - MACD 라인: 파란색
   - Signal 라인: 빨간색
   - Histogram: 녹색/빨강색

5. **변동성 차트** (라인 976-1021)
   - 변동성 추이
   - 2-8% 범위 표시 (대시 라인)

---

## 11. 데이터 다운로드 및 내보내기

### CSV 다운로드
- UTF-8-sig 인코딩
- 파일명: `swing_analysis_YYYYMMDD_HHMMSS.csv`

### Excel 다운로드
- xlsxwriter 엔진 사용
- HYPERLINK 수식으로 클릭 가능한 링크
- 포맷: 파란색 폰트 (티커), Bold (종목명)

---

## 12. 성능 고려사항

### 시간 복잡도

- **조회**: O(n) - n개 종목
- **지표 계산**: O(m) - m개 캔들
- **종합**: O(n × m) - 약 900 × 180 = 162,000

### 메모리 사용

- 한 종목당 약 1KB (기본 정보)
- 900개 종목: 약 1MB
- 차트 데이터: 캐시되어 재조회 시 메모리 절약

---

## 13. 추천 사항 및 개선안

### 즉시 개선 가능

1. **상수 정의**
   ```python
   MA_PERIODS = {'short': 5, 'medium': 20, 'long': 60}
   RSI_PERIOD = 14
   VOLATILITY_RANGE = (2, 8)
   ```

2. **데이터 조회 유틸리티**
   ```python
   class DataFetcher:
       def fetch_stock_data(ticker, days, retries=3)
   ```

3. **에러 로깅**
   ```python
   import logging
   logger = logging.getLogger(__name__)
   logger.error(f"Failed to fetch {ticker}: {str(e)}")
   ```

### 중기 개선

1. **데이터베이스 캐싱** (SQLite)
2. **병렬 처리** (multiprocessing)
3. **더 견고한 네트워크 재시도**
4. **점수 계산 검증 테스트**

### 장기 개선

1. **머신러닝** 기반 종목 추천
2. **포트폴리오 최적화**
3. **백테스트** 시스템
4. **실시간 알림** 시스템

---

## 14. 결론

**스윙매매 종목 추천 시스템**은 다음과 같은 특징을 가진 견고한 기술적 분석 플랫폼입니다:

✅ **강점**:
- 명확한 3가지 분석 모듈 (스윙매매, 급등주, 급등신호)
- 포괄적인 기술적 지표 (MA, RSI, MACD, 변동성, 거래량)
- 직관적인 Streamlit UI
- 캐싱을 통한 성능 최적화
- 에러 처리 및 폴백 메커니즘

⚠️ **주의사항**:
- 네트워크 의존성 높음
- TA-Lib 필수 설치
- 점수 계산 로직 복잡 (40-30-30 가중치)
- 부동소수점 연산 정밀도 이슈

**전체적으로 완성도 높은 프로젝트**이며, 추가 개선으로 더욱 강화할 수 있습니다.

