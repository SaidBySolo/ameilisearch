from typing import Any, Callable, Coroutine
from ameilisearch.index import Index

IndexMaker = Callable[..., Coroutine[Any, Any, Index]]