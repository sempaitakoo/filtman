import dataclasses
import json
from pathlib import Path

from app.models import PeerInfo, PeerUniverse

PEERS_FILE = Path("peers.lock.json")


def read_universe(path: Path = PEERS_FILE) -> PeerUniverse | None:
    """Читает peers.lock.json. Возвращает None если файл не существует."""
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    peers = [PeerInfo(**entry) for entry in data]
    return PeerUniverse(peers=peers)


def write_universe(universe: PeerUniverse, path: Path = PEERS_FILE) -> None:
    """Записывает PeerUniverse в peers.lock.json."""
    data = [dataclasses.asdict(p) for p in universe.peers]
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
