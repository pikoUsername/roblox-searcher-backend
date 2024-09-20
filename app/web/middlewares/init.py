from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.web.middlewares.logger import LoggingMiddleware

origins = [
    "http://localhost",
    "http://localhost:8000",
]


def load_middlewares(
        app: FastAPI,
        debug: bool = False
) -> None:
    if debug:
        # дает разрешение отправлять любым хостам на бекенд свои запросы.
        # что очень не безапасно
        origins.append("*")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(LoggingMiddleware, debug=debug)