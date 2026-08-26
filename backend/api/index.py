"""What Vercel runs.

The platform looks for a Python file under api/ and serves whatever ASGI
application it finds there, so this is a doorway rather than a place for logic:
the application itself is the same app.main:app that uvicorn serves locally,
and nothing here changes how it behaves.

Being on Vercel is not configured — the platform sets VERCEL itself, and the
settings read it — so this file has nothing to declare.
"""

from app.main import app

__all__ = ["app"]
