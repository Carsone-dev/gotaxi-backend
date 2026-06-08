import math
from typing import TypeVar, Generic
from pydantic import BaseModel

T = TypeVar("T")


def paginate(total: int, page: int, size: int) -> dict:
    pages = math.ceil(total / size) if size > 0 else 0
    return {"total": total, "page": page, "size": size, "pages": pages}