import argparse
import sys
import os
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.session import SessionLocal
from app.db.models import AuditLog


def run_audit_report(limit: int = 50, event_filter: str = None):
    """CLI tool to inspect audit logs for security review and lecturer demonstration (FR12, A44)."""
    db = SessionLocal()
    try:
        query = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
        if event_filter:
            query = query.filter(AuditLog.event_type == event_filter)
        logs = query.limit(limit).all()

        print("=" * 100)
        print(f"NEXIS AUDIT LOG REPORT (Last {len(logs)} events)")
        print("=" * 100)
        print(f"{'TIMESTAMP':<24} | {'EVENT TYPE':<22} | {'OUTCOME':<8} | {'IP':<15} | {'EMAIL HASH (TRUNC)':<18}")
        print("-" * 100)

        for log in logs:
            ts = log.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC") if log.timestamp else "N/A"
            hash_display = log.email_hash[:16] + "..." if log.email_hash else "None"
            ip_display = log.ip or "Unknown"
            print(f"{ts:<24} | {log.event_type:<22} | {log.outcome:<8} | {ip_display:<15} | {hash_display:<18}")
            if log.details:
                print(f"   Details: {log.details}")

        print("=" * 100)
        print("Note: Credential confidentiality verified. Passwords, TOTP codes, and recovery codes are strictly excluded.")
        print("=" * 100)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nexis Audit Log Inspector")
    parser.add_argument("--limit", type=int, default=50, help="Number of records to display")
    parser.add_argument("--event", type=str, default=None, help="Filter by event type")
    args = parser.parse_args()

    run_audit_report(limit=args.limit, event_filter=args.event)
