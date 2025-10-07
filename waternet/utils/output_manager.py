from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Optional, Union

PathLike = Union[str, Path]


def ensure_output_tree(base_dir: PathLike, subdirs: Iterable[PathLike]) -> Dict[str, Path]:
    """
    确保 ``base_dir`` 以及指定的子目录全部创建完成。

    参数：
        base_dir：需要创建或检查的根目录。
        subdirs：需要同步创建的相对子目录集合。

    返回：
        以子目录字符串为键、对应绝对路径为值的字典。
    """
    base_path = Path(base_dir)
    base_path.mkdir(parents=True, exist_ok=True)

    created: Dict[str, Path] = {}
    for sub in subdirs:
        sub_path = base_path / Path(sub)
        sub_path.mkdir(parents=True, exist_ok=True)
        created[str(sub)] = sub_path
    return created


def timestamped_path(
    base_dir: PathLike,
    stem: str,
    suffix: str = "",
    timestamp: Optional[str] = None,
) -> Path:
    """
    在 ``base_dir`` 下构造带时间戳的文件路径。

    参数：
        base_dir：目标目录。
        stem：文件名前缀。
        suffix：文件扩展名，允许不带点。
        timestamp：可选的时间戳，留空时使用当前 UTC。
    """
    ts = timestamp or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    if suffix and not suffix.startswith("."):
        suffix = f".{suffix}"
    return Path(base_dir) / f"{stem}_{ts}{suffix}"
