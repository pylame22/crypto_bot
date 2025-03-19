from multiprocessing import Queue
from typing import Any

type DictStrAny = dict[str, Any]

type DataQueue = Queue[DictStrAny | None]
