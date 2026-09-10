from pathlib import Path


class LocalStorage:
    """本地开发存储；通过统一接口保留替换为对象存储的边界。"""

    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, key: str, content: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root not in path.parents:
            raise ValueError("非法存储路径")
        return path
