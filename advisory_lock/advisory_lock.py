#!/usr/bin/env python3
# -*- coding: utf8 -*-

# pylint: disable=useless-suppression             # [I0021]
# pylint: disable=missing-docstring               # [C0111] docstrings are always outdated and wrong
# pylint: disable=fixme                           # [W0511] todo is encouraged
# pylint: disable=line-too-long                   # [C0301]
# pylint: disable=too-many-instance-attributes    # [R0902]
# pylint: disable=too-many-lines                  # [C0302] too many lines in module
# pylint: disable=invalid-name                    # [C0103] single letter var names, name too descriptive
# pylint: disable=too-many-return-statements      # [R0911]
# pylint: disable=too-many-branches               # [R0912]
# pylint: disable=too-many-statements             # [R0915]
# pylint: disable=too-many-arguments              # [R0913]
# pylint: disable=too-many-nested-blocks          # [R1702]
# pylint: disable=too-many-locals                 # [R0914]
# pylint: disable=too-few-public-methods          # [R0903]
# pylint: disable=no-member                       # [E1101] no member for base
# pylint: disable=attribute-defined-outside-init  # [W0201]
# pylint: disable=too-many-boolean-expressions    # [R0916] in if statement
from __future__ import annotations

import fcntl
import os
from math import inf
from pathlib import Path

import click
from asserttool import ic
from clicktool import click_add_options
from clicktool import click_global_options
from clicktool import tv


# for cli
def path_is_advisory_locked(
    path: Path,
    verbose: bool | int | float,
) -> None:

    with AdvisoryLock(
        path=path,
        open_read=False,
        open_write=True,  # using lockf, so NFS locks work, requires 'w'
        flock=False,
        file_exists=True,
        verbose=verbose,
    ) as _:
        raise AssertionError(path.as_posix(), "was not advisory locked")
    # no Exception, an advisory lock exists, default return of None


# https://docs.python.org/3/library/fcntl.html
class AdvisoryLock:
    def __init__(
        self,
        path: Path,
        *,
        file_exists: bool,
        open_read: bool,
        open_write: bool,
        flock: bool,
        verbose: bool | int | float,
    ):

        self.verbose = verbose
        self.path = path
        self.file_exists = file_exists
        self.open_read = open_read
        self.open_write = open_write
        self.flock = flock
        if verbose == inf:
            ic(self.path)

    def __enter__(self):
        if self.verbose == inf:
            ic()

        # O_RDWR            Read/Write
        # O_RDONLY          Write Only
        # O_WRONLY          Read Only
        if self.open_read and self.open_write:
            flags = os.O_RDWR
        elif self.open_read:
            flags = os.O_RDONLY
        elif (
            self.open_write
        ):  # may want to add write_to_existing_file double check flag?
            flags = os.O_WRONLY
        else:
            raise ValueError(
                f"at least one of {self.open_read=} and {self.open_write=} must be True"
            )

        # O_NOFOLLOW    Dont follow symlink if the last element in the path is one
        flags |= os.O_NOFOLLOW

        # O_CREAT       If pathname does not exist, create it as a regular file.
        # O_EXCL        Ensure that this call creates the file
        if not self.file_exists:
            flags |= os.O_CREAT | os.O_EXCL
        assert self.path.exists()

        self.fd = os.open(self.path, flags, 0o600)
        if self.verbose > 2:
            ic(self.fd, os.fstat(self.fd), self.path)

        # race here unless self.file_exists=False (and therefore flags |= os.O_CREAT | os.O_EXCL)
        #   its a race because another process could have obtained self.fd...
        # LOCK_EX       Place an exclusive lock.  Only one process may hold an exclusive lock for a given file at a given time.
        # LOCK_NB       Nonblocking request
        if self.flock:
            fcntl.flock(
                self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB
            )  # acquire a non-blocking advisory lock  # broken on NFS
            if self.verbose == inf:
                ic("got (flock) lock:", self.path)
        else:
            fcntl.lockf(
                self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB
            )  # acquire a non-blocking advisory lock
            if self.verbose == inf:
                ic("got (lockf) lock:", self.path)

        return self.fd

    def __exit__(self, etype, value, traceback):
        if self.verbose == inf:
            ic(etype)
            ic(value)
            ic(traceback)

        fcntl.lockf(
            self.fd, fcntl.LOCK_UN
        )  # bug use whatever function the locking was accomplished with
        os.close(self.fd)


@click.command()
@click.argument("path", type=str, nargs=1)
@click.option("--no-read", is_flag=True)
@click.option(
    "--flock", is_flag=True
)  # making lockf the default, implies --write, on the other hand, lockf WORKS in all cases (with --write)... because flock is broken on NFS
@click.option(
    "--write", is_flag=True
)  # as-is, this reqires thought, so it's good for now
@click.option("--hold", is_flag=True)
@click.option("--ipython", is_flag=True)
@click.option("--pdb", "pudb", is_flag=True)
@click_add_options(click_global_options)
@click.pass_context
def cli(
    ctx,
    path,
    no_read: bool,
    write: bool,
    flock: bool,
    verbose: bool | int | float,
    verbose_inf: bool,
    dict_output: bool,
    hold: bool,
    ipython: bool,
    pudb: bool,
):

    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )

    lock_type = "lockf"
    if flock:
        lock_type = "flock"

    path = Path(path).expanduser()
    if not flock:  # flock is broken on NFS
        if not write:
            raise ValueError("lockf() requires a O_RDWR fd, specify --write")

    with AdvisoryLock(
        path=path,
        open_read=not no_read,
        open_write=write,
        flock=flock,
        file_exists=True,
        verbose=verbose,
    ) as fl:
        ic(fl)
        # pylint: disable=import-outside-toplevel # pylint: disable=C0415
        # pylint: disable=W1515
        if ipython:
            import IPython

            IPython.embed()
        if pudb:
            import pdb

            pdb.set_trace()
            from pudb import set_trace

            set_trace(paused=False)

        if hold:
            _ = input(
                f"press enter to release {lock_type} advisory lock on: {path.as_posix()}"
            )
