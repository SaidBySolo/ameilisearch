from types import TracebackType
from typing import Any, Dict, List, Optional, Type

from ameilisearch._httprequests import HttpRequests
from ameilisearch.config import Config
from ameilisearch.errors import MeiliSearchApiError, MeiliSearchError
from ameilisearch.index import Index


class Client:
    """
    A client for the MeiliSearch API
    A client instance is needed for every MeiliSearch API method to know the location of
    MeiliSearch and its permissions.
    """

    def __init__(
        self, url: str, apiKey: Optional[str] = None, timeout: Optional[int] = None
    ) -> None:
        """
        Parameters
        ----------
        url:
            The url to the MeiliSearch API (ex: http://localhost:7700)
        apiKey:
            The optional API key for MeiliSearch
        """
        self.config = Config(url, apiKey, timeout=timeout)

        self.http = HttpRequests(self.config)

    async def close(self) -> None:
        """Close client session"""
        if self.http.session and not self.http.session.closed:
            await self.http.session.close()

    async def create_index(
        self, uid: str, options: Optional[Dict[str, Any]] = None
    ) -> Index:
        """Create an index.
        Parameters
        ----------
        uid: str
            UID of the index.
        options (optional): dict
            Options passed during index creation (ex: primaryKey).
        Returns
        -------
        index : Index
            An instance of Index containing the information of the newly created index.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await Index.create(self.config, uid, options)

    async def delete_index_if_exists(self, uid: str) -> bool:
        """Deletes an index if it already exists
        Parameters
        ----------
        uid:
            UID of the index.
        Returns
        --------
        Returns True if an index was deleted or False if not
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """

        try:
            await self.http.delete(f"{self.config.paths.index}/{uid}")
            return True
        except MeiliSearchApiError as error:
            if error.code != "index_not_found":
                raise error
            return False

    async def get_indexes(self) -> List[Index]:
        """Get all indexes.
        Returns
        -------
        indexes:
            List of Index instances.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        response = await self.http.get(self.config.paths.index)

        return [
            Index(
                self.config,
                index["uid"],
                index["primaryKey"],
                index["createdAt"],
                index["updatedAt"],
            )
            for index in response
        ]

    async def get_raw_indexes(self) -> List[Dict[str, Any]]:
        """Get all indexes in dictionary format.
        Returns
        -------
        indexes:
            List of indexes in dictionary format. (e.g [{ 'uid': 'movies' 'primaryKey': 'objectID' }])
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.get(self.config.paths.index)

    async def get_index(self, uid: str) -> Index:
        """Get the index.
        This index should already exist.
        Parameters
        ----------
        uid:
            UID of the index.
        Returns
        -------
        index:
            An Index instance containing the information of the fetched index.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await Index(self.config, uid).fetch_info()

    async def get_raw_index(self, uid: str) -> Dict[str, Any]:
        """Get the index as a dictionary.
        This index should already exist.
        Parameters
        ----------
        uid:
            UID of the index.
        Returns
        -------
        index:
            An index in dictionary format. (e.g { 'uid': 'movies' 'primaryKey': 'objectID' })
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.get(f"{self.config.paths.index}/{uid}")

    def index(self, uid: str) -> Index:
        """Create a local reference to an index identified by UID, without doing an HTTP call.
        Calling this method doesn't create an index in the MeiliSearch instance, but grants access to all the other methods in the Index class.
        Parameters
        ----------
        uid:
            UID of the index.
        Returns
        -------
        index:
            An Index instance.
        """
        if uid is not None:
            return Index(self.config, uid=uid)
        raise Exception("The index UID should not be None")

    async def get_or_create_index(
        self, uid: str, options: Optional[Dict[str, Any]] = None
    ) -> Index:
        """Get an index, or create it if it doesn't exist.
        Parameters
        ----------
        uid:
            UID of the index
        options (optional): dict
            Options passed during index creation (ex: primaryKey)
        Returns
        -------
        index:
            An instance of Index containing the information of the retrieved or newly created index.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        try:
            index_instance = await self.get_index(uid)
        except MeiliSearchApiError as err:
            if err.code != "index_not_found":
                raise err
            index_instance = await self.create_index(uid, options)
        return index_instance

    async def get_all_stats(self) -> Dict[str, Any]:
        """Get all stats of MeiliSearch
        Get information about database size and all indexes
        https://docs.meilisearch.com/reference/api/stats.html
        Returns
        -------
        stats:
            Dictionary containing stats about your MeiliSearch instance.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.get(self.config.paths.stat)

    async def health(self) -> Dict[str, str]:
        """Get health of the MeiliSearch server.
        Returns
        -------
        health:
            Dictionary containing the status of the MeiliSearch instance.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.get(self.config.paths.health)

    async def is_healthy(self) -> bool:
        """Get health of the MeiliSearch server."""
        try:
            await self.health()
        except MeiliSearchError:
            return False
        return True

    async def get_keys(self) -> Dict[str, str]:
        """Get all keys.
        Get the public and private keys.
        Returns
        -------
        keys:
            Dictionary of keys and their information.
            https://docs.meilisearch.com/reference/api/keys.html#get-keys
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.get(self.config.paths.keys)

    async def get_version(self) -> Dict[str, str]:
        """Get version MeiliSearch
        Returns
        -------
        version:
            Information about the version of MeiliSearch.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.get(self.config.paths.version)

    async def version(self) -> Dict[str, str]:
        """Alias for get_version
        Returns
        -------
        version:
            Information about the version of MeiliSearch.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.get_version()

    async def create_dump(self) -> Dict[str, str]:
        """Trigger the creation of a MeiliSearch dump.
        Returns
        -------
        Dump:
            Information about the dump.
            https://docs.meilisearch.com/reference/api/dump.html#create-a-dump
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.post(self.config.paths.dumps)

    async def get_dump_status(self, uid: str) -> Dict[str, str]:
        """Retrieve the status of a MeiliSearch dump creation.
        Parameters
        ----------
        uid:
            UID of the dump.
        Returns
        -------
        Dump status:
            Information about the dump status.
            https://docs.meilisearch.com/reference/api/dump.html#get-dump-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.get(self.config.paths.dumps + "/" + str(uid) + "/status")

    async def __aenter__(self) -> "Client":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ):
        if self.http.session:
            await self.http.session.close()
