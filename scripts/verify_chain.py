#!/usr/bin/env python3
"""
Standalone Tamper-Evident Audit Chain Verifier.
Shares ZERO code with the Vouch application runtime.
Connects directly to PostgreSQL, reads the audit_log table,
and independently recalculates every SHA-256 block hash from genesis to head.
"""

import sys
import os
import json
import hashlib
import asyncio

try:
    import asyncpg
except ImportError:
    print("Error: asyncpg is required. Install via `pip install asyncpg`.")
    sys.exit(1)

GENESIS_HASH = "0" * 64


def canonical_json_dumps(payload) -> str:
    """Formats JSON canonically (keys sorted, no spaces) matching RFC-8785 principles."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


async def verify_chain_independent(db_url: str):
    print("=" * 70)
    print(" VOUCH: STANDALONE CRYPTOGRAPHIC AUDIT LOG VERIFIER")
    print("=" * 70)

    # Clean db_url for asyncpg
    clean_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    print(f"[*] Target Database: {clean_url.split('@')[-1]}")

    conn = await asyncpg.connect(clean_url)
    try:
        rows = await conn.fetch("SELECT seq, prev_hash, hash, event_type, payload_json, ts FROM audit_log ORDER BY seq ASC;")
        total_blocks = len(rows)
        print(f"[*] Retrieved {total_blocks} audit log blocks.")
        print("-" * 70)

        if total_blocks == 0:
            print("[INFO] Audit log is empty (Genesis state). Chain is valid.")
            return True

        expected_prev = GENESIS_HASH

        for r in rows:
            seq = r["seq"]
            prev_hash = r["prev_hash"]
            stored_hash = r["hash"]
            event_type = r["event_type"]
            raw_payload = r["payload_json"]

            payload_dict = json.loads(raw_payload) if isinstance(raw_payload, str) else dict(raw_payload)

            # Check sequence link
            if prev_hash != expected_prev:
                print(f"[FAIL] CHAIN BROKEN at Block #{seq}!")
                print(f"       Expected prev_hash: {expected_prev}")
                print(f"       Found prev_hash:    {prev_hash}")
                return False

            # Recalculate block hash
            canonical_body = canonical_json_dumps(payload_dict)
            hasher = hashlib.sha256()
            hasher.update(f"{prev_hash}:{event_type}:{canonical_body}".encode("utf-8"))
            computed_hash = hasher.hexdigest()

            if computed_hash != stored_hash:
                print(f"[FAIL] TAMPERING DETECTED at Block #{seq} ({event_type})!")
                print(f"       Stored hash:   {stored_hash}")
                print(f"       Computed hash: {computed_hash}")
                return False

            print(f"  [OK] Block #{seq:03d} | {event_type:<32} | {stored_hash[:16]}...")
            expected_prev = stored_hash

        print("-" * 70)
        print(f" [PASSED] ALL {total_blocks} BLOCKS CRYPTOGRAPHICALLY VALID.")
        print(f" Head Hash: {expected_prev}")
        print("=" * 70)
        return True

    finally:
        await conn.close()


if __name__ == "__main__":
    db_conn = os.environ.get("DATABASE_URL", "postgresql://postgres:root@localhost:5432/vouch_db")
    success = asyncio.run(verify_chain_independent(db_conn))
    sys.exit(0 if success else 1)
