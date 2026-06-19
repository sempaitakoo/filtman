from dataclasses import dataclass, field

type FilterId = int
type ChatId = int


@dataclass
class FilterSpec:
    """Описание одного фильтра — то, что хранится в filters.toml."""

    id: FilterId
    title: str
    channels: list[ChatId] = field(default_factory=list)
    pinned: list[ChatId] = field(default_factory=list)
    exclude: list[ChatId] = field(default_factory=list)
    broadcasts: bool = False
    contacts: bool = False
    non_contacts: bool = False
    groups: bool = False
    bots: bool = False
    exclude_muted: bool = False
    exclude_read: bool = False
    exclude_archived: bool = False


@dataclass
class FiltersState:
    """Полное состояние всех фильтров — структура filters.toml / filters.lock.toml."""

    filters: dict[FilterId, FilterSpec]


@dataclass
class ChannelMatch:
    """Результат поиска find-channel."""

    chat_id: ChatId
    username: str | None
    title: str


@dataclass
class FilterDiff:
    """Разница между двумя состояниями FiltersState."""

    created: list[FilterSpec]
    updated: list[tuple[FilterSpec, FilterSpec]]  # (old, new)
    deleted: list[FilterSpec]

    @property
    def is_empty(self) -> bool:
        return not (self.created or self.updated or self.deleted)
