import time
from collections import defaultdict, deque
from fastapi import HTTPException
_hits = defaultdict(deque)
def limit(key: str, n: int, per: int):
    now = time.time(); d = _hits[key]
    while d and now - d[0] > per: d.popleft()
    if len(d) >= n: raise HTTPException(429, "Too many requests, please slow down")
    d.append(now)
