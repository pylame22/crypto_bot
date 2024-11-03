from abc import ABC
from typing import Any, ClassVar

import msgspec
from aiohttp import ClientResponse

from app.core.enums import ExchangeEnum
from app.core.types import DictStrAny
from app.services.lifespan import LifeSpanContext


class ExchangeError(Exception):
    def __init__(self, status_code: int, *, message: str) -> None:
        self._status_code = status_code
        self._message = message

    def __str__(self) -> str:
        return f"{self._status_code}: {self._message}"


class BaseExchangeAPI(ABC):
    _EXCHANGE: ExchangeEnum
    _API_URL: str

    _GET = "get"
    _POST = "post"
    _PUT = "put"
    _PATCH = "patch"
    _DELETE = "delete"

    _SUCCES_STATUS_CODES = (200, 201, 204)

    _DEFAULT_HEADERS: ClassVar = {"Content-Type": "application/json"}

    def __init__(self, context: LifeSpanContext) -> None:
        self._settings = context.settings
        self._http = context.http
        self._json_decoder = msgspec.json.Decoder()
        self._json_encoder = msgspec.json.Encoder()

    def _update_headers(self, headers: DictStrAny | None) -> DictStrAny:
        if not headers:
            headers = {}
        headers.update(self._DEFAULT_HEADERS)
        return headers

    async def _parse_response(self, response: ClientResponse) -> Any:
        content = await response.content.read()
        try:
            data = self._json_decoder.decode(content)
        except msgspec.DecodeError:
            data = content.decode()
        if response.status not in self._SUCCES_STATUS_CODES:
            raise ExchangeError(response.status, message=str(data))
        return data

    async def _request(
        self,
        method: str,
        path: str,
        *,
        body: DictStrAny | None = None,
        params: DictStrAny | None = None,
        headers: DictStrAny | None = None,
    ) -> Any:
        headers = self._update_headers(headers)
        request_args: dict[str, Any] = {"params": params, "headers": headers}
        if body:
            request_args["data"] = self._json_encoder.encode(body)
        response: ClientResponse = await getattr(self._http.session, method)(self._API_URL + path, **request_args)
        return await self._parse_response(response)
