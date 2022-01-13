import json


class MeiliSearchError(Exception):
    """Generic class for MeiliSearch error handling"""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        return f'MeiliSearchError. Error message: {self.message}'

class MeiliSearchApiError(MeiliSearchError):
    """Error sent by MeiliSearch API"""

    def __init__(self, error: str, text: bytes, status_code: int) -> None:
        self.status_code = status_code
        self.code = None
        self.link = None
        self.type = None

        if text:
            json_data = json.loads(text)
            self.message = json_data.get("message")
            self.code = json_data.get("code")
            self.link = json_data.get("link")
        else:
            self.message = error
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.code and self.link:
            return f'MeiliSearchApiError. Error code: {self.code}. Error message: {self.message} Error documentation: {self.link} Error type: {self.type}'

        return f'MeiliSearchApiError. {self.message}'

class MeiliSearchCommunicationError(MeiliSearchError):
    """Error when connecting to MeiliSearch"""

    def __str__(self) -> str:
        return f'MeiliSearchCommunicationError, {self.message}'

class MeiliSearchTimeoutError(MeiliSearchError):
    """Error when MeiliSearch operation takes longer than expected"""

    def __str__(self) -> str:
        return f'MeiliSearchTimeoutError, {self.message}'