import asyncio
import time

import click
from aiohttp import ClientSession
from dotenv import load_dotenv
from fastapi import FastAPI

from app.web.app import get_app
from app.web.provider import get_client, get_roblox_token_repo


@click.group()
def cli():
    load_dotenv()


@cli.command()
@click.option('--debug', is_flag=True, help="Run the FastAPI app in debug mode.")
def web(debug: bool):
    """Run the FastAPI web application."""
    loop = asyncio.get_event_loop()
    run = lambda x: loop.run_until_complete(x)

    token_repo, connection = run(get_roblox_token_repo())

    aiohttp_client = run(get_client(token_repo=token_repo))
    app: FastAPI = run(get_app(aiohttp_client, debug))
    import uvicorn
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    finally:
        run(aiohttp_client.close())
        run(connection.close())


if __name__ == '__main__':
    cli()
