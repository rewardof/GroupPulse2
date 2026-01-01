"""
Account Setup FSM States

Finite State Machine states for Telegram account setup flow.
"""

from aiogram.fsm.state import State, StatesGroup


class AccountSetupStates(StatesGroup):
    """FSM states for account setup flow."""

    # Account setup flow
    waiting_for_api_id = State()
    waiting_for_api_hash = State()
    waiting_for_phone = State()
    waiting_for_code = State()
    waiting_for_password = State()


class GroupSetupStates(StatesGroup):
    """FSM states for group management."""

    waiting_for_group_link = State()
    waiting_for_group_id = State()
    selecting_group_type = State()


class KeywordSetupStates(StatesGroup):
    """FSM states for keyword management."""

    waiting_for_keyword = State()
    waiting_for_keyword_type = State()


class RuleSetupStates(StatesGroup):
    """FSM states for rule creation."""

    waiting_for_rule_name = State()
    selecting_source_groups = State()
    selecting_destination_groups = State()
    selecting_keywords = State()
    configuring_conditions = State()
