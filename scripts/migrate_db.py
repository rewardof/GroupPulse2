#!/usr/bin/env python3
"""
Database Migration Script

Drops old tables and creates new schema.
WARNING: This will delete all existing data!
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from src.database.connection import get_async_engine
from src.database.models import Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate():
    """Drop all tables and recreate with new schema."""
    engine = get_async_engine()

    try:
        logger.info("🗑️  Dropping all existing tables...")

        async with engine.begin() as conn:
            # Drop all tables
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("✓ All tables dropped")

        logger.info("📋 Creating new tables...")

        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✓ All tables created")

        logger.info("=" * 60)
        logger.info("✅ Migration completed successfully!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Changes:")
        logger.info("  • Removed 'group_type' column from groups table")
        logger.info("  • Groups table now only stores destination groups")
        logger.info("  • account_id is now UNIQUE (one destination per account)")
        logger.info("  • Removed source_group_ids from forwarding_rules")
        logger.info("  • Removed destination_group_ids from forwarding_rules")
        logger.info("")
        logger.info("⚠️  All old data has been deleted!")
        logger.info("")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        await engine.dispose()


if __name__ == "__main__":
    print("=" * 60)
    print("⚠️  DATABASE MIGRATION WARNING ⚠️")
    print("=" * 60)
    print("")
    print("This will:")
    print("  1. DROP all existing tables")
    print("  2. DELETE all data (accounts, groups, keywords, rules)")
    print("  3. CREATE new tables with updated schema")
    print("")
    print("=" * 60)

    response = input("Are you sure you want to continue? (yes/no): ").strip().lower()

    if response != "yes":
        print("❌ Migration cancelled")
        sys.exit(0)

    print("")
    asyncio.run(migrate())
