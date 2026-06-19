# grpman — Architecture

## Структура модулей

```
grpman/
├── main.py                   # CLI точка входа (cyclopts)
└── app/
    ├── config.py             # Настройки из .env
    ├── models.py             # Доменные модели
    ├── mapper.py             # Конвертация dict ↔ FiltersState (TOML-слой)
    ├── storage/
    │   ├── io.py             # Чтение/запись filters.toml и filters.lock.toml
    │   └── diff.py           # diff_states, format_diff
    ├── ops/
    │   └── filters.py        # Операции над FiltersState без I/O и без Telegram
    ├── telegram/
    │   ├── api.py            # fetch_state, apply_state, search_channels
    │   └── wrappers.py       # Низкоуровневые обёртки Hydrogram
    └── commands/
        ├── local.py          # Команды, работающие только с TOML
        └── sync.py           # Команды, требующие Telegram (pull, push, find-channel)
```

---

## `app/config.py`

Настройки приложения через pydantic-settings.

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    API_ID: str
    API_HASH: str
    SESSION_NAME: str

settings = Settings()
```

---

## `app/models.py`

Доменные модели. Не зависят ни от Hydrogram, ни от TOML — чистые dataclass-ы.

```python
@dataclass
class FilterSpec:
    id: int
    title: str
    channels: list[int] = ...   # include_peers (chat_id)
    pinned: list[int] = ...     # pinned_peers (chat_id)
    exclude: list[int] = ...    # exclude_peers (chat_id)
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
    filters: list[FilterSpec]

@dataclass
class ChannelMatch:
    chat_id: int
    username: str | None
    title: str

@dataclass
class FilterDiff:
    created: list[FilterSpec]
    updated: list[tuple[FilterSpec, FilterSpec]]  # (old, new)
    deleted: list[FilterSpec]

    @property
    def is_empty(self) -> bool: ...
```

---

## `app/mapper.py`

Конвертация между TOML-словарём и доменными моделями. Не знает о файловой системе.

```python
BOOL_FLAGS = ("broadcasts", "contacts", "non_contacts", "groups", "bots",
              "exclude_muted", "exclude_read", "exclude_archived")
LIST_FIELDS = ("pinned", "channels", "exclude")

def state_from_dict(data: dict) -> FiltersState: ...
def state_to_dict(state: FiltersState) -> dict: ...
```

---

## `app/storage/io.py`

Чтение и запись TOML-файлов. Использует `mapper` для конвертации, не знает о Telegram.

```python
FILTERS_FILE = Path("filters.toml")
LOCK_FILE = Path("filters.lock.toml")

def read_filters(path: Path = FILTERS_FILE) -> FiltersState: ...
def write_filters(state: FiltersState, path: Path = FILTERS_FILE) -> None: ...
def read_lock(path: Path = LOCK_FILE) -> FiltersState | None: ...
def write_lock(state: FiltersState, path: Path = LOCK_FILE) -> None: ...
```

**Формат TOML:**

```toml
[filters.1]
title = "Работа"
pinned = [111111111]
channels = [123456789, 987654321]

[filters.3]
title = "Политика"
broadcasts = true
exclude = [333333333]
```

Правила записи: пустые списки и флаги `false` не записываются. `pinned` записывается перед `channels` для читаемости.

---

## `app/storage/diff.py`

Сравнение двух состояний и форматирование результата для вывода пользователю.

```python
def diff_states(old: FiltersState, new: FiltersState) -> FilterDiff: ...
def format_diff(diff: FilterDiff, *, colored: bool = False) -> str: ...
```

---

## `app/ops/filters.py`

Чистые операции над `FiltersState` — без файлового I/O и без Telegram. Сюда добавляются новые действия, которые работают только с локальными данными.

---

## `app/telegram/wrappers.py`

Низкоуровневые обёртки над Hydrogram. Изолируют вызовы API от бизнес-логики.

```python
def input_peer_to_chat_id(peer: InputPeer) -> int | None: ...
def iter_dialogs(client: Client) -> AsyncGenerator[Dialog]: ...
async def resolve_peer(client: Client, chat_id: int) -> InputPeer: ...
async def fetch_filters(client: Client) -> list[DialogFilter]: ...
```

---

## `app/telegram/api.py`

Инкапсулирует все вызовы Hydrogram API. Конвертирует между `raw.types.DialogFilter` и доменными моделями. Снаружи никто не работает с raw-объектами Telegram напрямую.

```python
async def fetch_state(client: Client) -> FiltersState:
    """channels ← include_peers, pinned ← pinned_peers, exclude ← exclude_peers.
    Фильтр All Chats (id=0) пропускается."""
    ...

async def apply_state(client: Client, target: FiltersState) -> None:
    """Создаёт новые фильтры, обновляет изменённые, удаляет лишние.
    chat_id резолвятся в InputPeer через resolve_peer()."""
    ...

async def search_channels(client: Client, query: str) -> list[ChannelMatch]:
    """Итерируется по get_dialogs(), фильтрует по query (case-insensitive)."""
    ...
```

---

## `app/commands/sync.py`

Команды, требующие подключения к Telegram. Оркестрируют `storage` и `telegram`, выводят информацию пользователю, запрашивают подтверждения через `input()`.

```python
async def cmd_pull(client: Client) -> None:
    """
    1. fetch_state(client) → telegram_state
    2. Если filters.toml существует — прочитать, сравнить с telegram_state
    3. Если diff не пуст — показать diff, запросить confirm
    4. write_filters(telegram_state); write_lock(telegram_state)
    """

async def cmd_push(client: Client) -> None:
    """
    1. read_filters() → local_state  (ошибка если нет файла)
    2. read_lock() → lock_state
    3. fetch_state(client) → telegram_state
    4. Если lock_state есть и diff(lock_state, telegram_state) не пуст:
         показать «Telegram изменён извне», запросить confirm
    5. Показать diff(telegram_state, local_state), запросить confirm
    6. apply_state(client, local_state); write_lock(local_state)
    """

async def cmd_find_channel(client: Client, query: str) -> None:
    """search_channels(client, query) → вывести каждый match: chat_id  @username  "Title" """
```

---

## `app/commands/local.py`

Команды, работающие только с TOML — без подключения к Telegram. Используют `storage` и `ops`.

```python
def cmd_diff() -> None:
    """
    1. read_filters() → local_state  (ошибка если нет файла)
    2. read_lock() → lock_state  (ошибка если нет файла)
    3. diff_states(lock_state, local_state) → diff
    4. Если diff пуст — «Нет изменений.»
    5. Иначе — вывести format_diff(diff, colored=True)
    """
```

---

## `main.py`

CLI на `cyclopts`. Создаёт Hydrogram-клиент и вызывает команды из `commands/`.
Cyclopts поддерживает async-команды нативно — `asyncio.run()` не нужен.

---

## Зависимости между модулями

```
main.py
  ├─ commands/sync.py
  │    ├─ storage/io.py    (read/write TOML)
  │    ├─ storage/diff.py  (сравнение состояний)
  │    └─ telegram/api.py  (Hydrogram API)
  └─ commands/local.py
       ├─ storage/io.py
       ├─ storage/diff.py
       └─ ops/filters.py   (операции над FiltersState)

telegram/api.py
  └─ telegram/wrappers.py

storage/io.py
  └─ mapper.py

storage/diff.py
  └─ mapper.py  (BOOL_FLAGS, LIST_FIELDS)

mapper.py / models.py  — без внешних зависимостей (кроме stdlib)
```
