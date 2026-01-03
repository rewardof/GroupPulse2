#!/usr/bin/env python3
"""
Generate Telegram Session String

Run this once to generate session string, then copy it to listener.py
"""

import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = 28524826
API_HASH = "7f2ce73d335735fe428df68cd6de48db"


async def main():
    """Generate session string."""
    print("=" * 60)
    print("📱 Telegram Session Generator")
    print("=" * 60)

    client = TelegramClient(StringSession(), API_ID, API_HASH)

    await client.connect()

    if not await client.is_user_authorized():
        phone = input("\n📞 Enter phone number (with country code): ")
        await client.send_code_request(phone)

        code = input("🔐 Enter verification code: ")
        await client.sign_in(phone, code)

    # Get session string
    session_string = client.session.save()

    me = await client.get_me()

    print("\n" + "=" * 60)
    print(f"✅ Logged in as: {me.first_name} (@{me.username})")
    print("=" * 60)
    print("\n📋 SESSION STRING (copy to listener.py):")
    print("-" * 60)
    print(session_string)
    print("-" * 60)
    print("\nCopy this string to SESSION_STRING variable in listener.py")
    print("=" * 60)

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
