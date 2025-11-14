# 📈 스윙매매 종목 추천 시스템

기술적 분석을 기반으로 KOSPI 전체 종목을 분석하여 스윙매매에 적합한 종목을 추천하는 Python 애플리케이션입니다.

## 🎯 프로젝트 특징

- **자동 데이터 수집**: FinanceDataReader를 이용한 KOSPI 전체 종목의 실시간 데이터 수집
- **기술적 분석**: 이동평균선, RSI, MACD 등 주요 지표를 통한 종합 분석
- **✨ TA-Lib 패턴 감지** (NEW): Morning Star, Bullish Breakaway 등 정확한 캔들스틱 패턴 감지
- **🔍 1주일 필터링** (NEW): 지난 7일간의 패턴만 자동 선별
- **📈 패턴 시각화** (NEW): 차트에 패턴 위치, 마커, 텍스트 라벨 표시
- **지능형 필터링**: 스윙매매에 적합한 조건을 만족하는 종목만 선별
- **시각화**: Plotly를 이용한 인터랙티브 차트 및 분석 결과
- **사용자 친화적 인터페이스**: Streamlit 기반의 직관적인 웹 대시보드

## 🔍 분석 기준

### 기술적 지표
- **MA 정배열**: 5MA > 20MA > 60MA (상승 추세 확인)
- **골든크로스**: 20MA가 60MA를 상향 돌파 (강세 신호)
- **RSI**: 30~70 범위 (과매수/과매도 회피)
- **MACD**: MACD > Signal Line (상승 신호)
- **변동성**: 2~8% (스윙매매에 적합한 변동성)
- **거래량**: 평균 이상 (유동성 확보)

### 평가 기준
- **조건 점수 (40%)**: 기술적 조건 만족도
- **변동성 점수 (30%)**: 적절한 변동성 수준
- **거래량 점수 (30%)**: 거래량 유동성

## ✨ NEW: TA-Lib 기반 급등주 찾기

스윙매매에 최적화된 **TA-Lib 패턴 감지** 기능이 추가되었습니다!

### 주요 기능
- **Morning Star Pattern**: 하락 후 강한 반등 신호
- **Bullish Breakaway**: 저항선 돌파 상승 신호
- **1주일 필터링**: 최근 7일간의 패턴만 자동 선별
- **패턴 시각화**: 차트에 패턴 위치를 마커와 라벨로 표시
- **차트 네비게이션**: 이전/다음 버튼으로 종목 간편 이동
- **네이버 증권 연동**: 티커 클릭으로 자동 이동
- **자동 캐시**: 지난 7일 데이터 자동 로드

### 사용법
1. **급등주 찾기** 탭 (Tab 2) 클릭
2. **새로운 스캔 실행** 버튼 클릭
3. 스캔 범위 선택 (테스트 50개 / 빠른 스캔 200개 / 전체 958개)
4. 결과 확인 및 차트 분석

자세한 내용은 **QUICK_START.md** 참조

---

## 📋 시스템 요구사항

- **Python**: 3.8 이상
- **OS**: macOS, Linux, Windows
- **메모리**: 최소 2GB
- **TA-Lib**: 0.4.28 이상 (급등주 찾기 기능 사용 시 필수)

## 🚀 설치 및 실행

### ⚡ 빠른 시작 (TA-Lib 필수 설치)

```bash
# 1단계: TA-Lib 설치
brew install ta-lib          # macOS
pip install TA-Lib

# 2단계: 의존성 설치
pip install -r requirements.txt

# 3단계: 설정 검증
python3 verify_setup.py

# 4단계: 앱 실행
streamlit run app.py
```

자세한 내용은 **QUICK_START.md** 참조

---

### 1. 프로젝트 디렉토리로 이동
```bash
cd /Users/yoonkilee/Documents/코딩/이윤기/스윙매매
```

### 2. start.sh 스크립트 실행 (권장)
```bash
./start.sh
```

**start.sh가 자동으로 수행할 작업:**
- Python 버전 확인
- 가상 환경 생성 및 활성화
- 필수 패키지 설치
- Streamlit 앱 실행

### 3. 수동 설치 (대안)
```bash
# 가상 환경 생성
python3 -m venv venv

# 가상 환경 활성화
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate  # Windows

# 필수 패키지 설치
pip install -r requirements.txt

# 앱 실행
streamlit run app.py
```

## 📊 애플리케이션 사용법

### 시작 화면
1. **추천 종목**: 분석 시작 및 최상위 추천 종목 확인
2. **차트 분석**: 선택한 종목의 기술적 차트 분석
3. **데이터 테이블**: 전체 분석 결과를 테이블로 확인 및 다운로드
4. **정보**: 스윙매매 전략 및 실전 팁 참고

### 주요 기능

#### 🎯 추천 종목 탭
- **분석 시작 버튼**: KOSPI 전체 종목 분석
- **필터 조정**: 최소 점수 슬라이더로 추천 기준 설정
- **등급 분류**:
  - ⭐⭐⭐ Strong Buy (점수 70 이상): 적극 추천
  - ⭐⭐ Buy (점수 50~70): 추천
  - 점수 분포 차트로 시장 상황 파악

#### 📈 차트 분석 탭
- 종목별 캔들스틱 차트
- 이동평균선(MA5, MA20, MA60) 시각화
- 1개월, 3개월, 6개월 기간 선택
- 실시간 기술적 지표 확인

#### 📊 데이터 테이블 탭
- 모든 분석 결과를 테이블 형식으로 확인
- 원하는 정보 선택해서 표시
- CSV 형식으로 데이터 다운로드

## 📁 프로젝트 구조

```
스윙매매/
├── 📋 문서
│   ├── README.md                      # 이 파일
│   ├── QUICK_START.md                 # 빠른 시작 가이드 (⭐ 먼저 읽기)
│   ├── IMPLEMENTATION_COMPLETE.md     # 전체 구현 설명
│   ├── TALIB_UPDATE.md               # TA-Lib 기능 설명
│   └── FIX_REPORT.md                 # 수정 사항 기록
│
├── 💻 소스 코드
│   ├── app.py                         # Streamlit 메인 애플리케이션
│   ├── talib_ui.py                   # TA-Lib UI 모듈 (NEW)
│   ├── swing_analyzer.py             # 스윙매매 분석 엔진
│   └── config.py                     # 설정 파일
│
├── 🚀 실행/검증
│   ├── start.sh                       # 시작 스크립트
│   ├── verify_setup.py               # 설정 검증 스크립트 (NEW)
│   └── requirements.txt              # Python 의존성
│
└── 📁 데이터 (자동 생성)
    ├── venv/                          # 가상 환경
    └── analysis_data/                 # 캐시 파일
        └── talib_week_patterns_YYYY-MM-DD.csv
```

## 🔧 파일 설명

### app.py
Streamlit 기반의 웹 인터페이스
- 4개 탭 대시보드 (추천 종목, 기술 분석, **급등주 찾기 (NEW)**, 설정)
- 인터랙티브 차트 및 데이터 시각화
- 사용자 설정 기능
- 크기: 29.5 KB

### talib_ui.py (NEW!)
TA-Lib 기반 UI 모듈
- `render_talib_soaring_tab()`: 급등주 찾기 메인 함수
- 패턴 감지 및 시각화
- 차트 네비게이션
- 4개 탭 UI (전체/Morning Star/Breakaway/차트분석)
- 크기: 24.8 KB

### swing_analyzer.py
스윙매매 분석 엔진
- `SwingTradeAnalyzer`: 메인 분석 클래스
- `TalibPatternFinder`: TA-Lib 패턴 감지 클래스 (NEW)
- KOSPI 종목 데이터 수집
- 기술적 지표 계산
- 개별 및 전체 종목 분석
- `filter_swing_candidates()`: 후보 종목 필터링
- 크기: 48.3 KB

### requirements.txt
필수 Python 패키지
- pandas: 데이터 처리
- numpy: 수치 계산
- TA-Lib: 패턴 감지 (NEW)
- yfinance: 주가 데이터
- streamlit: 웹 인터페이스
- plotly: 인터랙티브 차트

### verify_setup.py (NEW!)
설정 검증 스크립트
- Python 버전 확인
- 필수 파일 확인
- 문법 검사
- Import 검증
- 세션 상태 확인
- 모든 조건 자동 검증

### start.sh
자동 실행 스크립트
- Python 버전 확인
- 가상 환경 설정
- 패키지 자동 설치
- Streamlit 실행

## 💡 사용 팁

### 효과적인 분석을 위한 팁

1. **필터 조정**: 처음에는 점수 50 이상으로 설정하여 충분한 양의 종목 확인
2. **차트 분석**: 추천 종목의 차트를 꼭 확인하여 기술적 상황 파악
3. **정기 분석**: 매일 또는 주 1-2회 정기적으로 분석 실행
4. **종목 압축**: 분석 결과 중 최상위 20~30개 종목에 집중

### 거래 시 주의사항

⚠️ **꼭 읽어주세요**

1. **이 추천은 참고만** - 투자 판단은 본인의 책임입니다
2. **종목 재확인** - 실제 투자 전 추가 분석 필수
3. **손절 설정** - 손절과 목표가를 미리 정하고 지키세요
4. **소액부터 시작** - 경험을 쌓을 때까지 소액으로 시작
5. **감정 거래 회피** - 뉴스나 추격 매수 피하기
6. **분산 투자** - 한 종목에 집중하지 말기

## 🐛 문제 해결

### "Python을 찾을 수 없습니다" 에러
```bash
# Python 설치 확인
python3 --version

# Homebrew로 설치 (macOS)
brew install python3
```

### 패키지 설치 실패
```bash
# pip 업그레이드
python3 -m pip install --upgrade pip

# 다시 설치 시도
pip install -r requirements.txt
```

### Streamlit 포트 충돌
```bash
# 다른 포트로 실행
streamlit run app.py --server.port 8502
```

### 데이터 조회 실패
- 인터넷 연결 확인
- FinanceDataReader 문제일 수 있으니 잠시 후 다시 시도

## 📚 스윙매매 전략 개요

### 핵심 원리
- **진입**: 상승 파동 초기에 저점에서 진입
- **보유**: 2~3일에서 1~2주 정도 보유
- **청산**: 고점 근처에서 매도, 변곡점에서 손절

### 장점
- 빠른 수익 실현 가능
- 다양한 거래 기회
- 장기투자보다 여유로운 대응

### 단점
- 정확한 타이밍 필요
- 변동성 리스크
- 빈번한 매매로 수수료 부담

## 🔗 관련 자료

- [FinanceDataReader 문서](https://github.com/FinanceData/FinanceDataReader)
- [Streamlit 문서](https://docs.streamlit.io/)
- [Plotly 문서](https://plotly.com/python/)

## 📝 라이선스

개인 학습 및 분석 목적으로 자유롭게 사용 가능합니다.

## ⚠️ 면책 조항

이 애플리케이션은 **교육 및 분석 목적**으로만 제공됩니다.
- 제공되는 분석 결과는 참고자료일 뿐입니다.
- 투자 결정은 본인의 책임입니다.
- 과거 성과가 미래 성과를 보장하지 않습니다.
- 투자 시 충분한 검토와 자문을 받으세요.

---

## 📖 더 알아보기

**처음 사용자는 이 순서로 읽어주세요:**

1. **QUICK_START.md** ← 5분 안에 시작하기
2. **IMPLEMENTATION_COMPLETE.md** ← 전체 기능 설명
3. **TALIB_UPDATE.md** ← TA-Lib 패턴 가이드
4. **FIX_REPORT.md** ← 기술적 수정 사항

**현재 상태**: ✅ Ready for Testing (모든 기능 검증 완료)

---

**마지막 업데이트**: 2025년 11월 13일
**버전**: 2.0.0 (TA-Lib 기반 급등주 찾기 기능 추가)
**상태**: ✅ Production Ready
