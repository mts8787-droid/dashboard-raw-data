"""SEMrush Enterprise → BigQuery 데이터 파이프라인 (CLI)

사용법:
    # 웹 포털 실행
    streamlit run app.py

    # CLI로 전체 데이터 수집
    python main.py --domain example.com --all

    # 특정 데이터만 수집
    python main.py --domain example.com --visibility
    python main.py --domain example.com --citations
    python main.py --domain example.com --audit
    python main.py --domain example.com --analytics
"""

import argparse
from semrush_client import SEMrushClient
from bigquery_loader import BigQueryLoader
from config import TARGET_DOMAIN


def collect_visibility(client: SEMrushClient, loader: BigQueryLoader):
    print("\n▶ Visibility Index 수집 중...")
    df = client.get_visibility_history()
    result = loader.load_dataframe(df, "visibility_index")
    print(f"  → {result['status']} ({result['rows']}행)")

    print("▶ Position Tracking 수집 중...")
    df = client.get_position_tracking()
    result = loader.load_dataframe(df, "position_tracking")
    print(f"  → {result['status']} ({result['rows']}행)")


def collect_citations(client: SEMrushClient, loader: BigQueryLoader):
    print("\n▶ Citation/Listing 데이터 수집 중...")
    df = client.get_citations_df()
    result = loader.load_dataframe(df, "citations")
    print(f"  → {result['status']} ({result['rows']}행)")


def collect_audit(client: SEMrushClient, loader: BigQueryLoader):
    print("\n▶ Site Audit 데이터 수집 중...")
    df = client.get_site_audit_info()
    result = loader.load_dataframe(df, "site_audit")
    print(f"  → {result['status']} ({result['rows']}행)")


def collect_analytics(client: SEMrushClient, loader: BigQueryLoader, domain: str):
    print(f"\n▶ Domain Analytics 수집 중 ({domain})...")
    for name, func in [
        ("domain_overview", lambda: client.domain_overview(domain)),
        ("domain_organic_keywords", lambda: client.domain_organic_keywords(domain)),
        ("domain_adwords_keywords", lambda: client.domain_adwords_keywords(domain)),
        ("backlinks_overview", lambda: client.domain_backlinks_overview(domain)),
        ("organic_competitors", lambda: client.organic_competitors(domain)),
    ]:
        print(f"  {name}...")
        try:
            df = func()
            result = loader.load_dataframe(df, name)
            print(f"    → {result['status']} ({result['rows']}행)")
        except Exception as e:
            print(f"    → 실패: {e}")


def main():
    parser = argparse.ArgumentParser(description="SEMrush Enterprise → BigQuery")
    parser.add_argument("--domain", help="대상 도메인")
    parser.add_argument("--all", action="store_true", help="모든 데이터 수집")
    parser.add_argument("--visibility", action="store_true", help="Visibility/Position 수집")
    parser.add_argument("--citations", action="store_true", help="Citations 수집")
    parser.add_argument("--audit", action="store_true", help="Site Audit 수집")
    parser.add_argument("--analytics", action="store_true", help="Domain Analytics 수집")
    parser.add_argument("--database", help="SEMrush DB (us, kr, jp 등)")
    args = parser.parse_args()

    client = SEMrushClient(database=args.database)
    loader = BigQueryLoader()

    run_all = args.all or not any([args.visibility, args.citations, args.audit, args.analytics])

    print("=" * 50)
    print("SEMrush Enterprise → BigQuery Pipeline")
    print("=" * 50)

    if run_all or args.visibility:
        collect_visibility(client, loader)
    if run_all or args.citations:
        collect_citations(client, loader)
    if run_all or args.audit:
        collect_audit(client, loader)
    if run_all or args.analytics:
        collect_analytics(client, loader, args.domain or TARGET_DOMAIN)

    print("\n" + "=" * 50)
    print("완료!")
    print("=" * 50)


if __name__ == "__main__":
    main()
