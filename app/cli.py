"""Phase 1-3 terminal harness — prove the pipeline works before there's a UI.

Usage (from the project root, with the venv active):
    python -m app.cli 0xF835A0247b0063C04EF22006eBe57c5F11977Cc4
    python -m app.cli --list          (show saved cases)
"""
import sys
from dotenv import load_dotenv

from app.api_clients.etherscan import fetch_transactions
from app.data.tagpacks import load_labels
from app.data.known_mixers import KNOWN_MIXERS
from app.graph.trace import trace_to_nearest_entity
from app.graph.risk import assess
from app.data.case_store import init_db, save_case, list_cases

load_dotenv()
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252, which can't print ₹


def show_cases(limit: int = 20) -> None:
    try:
        init_db()
        cases = list_cases(limit=limit)
    except Exception as exc:
        print(f"Could not reach the case database — is DATABASE_URL set in .env? ({exc})")
        return
    if not cases:
        print("No cases saved yet.")
        return
    for c in cases:
        risk_mark = "RISK" if c["risk_flag"] else "    "
        print(f"[{c['id']:>4}] {risk_mark}  {c['created_at']}  {c['seed_address']}  "
              f"-> {c['entity_type']}/{c['label'] or '?'}  (confidence {c['confidence']})")


def run(address: str, max_hops: int = 4) -> None:
    print(f"\nLoading GraphSense TagPack labels (first run only takes a few seconds)...")
    labels = load_labels()
    print(f"Loaded {len(labels)} labeled addresses.\n")

    print(f"Tracing {address} on Ethereum (up to {max_hops} hops)...\n")
    result = trace_to_nearest_entity(
        seed_address=address,
        currency="ETH",
        fetch_transactions_fn=lambda addr: fetch_transactions(addr),
        labels_lookup=labels,
        mixers_lookup=KNOWN_MIXERS,
        max_hops=max_hops,
    )

    risk = assess(result)

    print("=" * 60)
    print(f"Seed address       : {result.seed_address}")
    print(f"Hops taken         : {result.hop_count}")
    print(f"Path               : {' -> '.join(result.path)}")
    print(f"Entity type        : {result.entity_type}")
    print(f"Label              : {result.label or '(none — Unknown/Unattributed)'}")
    print(f"Confidence         : {result.confidence}")
    if result.source:
        print(f"Source             : {result.source}")
    if result.reason:
        print(f"Reason             : {result.reason}")
    print("-" * 60)
    print(f"Compliance status  : {risk.compliance_status}")
    print(f"Compliance detail  : {risk.compliance_detail}")
    print(f"RISK FLAG          : {'YES — ' + risk.risk_reason if risk.risk_flag else 'no'}")
    print("=" * 60)

    try:
        init_db()
        case_id = save_case("ETH", result, risk)
        print(f"Saved as case #{case_id}.")
    except Exception as exc:
        print(f"(Not saved — case database unreachable. Is DATABASE_URL set in .env? {exc})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.cli <ethereum_address>\n       python -m app.cli --list")
        sys.exit(1)
    if sys.argv[1] == "--list":
        show_cases()
    else:
        run(sys.argv[1])
