# 스윙매매 앱 - 설정 및 실행 가이드

## 📦 설치 및 실행 방법

### 1. 프로젝트 디렉토리 이동
```bash
cd "/Users/yoonkilee/Documents/코딩/이윤기/스윙매매"
```

### 2. 가상환경 활성화
```bash
source venv/bin/activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. Streamlit 앱 실행
```bash
streamlit run app.py
```

**기본 포트**: http://localhost:8501

---

## 📋 주요 변경사항 (v2.4.0)

### 새로운 기능
1. **Cufflinks 차트** - QuantFig를 이용한 전문적인 캔들스틱 차트
2. **자동 기술 지표** - MA5, MA20, MA60 자동 계산
3. **거래량 시각화** - Portland colorscale으로 상승/하락 구분
4. **인터랙티브 차트** - 마우스 호버, 드래그, 확대/축소 지원

### 개선사항
- 캔들스틱 차트가 명확하게 표시됨
- 이동평균선이 자동으로 계산되고 색상으로 구분됨
- 거래량이 같은 차트에 함께 표시됨 (QuantFig 사용)
- 코드가 간단해지고 유지보수가 쉬워짐

---

## 🔧 최근 추가 패키지

### cufflinks==0.17.3
Pandas DataFrame을 Plotly 차트로 쉽게 변환하는 라이브러리
- **용도**: QuantFig를 이용한 OHLC 캔들스틱 차트
- **설치**: `pip install cufflinks`
- **참고자료**: https://devscb.tistory.com/145

#### 의존 패키지 (자동 설치됨)
```
colorlover>=0.2.1
ipywidgets>=7.0.0
widgetsnbextension~=4.0.14
jupyterlab_widgets~=3.0.15
```

---

## 📊 현재 설치된 주요 패키지

```
pandas==2.1.0               # 데이터 분석
numpy==1.26.0               # 수치 계산
plotly==5.17.0              # 인터랙티브 차트
streamlit==1.28.1           # 웹 앱 프레임워크
TA-Lib==0.4.28              # 기술 지표 계산
cufflinks==0.17.3           # Plotly 래퍼 (NEW)
FinanceDataReader==0.9.50   # 주가 데이터
```

**전체 목록**: requirements.txt 참고

---

## 🎯 주요 기능

### 1. 추천 종목 탭 (🎯 추천 종목)
- 점수 50점 이상의 추천 종목 분석
- 자동으로 필터링된 종목만 표시

### 2. 차트 분석 탭 (📈 차트 분석)
**Cufflinks QuantFig 차트**
```
- 캔들스틱 (상승: 빨강, 하락: 파랑)
- 이동평균선 (MA5: 황색, MA20: 핑크, MA60: 초록)
- 거래량 (Portland colorscale)
- 범례, 호버 정보, 확대/축소 지원
```

### 3. 급등주 찾기 탭 (🚀 급등주 찾기)
- TA-Lib 패턴 감지
- Morning Star, Bullish Breakaway 패턴

### 4. 데이터 테이블 탭 (📊 데이터 테이블)
- 분석 결과 테이블 조회
- CSV 다운로드

### 5. 정보 탭 (ℹ️ 정보)
- 사용 방법
- 기술적 지표 설명
- 분석 기준

---

## ⚙️ 시스템 요구사항

- **Python**: 3.8 이상
- **OS**: macOS, Linux, Windows
- **메모리**: 최소 2GB (권장 4GB 이상)
- **인터넷**: 필수 (주가 데이터 수집)

---

## 🛠️ 문제 해결

### 문제 1: ModuleNotFoundError: No module named 'cufflinks'
**해결책**:
```bash
# venv 활성화 후 설치
source venv/bin/activate
pip install cufflinks
```

### 문제 2: TA-Lib 설치 실패
**해결책**:
```bash
# brew를 통한 설치 (macOS)
brew install ta-lib
pip install TA-Lib
```

### 문제 3: 데이터 조회 실패
**원인**: 인터넷 연결 문제 또는 데이터 소스 장애
**해결책**:
1. 인터넷 연결 확인
2. 분석 범위를 줄여서 재시도 (테스트 모드)
3. 캐시된 데이터 사용 옵션 활성화

### 문제 4: Streamlit 포트 충돌
```bash
# 다른 포트에서 실행
streamlit run app.py --server.port 8502
```

---

## 📝 파일 구조

```
스윙매매/
├── app.py                      # 메인 Streamlit 앱
├── swing_analyzer.py           # 분석 엔진
├── talib_ui.py                 # TA-Lib UI
├── requirements.txt            # 의존성
├── venv/                        # 가상환경
├── analysis_data/              # 캐시 데이터
└── 문서
    ├── CHANGES_SUMMARY.md      # 추천종목 기능 변경
    ├── CHART_FIX.md            # 차트 수정 내용
    ├── CUFFLINKS_CHART.md      # Cufflinks 구현 가이드
    └── SETUP_INSTRUCTIONS.md   # 이 파일
```

---

## 🚀 빠른 시작

```bash
# 1. 프로젝트 이동
cd "/Users/yoonkilee/Documents/코딩/이윤기/스윙매매"

# 2. venv 활성화
source venv/bin/activate

# 3. 의존성 설치 (처음 한 번만)
pip install -r requirements.txt

# 4. 앱 실행
streamlit run app.py

# 5. 웹 브라우저에서 http://localhost:8501 열기
```

---

## 📚 참고자료

- **Cufflinks 블로그**: https://devscb.tistory.com/145
- **Streamlit 공식 문서**: https://docs.streamlit.io
- **Plotly 공식 문서**: https://plotly.com/python

---

## 📧 업데이트 이력

| 버전 | 날짜 | 변경사항 |
|------|------|---------|
| v2.4.0 | 2025-11-14 | Cufflinks QuantFig 차트 추가 |
| v2.3.0 | 2025-11-14 | 차트 완전 수정 |
| v2.2.0 | 2025-11-14 | 차트 개선 |
| v2.1.0 | 2025-11-14 | 추천종목 분석 기능 추가 |
| v2.0.0 | - | 초기 버전 |

---

**마지막 수정**: 2025-11-14
**현재 버전**: v2.4.0
**상태**: ✅ 운영 중
