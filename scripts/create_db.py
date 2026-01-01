"""
Database Table Creation Script

Simple script to create all database tables.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database.connection import get_async_engine
from src.database.models import Base


async def create_tables():
    """Create all database tables."""
    print("Creating database tables...")

    try:
        engine = get_async_engine()

        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)

        print("✓ Database tables created successfully!")
        print("\nCreated tables:")
        print("  - users")
        print("  - telegram_accounts")
        print("  - groups")
        print("  - keywords")
        print("  - forwarding_rules")
        print("  - message_log")

    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(create_tables())
