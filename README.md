# ameiliSearch

> Asynchronous MeiliSearch API client that is **100% compatible** with [MeiliSearch Python](https://github.com/meilisearch/meilisearch-python)

upstream commit hash: ``38d862efb55dc68b0c52b509722cfa4c519d156a``

## Getting Started

### Add Documents

```py
import asyncio
import ameilisearch


async def main():
    async with ameilisearch.Client("http://127.0.0.1:7700", 'masterKey') as client:
        index = await client.index("movies")

    documents = [
        { 'id': 1, 'title': 'Carol', 'genres': ['Romance', 'Drama'] },
        { 'id': 2, 'title': 'Wonder Woman', 'genres': ['Action', 'Adventure'] },
        { 'id': 3, 'title': 'Life of Pi', 'genres': ['Adventure', 'Drama'] },
        { 'id': 4, 'title': 'Mad Max: Fury Road', 'genres': ['Adventure', 'Science Fiction'] },
        { 'id': 5, 'title': 'Moana', 'genres': ['Fantasy', 'Action']},
        { 'id': 6, 'title': 'Philadelphia', 'genres': ['Drama'] },
    ]

    # If the index 'movies' does not exist, MeiliSearch creates it when you first add the documents.
    async with index as index:
        index.add_documents(documents) # => { "updateId": 0 }

asyncio.get_event_loop().run_until_complete(main())

```

## Differences from synchronous clients

Existing API clients worked with ``requests``.

ameilisearch works with ``aiohttp``.

Users need to manage client sessions.

The http instance is in two places: ``Client`` and ``Index``.

Use the ``async with`` syntax to close the session immediately after use, or must close the session using ``await :client_or_index_instance:.http.session.close()`` after using it all.
