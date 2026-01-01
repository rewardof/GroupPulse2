"""
Forwarding Rule Repository

Specialized queries for forwarding rules.
"""

from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import ForwardingRule
from src.database.repositories.base import BaseRepository


class RuleRepository(BaseRepository[ForwardingRule]):
    """Repository for forwarding rule operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(ForwardingRule, session)

    async def get_active_rules_by_user(self, user_id: int) -> List[ForwardingRule]:
        """
        Get all active rules for a user, sorted by priority (descending).

        Args:
            user_id: User ID

        Returns:
            List[ForwardingRule]: List of active rules
        """
        result = await self.session.execute(
            select(ForwardingRule)
            .where(
                and_(
                    ForwardingRule.user_id == user_id,
                    ForwardingRule.is_active == True
                )
            )
            .order_by(ForwardingRule.priority.desc())
        )
        return list(result.scalars().all())

    async def get_rules_for_source_group(
        self,
        user_id: int,
        source_group_id: int
    ) -> List[ForwardingRule]:
        """
        Get active rules that apply to a specific source group.

        Args:
            user_id: User ID
            source_group_id: Source group ID

        Returns:
            List[ForwardingRule]: List of matching rules
        """
        result = await self.session.execute(
            select(ForwardingRule)
            .where(
                and_(
                    ForwardingRule.user_id == user_id,
                    ForwardingRule.is_active == True,
                    ForwardingRule.source_group_ids.contains([source_group_id])
                )
            )
            .order_by(ForwardingRule.priority.desc())
        )
        return list(result.scalars().all())

    async def toggle_rule(self, rule_id: int) -> Optional[ForwardingRule]:
        """
        Toggle rule active status.

        Args:
            rule_id: Rule ID

        Returns:
            Optional[ForwardingRule]: Updated rule or None
        """
        rule = await self.get(rule_id)
        if rule:
            return await self.update(rule_id, is_active=not rule.is_active)
        return None

    async def increment_stats(
        self,
        rule_id: int,
        processed: int = 0,
        forwarded: int = 0,
        skipped: int = 0
    ) -> None:
        """
        Increment rule statistics.

        Args:
            rule_id: Rule ID
            processed: Number processed
            forwarded: Number forwarded
            skipped: Number skipped
        """
        rule = await self.get(rule_id)
        if rule:
            await self.update(
                rule_id,
                total_processed=rule.total_processed + processed,
                total_forwarded=rule.total_forwarded + forwarded,
                total_skipped=rule.total_skipped + skipped
            )
