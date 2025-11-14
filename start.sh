#!/bin/bash

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 현재 디렉토리
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}스윙매매 종목 추천 시스템${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# Python 버전 확인
echo -e "${YELLOW}Python 버전 확인 중...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3을 찾을 수 없습니다. Python3을 설치해주세요.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Python $PYTHON_VERSION 발견${NC}"
echo ""

# 가상 환경 생성 및 활성화
echo -e "${YELLOW}가상 환경 설정 중...${NC}"
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "가상 환경 생성 중..."
    python3 -m venv "$SCRIPT_DIR/venv"
fi

# 가상 환경 활성화
source "$SCRIPT_DIR/venv/bin/activate"
echo -e "${GREEN}✓ 가상 환경 활성화됨${NC}"
echo ""

# 의존성 설치
echo -e "${YELLOW}필수 패키지 설치 중...${NC}"
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "이 과정은 처음 실행 시 시간이 걸릴 수 있습니다..."
fi
pip install --upgrade pip -q 2>/dev/null
pip install -r "$SCRIPT_DIR/requirements.txt" -q 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 패키지 설치 완료${NC}"
else
    echo -e "${RED}❌ 패키지 설치 실패${NC}"
    echo "❌ 설치 재시도 중..."
    pip install -r "$SCRIPT_DIR/requirements.txt"
fi
echo ""

# Streamlit 앱 실행
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Streamlit 앱 실행 중...${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "${YELLOW}💡 팁: 로컬 URL (보통 http://localhost:8501)에서 접속할 수 있습니다.${NC}"
echo -e "${YELLOW}   브라우저가 자동으로 열리지 않으면 위 주소를 복사해서 브라우저에 붙여넣으세요.${NC}"
echo ""

cd "$SCRIPT_DIR"
streamlit run app.py --logger.level=error
