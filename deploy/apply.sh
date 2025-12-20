#!/bin/bash

set -e

if [ ! -f .env ]; then
    echo ".env 파일이 없습니다. .env.example을 참고하여 .env 파일을 생성하세요."
    exit 1
fi

source .env

if [ -z "$SE_VNC_PASSWORD" ]; then
    echo "SE_VNC_PASSWORD가 .env 파일에 설정되지 않았습니다."
    exit 1
fi

if [ -z "$CHROME_NODE_REPLICAS" ]; then
    echo "CHROME_NODE_REPLICAS가 .env 파일에 설정되지 않았습니다."
    exit 1
fi

if [ -z "$PAN_API_SERVER_METALLB_IP" ]; then
    echo "PAN_API_SERVER_METALLB_IP가 .env 파일에 설정되지 않았습니다."
    exit 1
fi

if [ -z "$PAN_CHROME_NODE_METALLB_IP" ]; then
    echo "PAN_CHROME_NODE_METALLB_IP가 .env 파일에 설정되지 않았습니다."
    exit 1
fi

export SE_VNC_PASSWORD
export CHROME_NODE_REPLICAS
export PAN_API_SERVER_METALLB_IP
export PAN_CHROME_NODE_METALLB_IP

echo "이미지 빌드 및 푸시 중..."
./deploy/push-image.sh api-server latest

echo "기존 리소스 삭제 중..."
kubectl delete -f deploy/api-server.yaml --ignore-not-found=true
kubectl delete -f deploy/chrome-node.yaml --ignore-not-found=true
kubectl delete -f deploy/selenium-hub.yaml --ignore-not-found=true
kubectl delete -f deploy/pvc.yaml --ignore-not-found=true
kubectl delete -f deploy/pv.yaml --ignore-not-found=true

echo "리소스 생성 중..."
kubectl apply -f deploy/pv.yaml
kubectl apply -f deploy/pvc.yaml
kubectl apply -f deploy/selenium-hub.yaml
envsubst '${SE_VNC_PASSWORD} ${CHROME_NODE_REPLICAS} ${PAN_CHROME_NODE_METALLB_IP}' < deploy/chrome-node.yaml | kubectl apply -f -
envsubst '${PAN_API_SERVER_METALLB_IP}' < deploy/api-server.yaml | kubectl apply -f -

echo "완료"

