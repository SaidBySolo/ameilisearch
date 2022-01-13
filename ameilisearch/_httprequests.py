import json
from typing import Any, Dict, List, Optional, Type, Union
from types import TracebackType
from aiohttp.client_reqrep import ClientResponse

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from aiohttp.client import ClientConnectionError, ClientResponseError, ClientSession
from aiohttp.client_exceptions import ServerTimeoutError

from ameilisearch.config import Config
from ameilisearch.errors import (
    MeiliSearchApiError,
    MeiliSearchCommunicationError,
    MeiliSearchTimeoutError,
)


class HttpRequests:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {self.config.api_key}",
        }
        self.session: Optional[ClientSession] = None

    async def send_request(
        self,
        method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
        path: str,
        body: Optional[
            Union[Dict[str, Any], List[Dict[str, Any]], List[str], str]
        ] = None,
        content_type: Optional[str] = None,
    ) -> Any:
        if not self.session or self.session.closed:
            self.session = ClientSession()
        if content_type:
            self.headers["Content-Type"] = content_type

        self.headers = {k: v for k, v in self.headers.items() if v is not None}
        try:
            request_path = self.config.url + "/" + path
            if isinstance(body, bytes):
                response = await self.session.request(
                    method,
                    request_path,
                    timeout=self.config.timeout,
                    headers=self.headers,
                    data=body,
                )
            else:
                response = await self.session.request(
                    method,
                    request_path,
                    timeout=self.config.timeout,
                    headers=self.headers,
                    data=json.dumps(body) if body else None,
                )
            return await self.__validate(response)

        except ServerTimeoutError as err:
            raise MeiliSearchTimeoutError(str(err)) from err
        except ClientConnectionError as err:
            raise MeiliSearchCommunicationError(str(err)) from err

    async def get(self, path: str) -> Any:
        return await self.send_request("GET", path)

    async def post(
        self,
        path: str,
        body: Optional[
            Union[Dict[str, Any], List[Dict[str, Any]], List[str], str]
        ] = None,
        content_type: Optional[str] = "application/json",
    ) -> Any:
        return await self.send_request("POST", path, body, content_type)

    async def patch(
        self,
        path: str,
        body: Optional[Union[Dict[str, Any], List[Dict[str, Any]], List[str], str]] = None,
        content_type: Optional[str] = 'application/json',
    ) -> Any:
        return self.send_request("PATCH", path, body, content_type)

    async def put(
        self,
        path: str,
        body: Optional[Union[Dict[str, Any], List[Dict[str, Any]], List[str]]] = None,
        content_type: Optional[str] = "application/json",
    ) -> Any:
        return await self.send_request("PUT", path, body, content_type)

    async def delete(
        self,
        path: str,
        body: Optional[Union[Dict[str, Any], List[Dict[str, Any]], List[str]]] = None,
    ) -> Any:
        return await self.send_request("DELETE", path, body)

    @staticmethod
    async def __to_json(content: bytes, request: ClientResponse) -> Any:
        if content == b"":
            return request
        return json.loads(content)

    @staticmethod
    async def __validate(request: ClientResponse) -> Any:
        content = await request.content.read()
        try:
            request.raise_for_status()
            return await HttpRequests.__to_json(content, request)
        except ClientResponseError as err:
            raise MeiliSearchApiError(str(err), content, request.status) from err

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ):
        if self.session:
            await self.session.close()
