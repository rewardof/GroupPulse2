"""
Telegram Account Repository

Specialized queries for telegram accounts.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import TelegramAccount
from src.database.repositories.base import BaseRepository


class AccountRepository(BaseRepository[TelegramAccount]):
    """Repository for Telegram account operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(TelegramAccount, session)

    async def get_by_user_id(self, user_id: int) -> Optional[TelegramAccount]:
        """
        Get account by user ID (one account per user).

        Args:
            user_id: User ID

        Returns:
            Optional[TelegramAccount]: Account or None
        """
        result = await self.session.execute(
            select(TelegramAccount).where(TelegramAccount.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone_number: str) -> Optional[TelegramAccount]:
        """
        Get account by phone number.

        Args:
            phone_number: Phone number

        Returns:
            Optional[TelegramAccount]: Account or None
        """
        result = await self.session.execute(
            select(TelegramAccount).where(TelegramAccount.phone_number == phone_number)
        )
        return result.scalar_one_or_none()

    async def get_active_accounts(self) -> List[TelegramAccount]:
        """
        Get all active and authorized accounts.

        Returns:
            List[TelegramAccount]: List of active accounts
        """
        result = await self.session.execute(
            select(TelegramAccount).where(
                TelegramAccount.is_active == True,
                TelegramAccount.is_authorized == True
            )
        )
        return list(result.scalars().all())

    async def update_flood_wait(
        self,
        account_id: int,
        wait_until: datetime
    ) -> Optional[TelegramAccount]:
        """
        Update flood wait timestamp.

        Args:
            account_id: Account ID
            wait_until: Flood wait expiration datetime

        Returns:
            Optional[TelegramAccount]: Updated account or None
        """
        return await self.update(account_id, flood_wait_until=wait_until)

    async def clear_flood_wait(self, account_id: int) -> Optional[TelegramAccount]:
        """
        Clear flood wait.

        Args:
            account_id: Account ID

        Returns:
            Optional[TelegramAccount]: Updated account or None
        """
        return await self.update(account_id, flood_wait_until=None)

    async def increment_messages_sent(self, account_id: int) -> None:
        """
        Increment messages sent today counter.

        Args:
            account_id: Account ID
        """
        await self.session.execute(
            update(TelegramAccount)
            .where(TelegramAccount.id == account_id)
            .values(
                messages_sent_today=TelegramAccount.messages_sent_today + 1,
                last_message_at=datetime.utcnow()
            )
        )
        await self.session.flush()
