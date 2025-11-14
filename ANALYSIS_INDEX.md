# 코드베이스 분석 문서 인덱스

**생성일**: 2025-11-14  
**분석도**: Very Thorough (완전 분석)  
**분석 대상**: Swing Trading Stock Recommender System

---

## 문서 목록

### 1. EXPLORATION_SUMMARY.md (이 글 참조)
**길이**: ~400줄  
**목적**: 빠른 개요 제공

**포함 내용**:
- 프로젝트 구조 (3개 파일, 3,463줄)
- 3가지 핵심 분석 모듈
- 점수 계산 상세 분석
- 강점/약점 요약
- 종합 평가

**추천 대상**: 빠른 이해가 필요한 개발자

---

### 2. CODEBASE_ANALYSIS.md
**길이**: 752줄 (매우 상세)  
**목적**: 완전한 코드베이스 문서화

**포함 내용**:
- 프로젝트 개요 및 구조
- 3개 파일 라인별 상세 분석
- 8개 클래스 상세 설명
  - SwingTradeAnalyzer (전체 점수 계산 로직)
  - SoaringSignalFinder (4가지 신호 분석)
  - ComprehensiveAnalyzer (통합 실행)
  - 외 5개 클래스
- 데이터 처리 흐름도
- 점수 계산 상세 분석
- 캐시 시스템 설명
- 오류 처리 메커니즘
- 발견된 15개 이상의 이슈
- 성능 고려사항
- 13개 개선 제안

**추천 대상**: 깊은 이해가 필요한 개발자, 유지보수 담당자

---

### 3. 원본 문서들 (프로젝트 포함)
- **README.md**: 프로젝트 소개
- **QUICKSTART.md**: 빠른 시작 가이드
- **SETUP_INSTRUCTIONS.md**: 설치 방법
- **SESSION_COMPLETION_SUMMARY.md**: 최종 작업 요약
- **CHART_FIX.md**, **CHART_IMPROVEMENTS.md**: 차트 관련 개선

---

## 핵심 내용 요약

### 프로젝트 구조

```
스윙매매 종목 추천 시스템
│
├─ app.py (1,326줄)
│  ├─ 세션 상태 관리 (45줄)
│  ├─ UI 스타일 (44줄)
│  └─ 5개 탭 구현 (1,237줄)
│     ├─ 📊 추천 종목 (458줄)
│     ├─ 📈 차트 분석 (438줄)
│     ├─ 🚀 급등주 찾기 (3줄)
│     ├─ 📋 데이터 테이블 (182줄)
│     └─ ℹ️ 정보 (81줄)
│
├─ swing_analyzer.py (2,167줄)
│  ├─ SwingTradeAnalyzer (442줄)
│  ├─ SoaringStockFinder (159줄)
│  ├─ BullishBreakawayFinder (176줄)
│  ├─ MorningStarFinder (321줄)
│  ├─ TalibPatternFinder (186줄)
│  ├─ SoaringSignalFinder (371줄)  ← 4가지 신호 분석
│  ├─ ComprehensiveAnalyzer (86줄) ← 통합 실행
│  └─ ReverseMAAlignmentFinder (384줄)
│
└─ talib_ui.py (25,258줄)
   └─ TA-Lib 패턴 감지 UI
```

### 핵심 분석 로직

#### 1️⃣ 스윙매매 점수 (SwingTradeAnalyzer)
```
조건 점수 (40%) = (MA+Golden+RSI+MACD) × 0.4
변동성 점수 (30%) = 변동성_점수 × 0.3
거래량 점수 (30%) = 거래량_점수 × 0.3
─────────────────────────────────────
총점 (0-100) = 조건 + 변동성 + 거래량

등급:
Strong Buy (≥70) | Buy (50-69) | Hold (<50)
```

#### 2️⃣ 급등신호 점수 (SoaringSignalFinder)
```
이동평균 정배열 (30%) → check_ma_alignment()
거래량 신호 (25%)      → check_volume_signal()
캔들스틱 패턴 (25%)    → check_candlestick_signal()
지지선/저항선 (20%)    → check_support_breakout()
─────────────────────────────────────
총점 (0-100) = MA×30 + Volume×25 + Candle×25 + Support×20

확률:
높음(≥70) | 중간(50-69) | 낮음(<50)
```

#### 3️⃣ TA-Lib 패턴 (TalibPatternFinder)
```
Morning Star    → 하락 후 강한 상승신호
Bullish Breakaway → 저항선 돌파 상승
(최근 7일만 필터링)
```

---

## 주요 발견사항

### ✅ 강점
1. 명확한 3가지 분석 모듈
2. 포괄적 기술적 지표
3. 직관적인 Streamlit UI
4. 캐싱 시스템
5. 견고한 에러 처리

### ⚠️ 약점
1. 네트워크 의존성 높음
2. TA-Lib 필수 설치
3. 점수 계산 복잡도
4. 코드 중복 (특히 데이터 조회)
5. 부동소수점 연산 정밀도

---

## 파일별 주요 함수

### SwingTradeAnalyzer
| 함수 | 입력 | 목적 |
|------|------|------|
| `get_kospi_stocks()` | - | KOSPI 900개 종목 조회 |
| `get_stock_data()` | ticker | 120일 가격 데이터 |
| `calculate_indicators()` | df | MA, RSI, MACD, Vol 계산 |
| `analyze_stock()` | ticker | 개별 종목 점수 계산 (0-100) |
| `analyze_all_stocks()` | - | 모든 종목 분석 및 필터링 |

### SoaringSignalFinder
| 함수 | 신호 | 가중치 |
|------|------|--------|
| `check_ma_alignment()` | 이동평균 정배열 | 30% |
| `check_volume_signal()` | 거래량 신호 | 25% |
| `check_candlestick_signal()` | 캔들 패턴 | 25% |
| `check_support_breakout()` | 지지선/저항선 | 20% |

---

## 기술 스택

### 핵심 라이브러리
- **Streamlit** 1.28.1 - 웹 UI
- **pandas** 2.1.0 - 데이터 처리
- **Plotly** 5.17.0 - 차트
- **TA-Lib** 0.4.28 - 패턴 감지
- **FinanceDataReader** 0.9.50 - 주가 조회

### 데이터 소스
1. FinanceDataReader (1차)
2. KRX 공식 CSV (2차)
3. Naver Finance (3차 폴백)

---

## 개선 로드맵

### 즉시 (1주일)
- 상수 정의
- 데이터 조회 함수화
- 에러 로깅

### 단기 (1개월)
- 중복 코드 리팩토링
- 점수 계산 테스트
- SQLite 캐싱

### 중기 (3개월)
- 병렬 처리
- 더 견고한 네트워크 재시도
- 설정 파일 추가

### 장기 (6개월+)
- 백테스트 시스템
- 머신러닝 통합
- 실시간 알림

---

## 완성도 평가

| 항목 | 평가 | 설명 |
|------|------|------|
| **완성도** | ⭐⭐⭐⭐ | 명확한 기술분석, 좋은 통합 |
| **유지보수성** | ⭐⭐⭐ | 상수 정의, 함수화 필요 |
| **성능** | ⭐⭐⭐⭐ | 캐싱, 재시도 로직 우수 |
| **보안** | ⭐⭐⭐ | 일반적인 수준 |

---

## 문서 사용 가이드

### 빠른 이해 (5분)
→ EXPLORATION_SUMMARY.md 읽기

### 상세 이해 (30분)
→ CODEBASE_ANALYSIS.md의 섹션 3-5 읽기

### 완전 이해 (2시간)
→ CODEBASE_ANALYSIS.md 전체 읽기 + 코드 직접 검토

### 개발/유지보수 (필요시)
→ CODEBASE_ANALYSIS.md 섹션 8-13 참조

---

## 코드 위치별 가이드

### 점수 계산 로직
- **스윙매매**: swing_analyzer.py 라인 342-410
- **급등신호**: swing_analyzer.py 라인 1603-1609

### UI 구현
- **추천 종목 탭**: app.py 라인 148-605
- **차트 분석 탭**: app.py 라인 607-1045
- **데이터 테이블**: app.py 라인 1052-1234

### 데이터 처리
- **종목 조회**: swing_analyzer.py 라인 53-131
- **가격 데이터**: swing_analyzer.py 라인 133-200
- **지표 계산**: swing_analyzer.py 라인 202-229

### 필터링
- **스윙매매**: swing_analyzer.py 라인 462-478
- **패턴 (7일)**: talib_ui.py (필터 로직)

---

## FAQ

**Q: 점수가 100점이 아닌 이유?**
- 조건 점수 최대가 90점 (25+25+20+20)
- 40% 가중치로 최대 36점만 가능
- 의도적인 설계로 보임

**Q: 변동성 2-8% 범위는?**
- 스윙매매에 적합한 범위
- 너무 낮으면 수익 기회 적음
- 너무 높으면 리스크 높음

**Q: 왜 3개의 분석 모듈?**
- 다각적 분석으로 신뢰도 높임
- 각 모듈의 강점 활용
- 사용자 선택 가능

**Q: 캐싱은 언제 갱신?**
- 매일 새로운 날짜로 생성
- 같은 날은 재사용

---

## 추가 자료

### 관련 문서
- README.md: 프로젝트 개요
- requirements.txt: 필수 패키지
- start.sh: 실행 스크립트

### 외부 참고자료
- Streamlit 문서: https://docs.streamlit.io
- TA-Lib 문서: http://mrjbq7.github.io/ta-lib
- FinanceDataReader: https://github.com/FinanceData

---

**마지막 업데이트**: 2025-11-14

