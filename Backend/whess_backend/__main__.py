from __future__ import annotations

import uvicorn

from whess_backend.config import Settings


def main() -> None:
    settings = Settings.from_env()
    uvicorn.run(
        "whess_backend.app:app",
        host="0.0.0.0",
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
