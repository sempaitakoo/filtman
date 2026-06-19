# grpman — Architecture

## Структура модулей

```
grpman/
├── main.py              # CLI точка входа (typer)
├── app/
│   ├── __init__.py
│   ├── config.py        # Настройки из .env
│   ├── models.py        # Доменные модели
│   ├── storage.py       # Чтение/запись filters.toml и filters.lock.toml
│   ├── telegram.py      # Обёртки над Hydrogram API
│   ├── commands.py      # Бизнес-логика команд pull / push / find-channel
│   └── wrappers.py      # (уже есть) низкоуровневые обёртки Hydrogram
```

---

## `app/config.py`

Настройки приложения через pydantic-settings (уже используется в main.py).

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    API_ID: str
    API_HASH: str
    SESSION_NAME: str = "takoo"

settings = Settings()
```

---

## `app/models.py`

Доменные модели. Не зависят ни от Hydrogram, ни от TOML — чистые dataclass-ы.

```python
@dataclass
class FilterSpec:
    """Описание одного фильтра — то, что хранится в filters.toml."""
    id: int
    title: str
    channels: list[int] = field(default_factory=list)   # include_peers (chat_id)
    pinned: list[int] = field(default_factory=list)     # pinned_peers (chat_id)
    exclude: list[int] = field(default_factory=list)    # exclude_peers (chat_id)
    broadcasts: bool = False
    contacts: bool = False
    groups: bool = False
    bots: bool = False
    exclude_muted: bool = False
    exclude_read: bool = False
    exclude_archived: bool = False


@dataclass
class FiltersState:
    """Полное состояние всех фильтров — структура filters.toml / filters.lock.toml."""
    filters: dict[int, FilterSpec]   # filter_id → FilterSpec


@dataclass
class ChannelMatch:
    """Результат поиска find-channel."""
    chat_id: int
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
```

---

## `app/storage.py`

Чтение и запись TOML-файлов. Знает только о `FilterSpec` / `FiltersState`, не знает о Telegram.

```python
FILTERS_FILE = Path("filters.toml")
LOCK_FILE = Path("filters.lock.toml")


def read_filters(path: Path = FILTERS_FILE) -> FiltersState:
    """Читает filters.toml → FiltersState. Raises FileNotFoundError если нет файла."""
    ...

def write_filters(state: FiltersState, path: Path = FILTERS_FILE) -> None:
    """Записывает FiltersState → filters.toml."""
    ...

def read_lock(path: Path = LOCK_FILE) -> FiltersState | None:
    """Читает filters.lock.toml. Возвращает None если файл не существует."""
    ...

def write_lock(state: FiltersState, path: Path = LOCK_FILE) -> None:
    """Записывает filters.lock.toml."""
    ...

def diff_states(old: FiltersState, new: FiltersState) -> FilterDiff:
    """Сравнивает два состояния, возвращает diff."""
    ...

def format_diff(diff: FilterDiff) -> str:
    """Форматирует FilterDiff в читаемый текст для вывода пользователю."""
    ...
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
channels = []
exclude = [333333333]
```

Правила записи: все поля записываются всегда, включая пустые списки и флаги `false`. `pinned` записывается перед `channels` для читаемости.

---

## `app/telegram.py`

Инкапсулирует все вызовы Hydrogram API. Конвертирует между raw Telegram-объектами и доменными моделями (`FilterSpec`, `FiltersState`, `ChannelMatch`). Снаружи никто не работает с `raw.types.DialogFilter` напрямую.

```python
async def fetch_state(client: Client) -> FiltersState:
    """Получить текущие фильтры из Telegram → FiltersState.

    Конвертирует raw.types.DialogFilter в FilterSpec.
    channels ← include_peers, pinned ← pinned_peers, exclude ← exclude_peers.
    Фильтр All Chats (id=0) пропускается.
    """
    ...

async def apply_state(client: Client, target: FiltersState) -> None:
    """Применить FiltersState к Telegram.

    - Создаёт новые фильтры (UpdateDialogFilter с новым id).
    - Обновляет изменённые фильтры.
    - Удаляет лишние фильтры (UpdateDialogFilter без filter=).
    При push chat_id резолвятся в InputPeer через resolve_peer().
    """
    ...

async def search_channels(client: Client, query: str) -> list[ChannelMatch]:
    """Искать среди диалогов пользователя по подстроке в title/username.

    Итерируется по get_dialogs(), фильтрует по query (case-insensitive).
    """
    ...
```

Внутренние хелперы (не публичный API модуля):

```python
def _raw_to_filter_spec(raw_filter: raw.types.DialogFilter) -> FilterSpec: ...
def _filter_spec_to_raw(spec: FilterSpec, peers: dict[int, InputPeer]) -> raw.types.DialogFilter: ...
def _input_peer_to_chat_id(peer: raw.base.InputPeer) -> int | None: ...
```

---

## `app/commands.py`

Бизнес-логика команд. Оркестрирует `storage` и `telegram`, выводит информацию пользователю, запрашивает подтверждения через `input()` / `cyclopts.utils.prompt()`.

```python
async def cmd_pull(client: Client) -> None:
    """
    1. fetch_state(client) → telegram_state
    2. Если filters.toml существует — прочитать, сравнить с telegram_state
    3. Если diff не пуст — показать diff, запросить confirm
    4. write_filters(telegram_state); write_lock(telegram_state)
    """
    ...

async def cmd_push(client: Client) -> None:
    """
    1. read_filters() → local_state  (ошибка если нет файла)
    2. read_lock() → lock_state
    3. fetch_state(client) → telegram_state
    4. Если lock_state есть и diff(lock_state, telegram_state) не пуст:
         показать «Telegram изменён извне», показать diff, запросить confirm
    5. Показать что будет сделано: diff(telegram_state, local_state)
    6. Запросить confirm
    7. apply_state(client, local_state)
    8. write_lock(local_state)
    """
    ...

async def cmd_find_channel(client: Client, query: str) -> None:
    """
    1. search_channels(client, query) → matches
    2. Вывести каждый match: chat_id  @username  "Title"
    """
    ...
```

---

## `main.py`

CLI на `cyclopts`. Создаёт Hydrogram-клиент и вызывает команды из `commands.py`.
Cyclopts поддерживает async-команды нативно — `asyncio.run()` не нужен.

```python
app = cyclopts.App()

def get_client() -> Client:
    return Client(settings.SESSION_NAME, api_id=settings.API_ID, api_hash=settings.API_HASH)

@app.command
async def pull() -> None:
    """Скачать фильтры из Telegram в filters.toml."""
    async with get_client() as client:
        await cmd_pull(client)

@app.command
async def push() -> None:
    """Применить filters.toml к Telegram."""
    async with get_client() as client:
        await cmd_push(client)

@app.command(name="find-channel")
async def find_channel(query: str) -> None:
    """Найти канал среди диалогов по названию."""
    async with get_client() as client:
        await cmd_find_channel(client, query)

if __name__ == "__main__":
    app()
```

---

## Зависимости между модулями

```
main.py
  └─ commands.py
       ├─ storage.py   (read/write TOML)
       ├─ telegram.py  (Hydrogram API)
       └─ models.py

telegram.py
  └─ wrappers.py  (низкоуровневые вызовы Hydrogram)

storage.py / models.py  — без внешних зависимостей (кроме stdlib)
```

---

## Что остаётся от текущего кода

| Файл | Судьба |
|---|---|
| `app/wrappers.py` | Остаётся как есть — используется внутри `telegram.py` |
| `app/folders.py` | Функции переносятся/рефакторятся в `telegram.py` |
| `folder_manager.py` | Удаляется — логика поглощается новыми модулями |
| `main.py` | Переписывается под typer CLI |

---

## Зависимости для добавления в pyproject.toml

- `cyclopts` — CLI-фреймворк (поддерживает async-команды нативно)
- `tomli-w` — запись TOML (чтение через stdlib `tomllib`, Python 3.11+)
