from datetime import datetime
from asyncio import sleep

import pytest

from ameilisearch.client import Client


@pytest.mark.asyncio
# Waits until the end of the dump creation.
# Raises a TimeoutError if the `timeout_in_ms` is reached.
async def wait_for_dump_creation(
    client: Client,
    dump_uid: str,
    timeout_in_ms: float = 10000,
    interval_in_ms: float = 500,
):
    start_time = datetime.now()
    elapsed_time = 0
    while elapsed_time < timeout_in_ms:
        dump = await client.get_dump_status(dump_uid)
        if dump["status"] != "in_progress":
            return
        sleep(interval_in_ms / 1000)
        time_delta = datetime.now() - start_time
        elapsed_time = time_delta.seconds * 1000 + time_delta.microseconds / 1000
    raise TimeoutError
