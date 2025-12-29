import asyncio

from engines.chat.contracts import Contact
from engines.chat.service import transport_layer
from engines.chat.service.transport_layer import publish_message, subscribe_async
from engines.common.identity import RequestContext
from engines.realtime.timeline import InMemoryTimelineStore, set_timeline_store


def test_stream_replay_across_restart():
    async def _run():
        shared_storage: dict[str, list[dict]] = {}
        set_timeline_store(InMemoryTimelineStore(shared_storage))
        transport_layer.bus._impl = transport_layer.InMemoryBus()
        ctx = RequestContext(tenant_id="t_test", env="dev", mode="saas", project_id="p_demo")
        sender = Contact(id="u1")
        m1 = publish_message("thread-1", sender, "hello", context=ctx)
        publish_message("thread-1", sender, "world", context=ctx)

        # Simulate restart with fresh bus + store but shared durable data
        transport_layer.bus._impl = transport_layer.InMemoryBus()
        set_timeline_store(InMemoryTimelineStore(shared_storage))

        async def collect_messages(cursor, count):
            results = []
            async for msg in subscribe_async("thread-1", last_event_id=cursor, context=ctx):
                results.append(msg.text)
                if len(results) >= count:
                    break
            return results

        collector = asyncio.create_task(collect_messages(m1.id, 2))
        await asyncio.sleep(0)
        publish_message("thread-1", sender, "again", context=ctx)
        replay_and_live = await collector
        assert replay_and_live == ["world", "again"]

    asyncio.run(_run())
