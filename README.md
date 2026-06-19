# filtman

CLI-инструмент для управления папками (фильтрами) чатов в Telegram.

## Концепция

Состояние папок описывается в `filters.toml`. Редактируешь файл вручную — применяешь через `push`. Модель похожа на git: `pull` скачивает текущее состояние из Telegram, `push` применяет локальные изменения обратно.

## Установка

```bash
pip install -e .
```

Создай `.env`:

```env
API_ID=...
API_HASH=...
SESSION_NAME=myname
```

## Команды

| Команда | Описание | Telegram |
|---|---|---|
| `pull` | Скачать текущие фильтры из Telegram | да |
| `push` | Применить `filters.toml` к Telegram | да |
| `find-channel <query>` | Найти канал среди диалогов по названию | да |
| `diff` | Показать что изменится при следующем `push` | нет |
| `exclude <target> --from <source>` | Добавить peers одной папки в exclude другой | нет |
| `compact [filter_id]` | Заменить явные списки каналов флагами категорий | нет |
| `overlap [filter_id]` | Показать чаты, присутствующие в нескольких папках | нет* |
| `annotate` | Проставить комментарии с именами чатов в `filters.toml` | нет |

## Файлы

### `filters.toml`

Основной файл конфигурации. Редактируется вручную, применяется через `push`.

```toml
[filters.1]
title = "Работа"
pinned = [
    111111111, # Work Chat
]
channels = [
    123456789, # РБК
    987654321, # Breaking Mash
]

[filters.2]
title = "Мемы"
channels = [
    222222222, # MDK
    333333333, # Мемпул
]

[filters.3]
title = "Каналы"
broadcasts = true   # все каналы автоматически
exclude = [
    123456789, # РБК — уже в Работе
]
```

Числовой id секции (`[filters.1]`) — это id фильтра из Telegram, берётся при `pull`. Флаги `broadcasts`, `groups`, `contacts` и т.д. включают целую категорию чатов без перечисления. Пустые списки и флаги `false` не записываются.

*`overlap` не требует подключения к Telegram, но требует актуального `peers.lock.json` — запустите `pull` перед первым использованием.

### `peers.lock.json`

Кеш всех диалогов на момент последнего `pull`. Генерируется автоматически, не редактируется вручную. Используется командами `exclude`, `compact`, `annotate` и `overlap`.

```json
[
  {
    "chat_id": 123456789,
    "name": "РБК",
    "username": "rbc",
    "is_broadcast": true,
    "is_group": false,
    "is_contact": false,
    "is_non_contact": true,
    "is_bot": false
  },
  {
    "chat_id": 111111111,
    "name": "Work Chat",
    "username": null,
    "is_broadcast": false,
    "is_group": true,
    "is_contact": false,
    "is_non_contact": true,
    "is_bot": false
  }
]
```

### `filters.lock.toml`

Снимок состояния Telegram на момент последнего `pull`. Генерируется автоматически. Используется командой `push` для обнаружения конфликтов — если Telegram был изменён с другого устройства после `pull`, `push` покажет расхождение и запросит подтверждение.

## Типичный рабочий процесс

```bash
filtman pull                        # получить текущее состояние из Telegram
# отредактировать filters.toml
filtman diff                        # проверить изменения перед отправкой
filtman push                        # применить

filtman find-channel "breaking"     # узнать chat_id нужного канала
filtman overlap                     # найти чаты, которые дублируются в папках
filtman exclude 1 --from 2         # убрать из папки 1 всё, что есть в папке 2
filtman annotate                    # обновить комментарии после ручного редактирования
```
