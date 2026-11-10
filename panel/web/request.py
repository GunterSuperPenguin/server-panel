from dataclasses import dataclass

from ..hub import Hub
from ..registry import Instance, get_instance


@dataclass
class Request:
    query: dict
    data: dict
    locale: str

    def server_name(self) -> str:
        return self.query.get("server", [""])[0]

    def instance(self) -> Instance:
        return get_instance(self.server_name())


class EventStream:
    def __init__(self, hub: Hub):
        self.hub = hub
