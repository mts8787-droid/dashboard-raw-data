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
from datetime import datetime, timedelta
from semrush_client import SEMrushClient
from bigquery_loader import BigQueryLoader


def main():
    parser = argparse.ArgumentParser(description="SEMrush Enterprise → BigQuery")
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

    print("=" * 50)
    print("SEMrush Enterprise → BigQuery Pipeline")
    print(f"Brand: {args.brand} | Date: {start_date} ~ {end_date}")
    print(f"Models: {', '.join(models)}")
    print("=" * 50)

    all_frames = []
    for model in models:
        print(f"\n▶ {model} 수집 중...")
        try:
            df = client.fetch_ai_visibility(
                model=model, brand=args.brand, date_range=date_range
            )
            if not df.empty:
                all_frames.append(df)
                print(f"  → {len(df)}행")
            else:
                print(f"  → 데이터 없음")
        except Exception as e:
            print(f"  → 실패: {e}")

    if all_frames:
        import pandas as pd
        combined = pd.concat(all_frames, ignore_index=True)
        print(f"\n▶ BigQuery 저장 중... ({len(combined)}행)")
        result = loader.load_dataframe(combined, "ai_visibility")
        print(f"  → {result['status']} ({result['rows']}행)")

    print("\n" + "=" * 50)
    print("완료!")
    print("=" * 50)


if __name__ == "__main__":
    main()
