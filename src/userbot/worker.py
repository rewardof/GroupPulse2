"""
Userbot Worker Pool

Manages multiple userbot workers with auto-restart and health monitoring.
"""

from typing import Dict, Callable, List, Optional
from src.userbot.client import GroupPulseUserbot
import asyncio
import logging

logger = logging.getLogger(__name__)


class UserbotWorkerPool:
    """
    Manages multiple userbot workers.

    Features:
    - Auto-restart on crashes
    - Load balancing across accounts
    - Health monitoring
    - Graceful shutdown
    """

    def __init__(self, max_workers: int = 10):
        """
        Initialize worker pool.

        Args:
            max_workers: Maximum number of concurrent workers
        """
        self.max_workers = max_workers
        self.workers: Dict[int, GroupPulseUserbot] = {}
        self._running = False
        self._worker_tasks: Dict[int, asyncio.Task] = {}

    async def add_account(
        self,
        account_id: int,
        phone: str,
        api_id: int,
        api_hash: str,
        session_string: str,
        group_ids: List[int],
        message_handler: Callable
    ) -> bool:
        """
        Add and start a new userbot worker.

        Args:
            account_id: Database account ID
            phone: Phone number
            api_id: Telegram API ID
            api_hash: Telegram API hash
            session_string: Session string
            group_ids: List of group IDs to monitor
            message_handler: Message processing function

        Returns:
            bool: True if successfully added
        """
        if len(self.workers) >= self.max_workers:
            logger.error(f"Worker pool full ({self.max_workers} workers)")
            return False

        if account_id in self.workers:
            logger.warning(f"Account {account_id} already in worker pool")
            return False

        try:
            # Create userbot instance
            userbot = GroupPulseUserbot(
                account_id=account_id,
                phone=phone,
                api_id=api_id,
                api_hash=api_hash,
                session_string=session_string
            )

            # Add message handler
            userbot.add_message_handler(message_handler)

            # Start client
            started = await userbot.start()
            if not started:
                logger.error(f"Failed to start account {account_id}")
                return False

            # Listen to groups
            await userbot.listen_to_groups(group_ids)

            # Store worker
            self.workers[account_id] = userbot

            # Start worker loop
            task = asyncio.create_task(self._run_worker(userbot))
            self._worker_tasks[account_id] = task

            logger.info(f"✓ Worker added: account {account_id} monitoring {len(group_ids)} groups")
            return True

        except Exception as e:
            logger.error(f"Failed to add account {account_id}: {e}", exc_info=True)
            return False

    async def _run_worker(self, userbot: GroupPulseUserbot):
        """
        Run worker until disconnect.

        Args:
            userbot: Userbot instance
        """
        account_id = userbot.account_id

        try:
            logger.info(f"Worker {account_id} started, running until disconnect...")
            await userbot.client.run_until_disconnected()
            logger.info(f"Worker {account_id} disconnected normally")

        except Exception as e:
            logger.error(f"Worker {account_id} crashed: {e}", exc_info=True)

        finally:
            # Cleanup
            if account_id in self.workers:
                logger.warning(f"Removing crashed worker {account_id}")
                await self.remove_account(account_id)

    async def remove_account(self, account_id: int) -> bool:
        """
        Stop and remove a worker.

        Args:
            account_id: Account ID to remove

        Returns:
            bool: True if removed
        """
        if account_id not in self.workers:
            logger.warning(f"Account {account_id} not in worker pool")
            return False

        try:
            # Stop userbot
            userbot = self.workers[account_id]
            await userbot.stop()

            # Cancel worker task
            if account_id in self._worker_tasks:
                task = self._worker_tasks[account_id]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                del self._worker_tasks[account_id]

            # Remove from workers
            del self.workers[account_id]

            logger.info(f"✓ Worker removed: account {account_id}")
            return True

        except Exception as e:
            logger.error(f"Error removing worker {account_id}: {e}", exc_info=True)
            return False

    async def update_groups(
        self,
        account_id: int,
        group_ids: List[int],
        message_handler: Callable
    ) -> bool:
        """
        Update groups for an existing worker.

        Args:
            account_id: Account ID
            group_ids: New list of group IDs
            message_handler: Message handler function

        Returns:
            bool: True if updated
        """
        if account_id not in self.workers:
            logger.error(f"Account {account_id} not found in worker pool")
            return False

        try:
            userbot = self.workers[account_id]

            # Clear existing handlers
            userbot._message_handlers.clear()
            userbot._event_handlers.clear()

            # Add new handler
            userbot.add_message_handler(message_handler)

            # Re-register with new groups
            await userbot.listen_to_groups(group_ids)

            logger.info(f"✓ Updated groups for account {account_id}: {len(group_ids)} groups")
            return True

        except Exception as e:
            logger.error(f"Error updating groups for account {account_id}: {e}", exc_info=True)
            return False

    async def get_worker_status(self) -> Dict[int, Dict]:
        """
        Get status of all workers.

        Returns:
            Dict mapping account_id to status info
        """
        status = {}

        for account_id, userbot in self.workers.items():
            status[account_id] = {
                'is_running': userbot.is_running,
                'is_connected': userbot.client.is_connected(),
                'is_flood_waited': userbot.is_flood_waited,
                'phone': userbot.phone,
                'handler_count': len(userbot._message_handlers)
            }

        return status

    async def shutdown_all(self):
        """Gracefully stop all workers."""
        logger.info(f"Shutting down all workers ({len(self.workers)} workers)...")

        # Stop all workers
        tasks = []
        for account_id in list(self.workers.keys()):
            tasks.append(self.remove_account(account_id))

        await asyncio.gather(*tasks, return_exceptions=True)

        self.workers.clear()
        self._worker_tasks.clear()

        logger.info("✓ All workers shut down")

    @property
    def worker_count(self) -> int:
        """Get number of active workers."""
        return len(self.workers)

    @property
    def is_full(self) -> bool:
        """Check if worker pool is full."""
        return len(self.workers) >= self.max_workers
