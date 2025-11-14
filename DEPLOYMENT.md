# 스윙매매 종목 추천 시스템 배포 가이드

## 📦 빠른 설치

```bash
# 1. 저장소 클론
git clone <repository-url>
cd swing-trading

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 애플리케이션 실행
streamlit run app.py
```

## 🔧 시스템 요구사항

- Python 3.8 이상
- 메모리: 최소 2GB 권장
- 인터넷 연결 필수 (주가 데이터 조회)

## 📋 설치된 패키지

주요 의존성:
- **Streamlit** 1.28.1: 웹 프레임워크
- **Pandas** 2.1.0: 데이터 분석
- **Plotly** 5.17.0: 차트 시각화
- **TA-Lib** 0.4.28: 기술적 분석
- **yfinance** 0.2.32: 주가 데이터
- **BeautifulSoup4** 4.12.2: 웹 스크래핑

## 🎯 주요 기능

### 탭 구조 (총 5개)

1. **🎯 추천 종목**: KOSPI 전체 종목 분석 및 추천
2. **📈 차트 분석**: 선택한 종목의 기술적 분석 (기본 6개월)
3. **🚀 급등주 찾기**: TA-Lib 패턴 분석
4. **📊 데이터 테이블**: 분석 결과 조회 및 엑셀 내보내기
5. **ℹ️ 정보**: 시스템 설명 및 지표 가이드

## 🚀 배포 옵션

### Streamlit Cloud 배포 (무료)
```bash
streamlit cloud deploy
```

### Docker 배포
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
```

### 클라우드 서버 배포
- AWS EC2, Google Cloud, Azure VM 등에 배포 가능
- SSL 인증서 설정 필수
- 포트 8501 개방

## 📊 성능 최적화

- 첫 분석: 약 10~20분 (KOSPI 전체 종목 분석)
- 캐시 활용 시: 2~3초 (다른 탭 분석)
- 차트 로딩: 1~2초

## ⚙️ 트러블슈팅

### TA-Lib 설치 오류
```bash
# macOS
brew install ta-lib
pip install ta-lib

# Ubuntu
sudo apt-get install ta-lib
pip install ta-lib

# conda 사용 (권장)
conda install -c conda-forge ta-lib
```

### 메모리 부족
- 분석 범위를 "테스트 (50개)"로 줄이기
- 서버 메모리 증설

## 📞 지원

문제 발생 시 다음을 확인하세요:
1. 인터넷 연결 확인
2. Python 버전 확인 (3.8+)
3. 모든 패키지가 설치되었는지 확인
4. 포트 8501이 열려있는지 확인

---

**마지막 업데이트**: 2025-11-13
**버전**: 1.0.0
