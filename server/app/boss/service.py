from __future__ import annotations

import asyncio

from app.boss.feeds import FeedStore, fetch_feed
from app.boss.models import FeedPollResult
from app.boss.providers import auto_fanout_enabled, fanout_assessments


async def poll_feed_source(source_id: str, execute: bool = False) -> FeedPollResult:
    items = await fetch_feed(source_id)
    store = FeedStore()
    new_items = await asyncio.to_thread(store.remember_new, items)
    should_execute = execute and auto_fanout_enabled()

    provider_results = {}
    if should_execute:
        for item in new_items:
            provider_results[item.item_id] = await fanout_assessments(item)

    return FeedPollResult(
        source_id=source_id,
        fetched=len(items),
        new_items=new_items,
        executed=should_execute,
        provider_results=provider_results,
    )
