"""提供的运行时加载器；读取环境指定路径以便同一助手复用不同交接版本。"""
import os
from pathlib import Path


def load_inventory_skill():
    path = Path(os.environ.get("UFLOW_SKILL_PATH", Path(__file__).parent / "skills/inventory-risk/SKILL.md"))
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError("SKILL.md 需要 YAML frontmatter")
    return text
