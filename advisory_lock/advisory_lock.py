#!/usr/bin/env python3
# -*- coding: utf8 -*-

# pylint: disable=C0111  # docstrings are always outdated and wrong
# pylint: disable=W0511  # todo is encouraged
# pylint: disable=C0301  # line too long
# pylint: disable=R0902  # too many instance attributes
# pylint: disable=C0302  # too many lines in module
# pylint: disable=C0103  # single letter var names, func name too descriptive
# pylint: disable=R0911  # too many return statements
# pylint: disable=R0912  # too many branches
# pylint: disable=R0915  # too many statements
# pylint: disable=R0913  # too many arguments
# pylint: disable=R1702  # too many nested blocks
# pylint: disable=R0914  # too many local variables
# pylint: disable=R0903  # too few public methods
# pylint: disable=E1101  # no member for base
# pylint: disable=W0201  # attribute defined outside __init__
# pylint: disable=R0916  # Too many boolean expressions in if statement


import fcntl
import os
#import sys
from pathlib import Path

import click
from asserttool import ic
from asserttool import nevd

#from enumerate_input import enumerate_input
#from retry_on_exception import retry_on_exception


def path_is_advisory_locked(path: Path,
                            verbose: bool,
                            debug: bool,
                            ) -> None:

    with AdvisoryLock(path=path,
                      open_read=False,
                      open_write=True,  # using lockf, so NFS locks work, requires 'w'
                      flock=False,
                      file_exists=True,
                      verbose=verbose,
                      debug=debug,) as fl:
        raise AssertionError(path.as_posix(), 'was not advisory locked')
    return  #all good


# https://docs.python.org/3/library/fcntl.html
class AdvisoryLock():
    def __init__(self,
                 path: Path, *,
                 file_exists: bool,
                 open_read: bool,
                 open_write: bool,
                 flock: bool,
                 verbose: bool,
                 debug: bool,
                 ):

        self.verbose = verbose
        self.debug = debug
        self.path = path
        self.file_exists = file_exists
        self.open_read = open_read
        self.open_write = open_write
        self.flock = flock
        if debug:
            ic(self.path)

    def __enter__(self):
        if self.debug:
            ic()

        # O_RDWR            Read/Write
        # O_RDONLY          Write Only
        # O_WRONLY          Read Only
        if self.open_read and self.open_write:
            flags = os.O_RDWR
        elif self.open_read:
            flags = os.O_RDONLY
        elif self.open_write:  # may want to add write_to_existing_file double check flag?
            flags = os.O_WRONLY
        else:
            raise ValueError('at least one of `open_read` and `open_write` must be True')

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

        # race here _unless_ flags has os.O_CREAT | os.O_EXCL
        # LOCK_EX       Place an exclusive lock.  Only one process may hold an exclusive lock for a given file at a given time.
        # LOCK_NB       Nonblocking request
        if self.flock:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # acquire a non-blocking advisory lock  # broken on NFS
            if self.debug:
                ic('got (flock) lock:', self.path)
        else:
            fcntl.lockf(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # acquire a non-blocking advisory lock
            if self.debug:
                ic('got (lockf) lock:', self.path)

        return self.fd

    def __exit__(self, etype, value, traceback):
        if self.debug:
            ic(etype)
            ic(value)
            ic(traceback)

        fcntl.lockf(self.fd, fcntl.LOCK_UN)
        os.close(self.fd)


# import pdb; pdb.set_trace()
# from pudb import set_trace; set_trace(paused=False)

@click.command()
@click.argument("path", type=str, nargs=1)
@click.option('--verbose', is_flag=True)
@click.option('--no-read', is_flag=True)
@click.option('--flock', is_flag=True)  # making lockf the default, implies --write, on the other hand, lockf WORKS in all cases (with --write)... because flock is broken on NFS
@click.option('--write', is_flag=True)  # as-is, this reqires thought, so it's good for now
@click.option('--debug', is_flag=True)
@click.option('--hold', is_flag=True)
@click.option('--ipython', is_flag=True)
@click.pass_context
def cli(ctx,
        path,
        no_read: bool,
        write: bool,
        flock: bool,
        verbose: bool,
        debug: bool,
        hold: bool,
        ipython: bool,
        ):

    null, end, verbose, debug = nevd(ctx=ctx,
                                     printn=False,
                                     ipython=False,
                                     verbose=verbose,
                                     debug=debug,)

    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['debug'] = debug
    ctx.obj['end'] = end
    ctx.obj['null'] = null

    lock_type = 'lockf'
    if flock:
        lock_type = 'flock'

    path = Path(path).expanduser()
    if not flock:  # flock is broken on NFS
        if not write:
            raise ValueError('lockf() requires a O_RDWR fd, specify --write')

    with AdvisoryLock(path=path,
                      open_read=not no_read,
                      open_write=write,
                      flock=flock,
                      file_exists=True,
                      verbose=verbose,
                      debug=debug,) as fl:
        ic(fl)
        if ipython:
            import IPython
            IPython.embed()
        if hold:
            ans = input('press enter to release {} advisory lock on: '.format(lock_type) + path.as_posix())
