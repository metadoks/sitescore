from __future__ import annotations
import argparse
from datetime import datetime, timezone
from uuid import uuid4
from .auth import ALL_SCOPES, provision_service_key
from .db_models import ConsumerModel
from .runtime import build_runtime


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision one SiteScore machine consumer service key")
    parser.add_argument("--name", required=True)
    parser.add_argument("--scope", action="append", dest="scopes", required=True, choices=sorted(ALL_SCOPES))
    args = parser.parse_args()
    runtime = build_runtime()
    with runtime.database.session() as session:
        with session.begin():
            consumer = ConsumerModel(
                consumer_id=uuid4(),
                name=args.name,
                active=True,
                created_at=datetime.now(timezone.utc),
            )
            session.add(consumer)
            session.flush()
            token = provision_service_key(
                session,
                consumer_id=consumer.consumer_id,
                scopes=set(args.scopes),
                pepper=runtime.settings.api_key_pepper,
            )
    print(token)
