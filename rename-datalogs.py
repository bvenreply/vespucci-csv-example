#!/bin/env python
from pathlib import Path
import re
import logging
from typing import Any
import typer
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from hashlib import sha256, file_digest
from base64 import b32encode

ex = ThreadPoolExecutor((os.cpu_count() or 2) * 2)

log = logging.getLogger(__name__)

app = typer.Typer()


class InputError(Exception): ...


reg = re.compile("^([^_]+)_[^_]+_(\\d+)\\.csv$")


def rename_one(to_rename: Path, tag: str) -> Any:
    name = to_rename.name

    if not name.startswith(tag):
        log.warn("File named %s does not adhere to convention, skipping", name)
        return

    sensor_first_index = len(tag) + 1
    name_without_tag = name[sensor_first_index:]

    matched = reg.match(name_without_tag)
    groups = matched.groups()

    assert len(groups) == 2

    sensor, idx = groups

    with open(to_rename, "rb") as file:
        digest = file_digest(file, sha256)
        encoded = b32encode(digest.digest()).decode("utf-8").lower()

    new_name = f"{sensor}_{encoded[:8]}.csv"

    log.debug("Renaming %s -> %s", name, new_name)

    to_rename.rename(to_rename.with_name(new_name))


def rename_in_dir(directory: Path) -> Any:
    files = directory.glob("*.csv")

    futs = (ex.submit(rename_one, file, directory.name) for file in files)
    es = []

    for fut in as_completed(futs):
        if fut.exception() is not None:
            es.append(fut.exception())

    if len(es) > 0:
        raise ExceptionGroup("Errors running command", es)


@app.command()
def rename(acquisition_folder: str) -> Any:
    log.info("Starting rename command")

    path = Path(acquisition_folder).absolute()

    if not path.exists():
        raise InputError("Acquisition folder not found")

    if not path.is_dir():
        raise InputError("Target path is not a directory")

    children = tuple(path.iterdir())

    for child in children:
        if child.is_dir():
            rename_in_dir(child)


def run() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "info").upper())
    app()


if __name__ == "__main__":
    run()
