# pylint: disable=redefined-outer-name
import json
from typing import Any, List
from pytest import fixture
from ameilisearch.index import Index

from tests import common
import ameilisearch
from tests.types import IndexMaker


@fixture(scope="session")
async def client():
    client = ameilisearch.Client(common.BASE_URL, common.MASTER_KEY)
    yield client
    if client.http.session:
        if not client.http.session.closed:
            await client.http.session.close()


@fixture(autouse=True)
async def clear_indexes(client: ameilisearch.Client):
    """
    Auto-clears the indexes after each test function run.
    Makes all the test functions independent.
    """
    # Yields back to the test function.
    yield
    # Deletes all the indexes in the MeiliSearch instance.
    indexes = await client.get_indexes()
    for index in indexes:
        ind = await client.index(index.uid)
        await ind.delete()
        if ind.http.session:
            if not ind.http.session.closed:
                await ind.http.session.close()


@fixture(scope="function")
async def indexes_sample(client: ameilisearch.Client):
    indexes: List[Index] = []
    for index_args in common.INDEX_FIXTURE:
        index = await client.create_index(**index_args)  # type:ignore
        indexes.append(index)
    # Yields the indexes to the test to make them accessible.
    yield indexes


@fixture(scope="session")
def small_movies():
    """
    Runs once per session. Provides the content of small_movies.json.
    """
    with open("./datasets/small_movies.json", "r", encoding="utf-8") as movie_file:
        yield json.loads(movie_file.read())


@fixture(scope="session")
def small_movies_json_file():
    """
    Runs once per session. Provides the content of small_movies.json from read.
    """
    with open("./datasets/small_movies.json", "r", encoding="utf-8") as movie_json_file:
        return movie_json_file.read().encode("utf-8")


@fixture(scope="session")
def songs_csv():
    """
    Runs once per session. Provides the content of songs.csv from read..
    """
    with open("./datasets/songs.csv", "r", encoding="utf-8") as song_csv_file:
        return song_csv_file.read().encode("utf-8")


@fixture(scope="session")
def songs_ndjson():
    """
    Runs once per session. Provides the content of songs.ndjson from read..
    """
    with open("./datasets/songs.ndjson", "r", encoding="utf-8") as song_ndjson_file:
        return song_ndjson_file.read().encode("utf-8")


@fixture(scope="function")
def empty_index(client: ameilisearch.Client):
    async def index_maker(index_name: str = common.INDEX_UID):
        return await client.create_index(uid=index_name)

    return index_maker


@fixture(scope="function")
def index_with_documents(empty_index: IndexMaker, small_movies: List[Any]):
    async def index_maker(
        index_name: str = common.INDEX_UID, documents: List[Any] = small_movies
    ):
        index = await empty_index(index_name)
        response = await index.add_documents(documents)
        await index.wait_for_pending_update(response["updateId"])
        return index

    return index_maker
