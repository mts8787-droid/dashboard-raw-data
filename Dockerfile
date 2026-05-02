# SEMrush Enterprise → BigQuery 적재 파이프라인
# 두 가지 모드:
#   1. CLI Job (Cloud Run Job) — `python main.py`
#   2. Streamlit 관리자 (현행 Render web) — `bash start.sh`
# 기본 모드는 Job (Cloud Run Job용 컨테이너).

FROM python:3.12-slim

# 의존성 캐시 활용: requirements 먼저 복사
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사
COPY config.py semrush_client.py bigquery_loader.py main.py ./
COPY app.py start.sh chart_utils.py ./
COPY pages ./pages

# 런타임 보안: 비-root 사용자로 실행
RUN useradd --create-home --shell /bin/bash app
USER app

# 기본 진입점: CLI Job 모드 (Cloud Run Job용).
# Streamlit 모드로 띄울 땐 docker run에서 `bash start.sh`로 ENTRYPOINT 오버라이드.
ENTRYPOINT ["python", "main.py"]
CMD []
