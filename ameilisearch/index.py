from datetime import datetime
from time import sleep
from types import TracebackType
from typing import Any, Dict, Generator, List, Optional, Type, Union
from urllib.parse import urlencode

from aiohttp.client_reqrep import ClientResponse

from ameilisearch._httprequests import HttpRequests
from ameilisearch.config import Config
from ameilisearch.errors import MeiliSearchApiError, MeiliSearchTimeoutError


# pylint: disable=too-many-public-methods
class Index:
    """
    Indexes routes wrapper.
    Index class gives access to all indexes routes and child routes (inherited).
    https://docs.meilisearch.com/reference/api/indexes.html
    """

    def __init__(
        self,
        config: Config,
        uid: str,
        primary_key: Optional[str] = None,
        created_at: Optional[Union[datetime, str]] = None,
        updated_at: Optional[Union[datetime, str]] = None,
    ) -> None:
        """
        Parameters
        ----------
        config:
            Config object containing permission and location of MeiliSearch.
        uid:
            UID of the index on which to perform the index actions.
        primary_key:
            Primary-key of the index.
        """
        self.config = config
        self.http = HttpRequests(config)
        self.uid = uid
        self.primary_key = primary_key
        self.created_at = self._iso_to_date_time(created_at)
        self.updated_at = self._iso_to_date_time(updated_at)

    async def close(self) -> None:
        """Close client session"""
        if self.http.session and not self.http.session.closed:
            await self.http.session.close()

    async def delete(self) -> ClientResponse:
        """Delete the index.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """

        return await self.http.delete(f"{self.config.paths.index}/{self.uid}")

    async def delete_if_exists(self) -> bool:
        """Deletes the index if it already exists
        Returns
        --------
        Returns True if an index was deleted or False if not
        Raises
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        try:
            await self.delete()
            return True
        except MeiliSearchApiError as error:
            if error.code != "index_not_found":
                raise error
            return False

    async def update(self, primary_key: str) -> "Index":
        """Update the index primary-key.
        Parameters
        ----------
        primary_key:
            The primary key to use for the index.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        payload = {"primaryKey": primary_key}
        response = await self.http.put(f"{self.config.paths.index}/{self.uid}", payload)
        self.primary_key = response["primaryKey"]
        self.created_at = self._iso_to_date_time(response["createdAt"])
        self.updated_at = self._iso_to_date_time(response["updatedAt"])
        return self

    async def fetch_info(self) -> "Index":
        """Fetch the info of the index.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        index_dict = await self.http.get(f"{self.config.paths.index}/{self.uid}")
        self.primary_key = index_dict["primaryKey"]
        self.created_at = self._iso_to_date_time(index_dict["createdAt"])
        self.updated_at = self._iso_to_date_time(index_dict["updatedAt"])
        return self

    async def get_primary_key(self) -> Optional[str]:
        """Get the primary key.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return (await self.fetch_info()).primary_key

    @classmethod
    async def create(
        cls, config: Config, uid: str, options: Optional[Dict[str, Any]] = None
    ) -> "Index":
        """Create the index.
        Parameters
        ----------
        uid:
            UID of the index.
        options:
            Options passed during index creation (ex: { 'primaryKey': 'name' }).
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        if options is None:
            options = {}
        payload = {**options, "uid": uid}
        index_dict = await HttpRequests(config).post(config.paths.index, payload)

        return cls(config, index_dict["uid"], index_dict["primaryKey"])

    async def get_all_update_status(self) -> List[Dict[str, Any]]:
        """Get all update status
        Returns
        -------
        update:
            List of all enqueued, processing, processed or failed actions of the index.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.get(
            f"{self.config.paths.index}/{self.uid}/{self.config.paths.update}"
        )

    async def get_update_status(self, update_id: int) -> Dict[str, Any]:
        """Get one update status
        Parameters
        ----------
        update_id:
            identifier of the update to retrieve
        Returns
        -------
        update:
            A Dictionary containing the details of the update status.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.get(
            f"{self.config.paths.index}/{self.uid}/{self.config.paths.update}/{update_id}"
        )

    async def wait_for_pending_update(
        self,
        update_id: int,
        timeout_in_ms: int = 5000,
        interval_in_ms: int = 50,
    ) -> Dict[str, Any]:
        """Wait until MeiliSearch processes an update, and get its status.
        Parameters
        ----------
        update_id:
            identifier of the update to retrieve
        timeout_in_ms (optional):
            time the method should wait before raising a MeiliSearchTimeoutError
        interval_in_ms (optional):
            time interval the method should wait (sleep) between requests
        Returns
        -------
        update:
            Dictionary containing the details of the processed update status.
        Raises
        ------
        MeiliSearchTimeoutError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        start_time = datetime.now()
        elapsed_time = 0.0
        while elapsed_time < timeout_in_ms:
            get_update = await self.get_update_status(update_id)

            if (
                get_update["status"] != "enqueued"
                and get_update["status"] != "processing"
            ):
                return get_update
            sleep(interval_in_ms / 1000)
            time_delta = datetime.now() - start_time
            elapsed_time = time_delta.seconds * 1000 + time_delta.microseconds / 1000
        raise MeiliSearchTimeoutError(
            f"timeout of ${timeout_in_ms}ms has exceeded on process ${update_id} when waiting for pending update to resolve."
        )

    async def get_stats(self) -> Dict[str, Any]:
        """Get stats of the index.
        Get information about the number of documents, field frequencies, ...
        https://docs.meilisearch.com/reference/api/stats.html
        Returns
        -------
        stats:
            Dictionary containing stats about the given index.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.get(
            f"{self.config.paths.index}/{self.uid}/{self.config.paths.stat}"
        )

    async def search(
        self, query: str, opt_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Search in the index.
        Parameters
        ----------
        query:
            String containing the searched word(s)
        opt_params (optional):
            Dictionary containing optional query parameters
            https://docs.meilisearch.com/reference/api/search.html#search-in-an-index
        Returns
        -------
        results:
            Dictionary with hits, offset, limit, processingTime and initial query
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        if opt_params is None:
            opt_params = {}
        body = {"q": query, **opt_params}
        return await self.http.post(
            f"{self.config.paths.index}/{self.uid}/{self.config.paths.search}",
            body=body,
        )

    async def get_document(self, document_id: str) -> Dict[str, Any]:
        """Get one document with given document identifier.
        Parameters
        ----------
        document_id:
            Unique identifier of the document.
        Returns
        -------
        document:
            Dictionary containing the documents information.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.get(
            f"{self.config.paths.index}/{self.uid}/{self.config.paths.document}/{document_id}"
        )

    async def get_documents(
        self, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get a set of documents from the index.
        Parameters
        ----------
        parameters (optional):
            parameters accepted by the get documents route: https://docs.meilisearch.com/reference/api/documents.html#get-all-documents
        Returns
        -------
        document:
            List of dictionaries containing the documents information.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        if parameters is None:
            parameters = {}
        return await self.http.get(
            f"{self.config.paths.index}/{self.uid}/{self.config.paths.document}?{urlencode(parameters)}"
        )

    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        primary_key: Optional[str] = None,
    ) -> Dict[str, int]:
        """Add documents to the index.
        Parameters
        ----------
        documents:
            List of documents. Each document should be a dictionary.
        primary_key (optional):
            The primary-key used in index. Ignored if already set up.
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        url = self._build_url(primary_key)
        return await self.http.post(url, documents)

    async def add_documents_in_batches(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 1000,
        primary_key: Optional[str] = None,
    ) -> List[Dict[str, int]]:
        """Add documents to the index in batches.
        Parameters
        ----------
        documents:
            List of documents. Each document should be a dictionary.
        batch_size (optional):
            The number of documents that should be included in each batch. Default = 1000
        primary_key (optional):
            The primary-key used in index. Ignored if already set up.
        Returns
        -------
        update:
            List of dictionaries containing an update ids to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request.
            MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """

        update_ids: List[Any] = []

        for document_batch in self._batch(documents, batch_size):
            update_id = await self.add_documents(document_batch, primary_key)
            update_ids.append(update_id)

        return update_ids

    async def add_documents_json(
        self,
        str_documents: str,
        primary_key: Optional[str] = None,
    ) -> Dict[str, int]:
        """Add string documents from JSON file to the index.
        Parameters
        ----------
        str_documents:
            String of document from a JSON file.
        primary_key (optional):
            The primary-key used in index. Ignored if already set up.
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.add_documents_raw(
            str_documents, primary_key, "application/json"
        )

    async def add_documents_csv(
        self,
        str_documents: str,
        primary_key: Optional[str] = None,
    ) -> Dict[str, int]:
        """Add string documents from a CSV file to the index.
        Parameters
        ----------
        str_documents:
            String of document from a CSV file.
        primary_key (optional):
            The primary-key used in index. Ignored if already set up.
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.add_documents_raw(str_documents, primary_key, "text/csv")

    async def add_documents_ndjson(
        self,
        str_documents: str,
        primary_key: Optional[str] = None,
    ) -> Dict[str, int]:
        """Add string documents from a NDJSON file to the index.
        Parameters
        ----------
        str_documents:
            String of document from a NDJSON file.
        primary_key (optional):
            The primary-key used in index. Ignored if already set up.
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.add_documents_raw(
            str_documents, primary_key, "application/x-ndjson"
        )

    async def add_documents_raw(
        self,
        str_documents: str,
        primary_key: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, int]:
        """Add string documents to the index.
        Parameters
        ----------
        str_documents:
            String of document.
        primary_key (optional):
            The primary-key used in index. Ignored if already set up.
        type:
            The type of document. Type available: 'csv', 'json', 'jsonl'
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        url = self._build_url(primary_key)
        return await self.http.post(url, str_documents, content_type)

    async def update_documents(
        self, documents: List[Dict[str, Any]], primary_key: Optional[str] = None
    ) -> Dict[str, int]:
        """Update documents in the index.
        Parameters
        ----------
        documents:
            List of documents. Each document should be a dictionary.
        primary_key (optional):
            The primary-key used in index. Ignored if already set up
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        url = self._build_url(primary_key)
        return await self.http.put(url, documents)

    async def update_documents_in_batches(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 1000,
        primary_key: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Update documents to the index in batches.
        Parameters
        ----------
        documents:
            List of documents. Each document should be a dictionary.
        batch_size (optional):
            The number of documents that should be included in each batch. Default = 1000
        primary_key (optional):
            The primary-key used in index. Ignored if already set up.
        Returns
        -------
        update:
            List of dictionaries containing an update ids to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request.
            MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """

        update_ids: List[Any] = []

        for document_batch in self._batch(documents, batch_size):
            update_id = self.update_documents(document_batch, primary_key)
            update_ids.append(update_id)

        return update_ids

    async def delete_document(self, document_id: str) -> Dict[str, Any]:
        """Delete one document from the index.
        Parameters
        ----------
        document_id:
            Unique identifier of the document.
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.delete(
            f"{self.config.paths.index}/{self.uid}/{self.config.paths.document}/{document_id}"
        )

    async def delete_documents(self, ids: List[str]) -> Dict[str, int]:
        """Delete multiple documents from the index.
        Parameters
        ----------
        list:
            List of unique identifiers of documents.
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.post(
            f"{self.config.paths.index}/{self.uid}/{self.config.paths.document}/delete-batch",
            ids,
        )

    async def delete_all_documents(self) -> Dict[str, int]:
        """Delete all documents from the index.
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.delete(
            f"{self.config.paths.index}/{self.uid}/{self.config.paths.document}"
        )

    # GENERAL SETTINGS ROUTES

    async def get_settings(self) -> Dict[str, Any]:
        """Get settings of the index.
        https://docs.meilisearch.com/reference/api/settings.html
        Returns
        -------
        settings
            Dictionary containing the settings of the index.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.get(
            f"{self.config.paths.index}/{self.uid}/{self.config.paths.setting}"
        )

    async def update_settings(self, body: Dict[str, Any]) -> Dict[str, int]:
        """Update settings of the index.
        https://docs.meilisearch.com/reference/api/settings.html#update-settings
        Parameters
        ----------
        body:
            Dictionary containing the settings of the index.
            More information:
            https://docs.meilisearch.com/reference/api/settings.html#update-settings
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.post(
            f"{self.config.paths.index}/{self.uid}/{self.config.paths.setting}", body
        )

    async def reset_settings(self) -> Dict[str, int]:
        """Reset settings of the index to default values.
        https://docs.meilisearch.com/reference/api/settings.html#reset-settings
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.delete(
            f"{self.config.paths.index}/{self.uid}/{self.config.paths.setting}"
        )

    # RANKING RULES SUB-ROUTES

    async def get_ranking_rules(self) -> List[str]:
        """
        Get ranking rules of the index.
        Returns
        -------
        settings: list
            List containing the ranking rules of the index.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.get(
            self.__settings_url_for(self.config.paths.ranking_rules)
        )

    async def update_ranking_rules(self, body: List[str]) -> Dict[str, int]:
        """
        Update ranking rules of the index.
        Parameters
        ----------
        body:
            List containing the ranking rules.
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.post(
            self.__settings_url_for(self.config.paths.ranking_rules), body
        )

    async def reset_ranking_rules(self) -> Dict[str, int]:
        """Reset ranking rules of the index to default values.
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.delete(
            self.__settings_url_for(self.config.paths.ranking_rules),
        )

    # DISTINCT ATTRIBUTE SUB-ROUTES

    async def get_distinct_attribute(self) -> Optional[str]:
        """
        Get distinct attribute of the index.
        Returns
        -------
        settings:
            String containing the distinct attribute of the index. If no distinct attribute None is returned.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.get(
            self.__settings_url_for(self.config.paths.distinct_attribute)
        )

    async def update_distinct_attribute(self, body: Dict[str, Any]) -> Dict[str, int]:
        """
        Update distinct attribute of the index.
        Parameters
        ----------
        body:
            String containing the distinct attribute.
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.post(
            self.__settings_url_for(self.config.paths.distinct_attribute), body
        )

    async def reset_distinct_attribute(self) -> Dict[str, int]:
        """Reset distinct attribute of the index to default values.
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.delete(
            self.__settings_url_for(self.config.paths.distinct_attribute),
        )

    # SEARCHABLE ATTRIBUTES SUB-ROUTES

    async def get_searchable_attributes(self) -> List[str]:
        """
        Get searchable attributes of the index.
        Returns
        -------
        settings:
            List containing the searchable attributes of the index.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.get(
            self.__settings_url_for(self.config.paths.searchable_attributes)
        )

    async def update_searchable_attributes(self, body: List[str]) -> Dict[str, int]:
        """
        Update searchable attributes of the index.
        Parameters
        ----------
        body:
            List containing the searchable attributes.
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.post(
            self.__settings_url_for(self.config.paths.searchable_attributes), body
        )

    async def reset_searchable_attributes(self) -> Dict[str, int]:
        """Reset searchable attributes of the index to default values.
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.delete(
            self.__settings_url_for(self.config.paths.searchable_attributes),
        )

    # DISPLAYED ATTRIBUTES SUB-ROUTES

    async def get_displayed_attributes(self) -> List[str]:
        """
        Get displayed attributes of the index.
        Returns
        -------
        settings:
            List containing the displayed attributes of the index.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.get(
            self.__settings_url_for(self.config.paths.displayed_attributes)
        )

    async def update_displayed_attributes(self, body: List[str]) -> Dict[str, int]:
        """
        Update displayed attributes of the index.
        Parameters
        ----------
        body:
            List containing the displayed attributes.
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.post(
            self.__settings_url_for(self.config.paths.displayed_attributes), body
        )

    async def reset_displayed_attributes(self) -> Dict[str, int]:
        """Reset displayed attributes of the index to default values.
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.delete(
            self.__settings_url_for(self.config.paths.displayed_attributes),
        )

    # STOP WORDS SUB-ROUTES

    async def get_stop_words(self) -> List[str]:
        """
        Get stop words of the index.
        Returns
        -------
        settings:
            List containing the stop words of the index.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.get(
            self.__settings_url_for(self.config.paths.stop_words)
        )

    async def update_stop_words(self, body: List[str]) -> Dict[str, int]:
        """
        Update stop words of the index.
        Parameters
        ----------
        body: list
            List containing the stop words.
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.post(
            self.__settings_url_for(self.config.paths.stop_words), body
        )

    async def reset_stop_words(self) -> Dict[str, int]:
        """Reset stop words of the index to default values.
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.delete(
            self.__settings_url_for(self.config.paths.stop_words),
        )

    # SYNONYMS SUB-ROUTES

    async def get_synonyms(self) -> Dict[str, List[str]]:
        """
        Get synonyms of the index.
        Returns
        -------
        settings: dict
            Dictionary containing the synonyms of the index.
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.get(self.__settings_url_for(self.config.paths.synonyms))

    async def update_synonyms(self, body: Dict[str, List[str]]) -> Dict[str, int]:
        """
        Update synonyms of the index.
        Parameters
        ----------
        body: dict
            Dictionary containing the synonyms.
        Returns
        -------
        update: dict
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.post(
            self.__settings_url_for(self.config.paths.synonyms), body
        )

    async def reset_synonyms(self) -> Dict[str, int]:
        """Reset synonyms of the index to default values.
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.delete(
            self.__settings_url_for(self.config.paths.synonyms),
        )

    # FILTERABLE ATTRIBUTES SUB-ROUTES

    async def get_filterable_attributes(self) -> List[str]:
        """
        Get filterable attributes of the index.
        Returns
        -------
        settings:
            List containing the filterable attributes of the index
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.get(
            self.__settings_url_for(self.config.paths.filterable_attributes)
        )

    async def update_filterable_attributes(self, body: List[str]) -> Dict[str, int]:
        """
        Update filterable attributes of the index.
        Parameters
        ----------
        body:
            List containing the filterable attributes.
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.post(
            self.__settings_url_for(self.config.paths.filterable_attributes), body
        )

    async def reset_filterable_attributes(self) -> Dict[str, int]:
        """Reset filterable attributes of the index to default values.
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.delete(
            self.__settings_url_for(self.config.paths.filterable_attributes),
        )

    # SORTABLE ATTRIBUTES SUB-ROUTES

    async def get_sortable_attributes(self) -> List[str]:
        """
        Get sortable attributes of the index.
        Returns
        -------
        settings:
            List containing the sortable attributes of the index
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.get(
            self.__settings_url_for(self.config.paths.sortable_attributes)
        )

    async def update_sortable_attributes(self, body: List[str]) -> Dict[str, int]:
        """
        Update sortable attributes of the index.
        Parameters
        ----------
        body:
            List containing the sortable attributes.
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.post(
            self.__settings_url_for(self.config.paths.sortable_attributes), body
        )

    async def reset_sortable_attributes(self) -> Dict[str, int]:
        """Reset sortable attributes of the index to default values.
        Returns
        -------
        update:
            Dictionary containing an update id to track the action:
            https://docs.meilisearch.com/reference/api/updates.html#get-an-update-status
        Raises
        ------
        MeiliSearchApiError
            An error containing details about why MeiliSearch can't process your request. MeiliSearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return await self.http.delete(
            self.__settings_url_for(self.config.paths.sortable_attributes),
        )

    @staticmethod
    def _batch(
        documents: List[Dict[str, Any]], batch_size: int
    ) -> Generator[List[Dict[str, Any]], None, None]:
        total_len = len(documents)
        for i in range(0, total_len, batch_size):
            yield documents[i : i + batch_size]

    @staticmethod
    def _iso_to_date_time(
        iso_date: Optional[Union[datetime, str]]
    ) -> Optional[datetime]:
        """
        MeiliSearch returns the date time information in iso format. Python's implementation of
        datetime can only handle up to 6 digits in microseconds, however MeiliSearch sometimes
        returns more digits than this in the micosecond sections so when that happens this method
        reduces the number of microseconds so Python can handle it. If the value passed is either
        None or already in datetime format the original value is returned.
        """
        if not iso_date:
            return None

        if isinstance(iso_date, datetime):
            return iso_date

        try:
            return datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            split = iso_date.split(".")
            reduce = len(split[1]) - 6
            reduced = f"{split[0]}.{split[1][:-reduce]}Z"
            return datetime.strptime(reduced, "%Y-%m-%dT%H:%M:%S.%fZ")

    def __settings_url_for(self, sub_route: str) -> str:
        return f"{self.config.paths.index}/{self.uid}/{self.config.paths.setting}/{sub_route}"

    def _build_url(
        self,
        primary_key: Optional[str] = None,
    ) -> str:
        if primary_key is None:
            return f"{self.config.paths.index}/{self.uid}/{self.config.paths.document}"
        primary_key = urlencode({"primaryKey": primary_key})
        return f"{self.config.paths.index}/{self.uid}/{self.config.paths.document}?{primary_key}"

    async def __aenter__(self) -> "Index":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ):
        if self.http.session:
            await self.http.session.close()
