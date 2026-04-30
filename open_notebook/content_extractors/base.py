from typing import Any, Protocol

from content_core.common import ProcessSourceState


class ContentExtractor(Protocol):
    name: str

    def supports(self, state: dict[str, Any]) -> bool:
        ...

    def extract(self, state: dict[str, Any]) -> ProcessSourceState | None:
        ...
