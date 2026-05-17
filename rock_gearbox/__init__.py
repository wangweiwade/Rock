"""Rock 齿轮箱自动选型程序核心包。"""

from .models import SelectionInput, SelectionResult, Gearbox
from .selector import select_gearbox, NoSuitableGearboxError

__all__ = [
    "SelectionInput",
    "SelectionResult",
    "Gearbox",
    "select_gearbox",
    "NoSuitableGearboxError",
]
