"""SEMrush Enterprise → BigQuery 데이터 파이프라인 (CLI)

사용법:
    # 웹 포털 실행
    streamlit run app.py

    # 전체 모델 7일치 수집
    python main.py

    # 특정 모델만
    python main.py --model search-gpt

    # 날짜 지정
    python main.py --start 2026-04-01 --end 2026-04-07

    # 브랜드 변경
    python main.py --brand Samsung
"""

import argparse
import sys
from datetime import datetime, timedelta
import pandas as pd
from semrush_client import SEMrushClient
from bigquery_loader import BigQueryLoader


def main() -> int:
    """SEMrush → BigQuery 적재. 종료 코드는 Cloud Run Job/Scheduler가 실패 감지에 사용.

    종료 코드:
      0 — 성공 (모든 모델 데이터 적재 완료)
      2 — 부분 실패 (일부 모델 fetch 실패, 적재된 데이터는 있음)
      1 — 전체 실패 (모든 모델 실패 또는 적재 자체 실패)
    """
    parser = argparse.ArgumentParser(description="SEMrush Enterprise → BigQuery")
    parser.add_argument("--project", help="프로젝트 코드 (예: AU_D2C). 미지정 시 전체 프로젝트 수집")
    parser.add_argument("--model", help="특정 AI 모델만 수집 (예: search-gpt)")
    parser.add_argument("--brand", default="LG", help="브랜드 필터 (기본: LG)")
    parser.add_argument("--start", help="시작일 (YYYY-MM-DD)")
    parser.add_argument("--end", help="종료일 (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=7, help="수집 일수 (기본: 7)")
    args = parser.parse_args()

    client = SEMrushClient()
    loader = BigQueryLoader()

    end_date = args.end or datetime.now().strftime("%Y-%m-%d")
    if args.start:
        start_date = args.start
    else:
        start = datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=args.days - 1)
        start_date = start.strftime("%Y-%m-%d")

    date_range = (start_date, end_date)
    models = [args.model] if args.model else client.AI_MODELS
    projects = [args.project] if args.project else list(client.PROJECTS.keys())

    print("=" * 50)
    print("SEMrush Enterprise → BigQuery Pipeline")
    print(f"Projects: {', '.join(projects)}")
    print(f"Brand: {args.brand} | Date: {start_date} ~ {end_date}")
    print(f"Models: {', '.join(models)}")
    print("=" * 50)

    any_success = False
    any_failure = False

    for proj in projects:
        print(f"\n{'─' * 50}")
        print(f"프로젝트: {proj}")
        print(f"{'─' * 50}")
        table_name = f"L0_Raw_visibility_{proj}"

        all_frames = []
        failures = []
        for model in models:
            print(f"\n  ▶ {model} 수집 중...")
            try:
                df = client.fetch_ai_visibility(
                    project=proj, model=model,
                    brand=args.brand, date_range=date_range,
                )
                if not df.empty:
                    all_frames.append(df)
                    print(f"    → {len(df)}행")
                else:
                    print(f"    → 데이터 없음")
            except Exception as e:
                print(f"    → 실패: {e}", file=sys.stderr)
                failures.append((model, str(e)))

        if not all_frames:
            print(f"\n  [{proj}] 적재할 데이터 없음", file=sys.stderr)
            any_failure = True
            continue

        combined = pd.concat(all_frames, ignore_index=True)
        print(f"\n  ▶ BigQuery 저장 중... ({len(combined)}행 → {table_name})")
        try:
            result = loader.load_dataframe(combined, table_name)
            print(f"    → {result['status']} ({result['rows']}행, 누적 {result.get('total_rows', '?')}행)")
            any_success = True
        except Exception as e:
            print(f"\n  적재 실패: {e}", file=sys.stderr)
            any_failure = True
            continue

        if failures:
            any_failure = True
            for model, err in failures:
                print(f"    실패: {model} — {err}", file=sys.stderr)

    # VIEW 갱신
    if any_success:
        print(f"\n▶ L0_Raw_visibility VIEW 갱신 중...")
        try:
            loader.refresh_l0_view()
            print("  → VIEW 갱신 완료")
        except Exception as e:
            print(f"  → VIEW 갱신 실패: {e}", file=sys.stderr)

    print("\n" + "=" * 50)
    if not any_success:
        print("전체 실패")
        return 1
    if any_failure:
        print("부분 완료")
        return 2
    print("완료!")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(main())
