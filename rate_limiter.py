"""Rate limiting for the FastAPI endpoints.

Uses ``slowapi`` keyed by the client's remote address. The limiter is
exposed as a module-level singleton and wired into the FastAPI app in
``api/main.py`` via ``app.state.limiter``.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)