# filtman

CLI-инструмент для управления папками (фильтрами) чатов в Telegram.

## Концепция

Состояние папок описывается в `filters.toml`. Редактируешь файл вручную — применяешь через `push`. Модель похожа на git.

## Команды

| Команда | Описание |
|---|---|
| `pull` | Скачать текущие фильтры из Telegram |
| `push` | Применить `filters.toml` к Telegram |
| `diff` | Показать что изменится при следующем `push` |
| `exclude <target> --from <source>` | Добавить peers одной папки в exclude другой |
| `find-channel <query>` | Найти канал среди диалогов по названию |

## Установка

```bash
pip install -e .
```

Создай `.env`:

```env
API_ID=...
API_HASH=...
SESSION_NAME=..
```

## Пример

```bash
filtman pull                  # получить текущее состояние
# отредактировать filters.toml
filtman diff                  # проверить изменения
filtman push                  # применить
```
