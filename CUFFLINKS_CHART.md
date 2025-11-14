# Cufflinks를 이용한 차트 개선

## 📚 참고자료
- 블로그: https://devscb.tistory.com/145
- Cufflinks: Pandas DataFrame을 Plotly 차트로 쉽게 변환하는 라이브러리

---

## 🎯 변경 사항

### 1. 라이브러리 추가

**requirements.txt에 추가:**
```
cufflinks==0.17.3
```

**app.py 임포트:**
```python
import cufflinks as cf

# Cufflinks 오프라인 모드 설정
cf.go_offline()
```

---

## 🔧 Cufflinks를 이용한 차트 구현

### QuantFig를 사용한 캔들스틱 차트

**기본 구조:**
```python
# 1. QuantFig 객체 생성 (OHLC 데이터 기반)
qf = cf.QuantFig(
    df,                           # OHLC 컬럼이 있는 DataFrame
    title='종목명 - 기간',
    legend='top',
    name='가격',
    up_color='#FF3131',          # 상승봉 색상
    down_color='#0047AB'         # 하락봉 색상
)

# 2. 기술 지표 추가
qf.add_sma(periods=5, column='Close', name='MA5', color='#FFB400')
qf.add_sma(periods=20, column='Close', name='MA20', color='#FF6B9D')
qf.add_sma(periods=60, column='Close', name='MA60', color='#00D084')

# 3. 거래량 추가
qf.add_volume(name='거래량', colorscale='Portland')

# 4. Plotly 차트로 변환
fig = qf.iplot(
    asFigure=True,               # Plotly Figure 반환
    dimensions=(1400, 800),
    showlegend=True,
    xTitle='날짜',
    yTitle='가격 (원)'
)

# 5. 레이아웃 커스터마이징
fig.update_layout(height=800)
```

---

## ✨ Cufflinks의 장점

### 1. **간단한 문법**
```python
# Plotly 방식 (복잡)
fig = go.Figure()
fig.add_trace(go.Candlestick(...))
fig.add_trace(go.Scatter(...))
fig.update_layout(...)

# Cufflinks 방식 (간단)
qf = cf.QuantFig(df)
qf.add_sma(...)
fig = qf.iplot(asFigure=True)
```

### 2. **자동 OHLC 인식**
- DataFrame에 Open, High, Low, Close 컬럼이 있으면 자동 인식
- 별도의 캔들스틱 설정 불필요

### 3. **기술 지표 자동 계산**
```python
# 간단한 메서드 호출만으로 기술 지표 추가
qf.add_sma(periods=20)     # 20일 이동평균
qf.add_rsi(periods=14)     # RSI
qf.add_bbands(periods=20)  # Bollinger Bands
qf.add_macd()              # MACD
qf.add_volume()            # 거래량
```

### 4. **인터랙티브 기능**
- Plotly 기반이므로 모든 인터랙티브 기능 지원
- 확대/축소, 드래그, 호버 정보 등

---

## 🎨 구현된 기술 지표

### 1. **QuantFig로 생성되는 내용**
```
├─ 캔들스틱 차트
│  ├─ 상승봉: #FF3131 (밝은 빨강)
│  └─ 하락봉: #0047AB (진한 파랑)
│
├─ 이동평균선
│  ├─ MA5: #FFB400 (황색, 5일)
│  ├─ MA20: #FF6B9D (핑크, 20일)
│  └─ MA60: #00D084 (초록, 60일)
│
├─ 거래량
│  └─ Portland colorscale (상승: 파랑→초록, 하락: 회색→빨강)
│
└─ 제목/범례/축 레이블
   └─ 자동 생성
```

---

## 🛠️ 코드 구현

### 현재 구현 (차트 분석 탭)

```python
# Cufflinks를 사용한 QuantFig 차트 생성
try:
    qf = cf.QuantFig(
        df,
        title=f'{st.session_state.selected_chart_stock} ({ticker}) - {chart_period}',
        legend='top',
        name='가격',
        up_color='#FF3131',      # 상승봉: 빨강
        down_color='#0047AB'      # 하락봉: 파랑
    )

    # 이동평균선 추가
    qf.add_sma(periods=5, column='Close', name='MA5 (5일)', color='#FFB400')
    qf.add_sma(periods=20, column='Close', name='MA20 (20일)', color='#FF6B9D')
    qf.add_sma(periods=60, column='Close', name='MA60 (60일)', color='#00D084')

    # 거래량 추가
    qf.add_volume(name='거래량', colorscale='Portland')

    # 차트 생성
    fig = qf.iplot(
        asFigure=True,
        dimensions=(1400, 800),
        showlegend=True,
        xTitle='날짜',
        yTitle='가격 (원)'
    )

    # 추가 설정
    fig.update_layout(
        height=800,
        xaxis_rangeslider_visible=False,
        hovermode='x unified',
        font=dict(size=11, family='Arial'),
        plot_bgcolor='rgba(240,240,240,0.3)',
        paper_bgcolor='white',
        legend=dict(
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='#000000',
            borderwidth=1,
            font=dict(size=10)
        )
    )

    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    # 폴백: 기본 Plotly 차트 표시
    st.error(f"❌ Cufflinks 차트 생성 실패: {str(e)}")
    # ... 기본 차트 코드
```

---

## 📊 사용 가능한 기술 지표

Cufflinks에서 사용 가능한 주요 메서드:

| 메서드 | 설명 | 파라미터 |
|--------|------|---------|
| `add_sma()` | 단순이동평균 | periods, column, name, color |
| `add_rsi()` | RSI | periods |
| `add_bbands()` | Bollinger Bands | periods |
| `add_macd()` | MACD | fast_period, slow_period, signal_period |
| `add_volume()` | 거래량 | name, colorscale |
| `add_adx()` | ADX | periods |
| `add_atr()` | ATR | periods |

---

## 🔄 폴백 메커니즘

Cufflinks 차트 생성 실패 시 기본 Plotly 차트로 자동 전환:

```python
try:
    qf = cf.QuantFig(df, ...)
    fig = qf.iplot(asFigure=True)
    st.plotly_chart(fig)
except Exception as e:
    st.error(f"Cufflinks 차트 생성 실패: {str(e)}")
    st.info("기본 차트로 표시합니다.")

    # 기본 Plotly 차트로 대체
    fig = go.Figure(data=[go.Candlestick(...)])
    st.plotly_chart(fig)
```

---

## 📈 차트 특징

### 캔들스틱 자동 표시
- Open, High, Low, Close 컬럼 자동 인식
- 별도 데이터 변환 불필요

### 이동평균선 자동 계산
- `add_sma()` 호출 시 자동으로 계산
- 색상 커스터마이징 가능

### 거래량 표시
- QuantFig에 자동 포함
- Colorscale으로 상승/하락 구분

### 인터랙티브 기능
- 마우스 호버로 상세 정보 표시
- 드래그로 확대/축소
- 범례 클릭으로 선 표시/숨김

---

## 🎯 장점 정리

✅ **간단한 구현**: 5줄로 캔들스틱 차트 완성
✅ **자동 계산**: 이동평균, RSI 등 자동 계산
✅ **일관된 스타일**: Cufflinks가 전체 스타일 관리
✅ **빠른 개발**: Plotly보다 훨씬 적은 코드
✅ **Plotly 호환**: 필요시 `update_layout()` 가능

---

## 📝 변경된 파일

### 1. requirements.txt
```
cufflinks==0.17.3  # 추가됨
```

### 2. app.py
```python
import cufflinks as cf
cf.go_offline()
```

- 라인 14-17: cufflinks 임포트 및 설정
- 라인 784-847: 차트 분석 탭의 가격 차트를 cufflinks로 변경
- 라인 849-872: 폴백 메커니즘 (기본 Plotly 차트)

---

## ✨ 결과

이제 차트 분석 탭에서 다음을 볼 수 있습니다:

```
📊 가격 차트 (Cufflinks QuantFig)
├─ 캔들스틱: 빨강(상승)/파랑(하락)
├─ MA5: 황색
├─ MA20: 핑크
├─ MA60: 초록
└─ 거래량: 자동 색상 구분

📈 거래량 (기존 - Plotly Bar)
📊 MACD (기존 - Plotly Scatter)
📉 변동성 (기존 - Plotly Scatter)
```

---

**구현 완료**: 2025-11-14
**버전**: v2.4.0
**상태**: ✅ Cufflinks 차트 적용 완료
