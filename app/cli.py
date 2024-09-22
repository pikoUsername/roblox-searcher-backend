import asyncio

import click
from aiohttp import ClientSession
from fastapi import FastAPI

from app.web.app import get_app
from app.web.provider import get_client, get_roblox_token_repo


@click.group()
def cli():
    pass


@cli.command()
@click.option('--debug', is_flag=True, help="Run the FastAPI app in debug mode.")
def web(debug: bool):
    """Run the FastAPI web application."""
    token_repo = get_roblox_token_repo()
    aiohttp_client = get_client(token_repo=token_repo)
    app: FastAPI = asyncio.run(get_app(aiohttp_client, debug))
    import uvicorn
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    finally:
        asyncio.run(aiohttp_client.close())


if __name__ == '__main__':
    cli()
