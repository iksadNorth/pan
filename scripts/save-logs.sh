#!/bin/bash
# Docker 컨테이너 로그를 파일로 저장하는 스크립트

LOG_DIR="./logs"
mkdir -p "$LOG_DIR"/{selenium-hub,chrome-node-1,chrome-node-2,api-server}

echo "Docker 컨테이너 로그를 저장합니다..."

# Selenium Hub 로그
if docker ps | grep -q selenium-hub; then
    docker logs selenium-hub > "$LOG_DIR/selenium-hub/hub-$(date +%Y%m%d-%H%M%S).log" 2>&1
    echo "✓ selenium-hub 로그 저장 완료"
fi

# Chrome Node 1 로그
if docker ps | grep -q chrome-node-1; then
    docker logs chrome-node-1 > "$LOG_DIR/chrome-node-1/node-1-$(date +%Y%m%d-%H%M%S).log" 2>&1
    echo "✓ chrome-node-1 로그 저장 완료"
fi

# Chrome Node 2 로그
if docker ps | grep -q chrome-node-2; then
    docker logs chrome-node-2 > "$LOG_DIR/chrome-node-2/node-2-$(date +%Y%m%d-%H%M%S).log" 2>&1
    echo "✓ chrome-node-2 로그 저장 완료"
fi

# API Server 로그
if docker ps | grep -q api-server; then
    docker logs api-server > "$LOG_DIR/api-server/api-$(date +%Y%m%d-%H%M%S).log" 2>&1
    echo "✓ api-server 로그 저장 완료"
fi

echo "모든 로그 저장 완료!"

