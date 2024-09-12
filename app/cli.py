import asyncio

import click
from fastapi import FastAPI

from app.web.app import get_app


@click.group()
def cli():
    pass


@cli.command()
@click.option('--debug', is_flag=True, help="Run the FastAPI app in debug mode.")
def web(debug: bool):
    """Run the FastAPI web application."""
    app: FastAPI = asyncio.run(get_app(debug))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == '__main__':
    cli()
