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
import sys
from pathlib import Path

import click
from enumerate_input import enumerate_input
from retry_on_exception import retry_on_exception


def eprint(*args, **kwargs):
    if 'file' in kwargs.keys():
        kwargs.pop('file')
    print(*args, file=sys.stderr, **kwargs)


try:
    from icecream import ic  # https://github.com/gruns/icecream
except ImportError:
    ic = eprint


# https://docs.python.org/3/library/fcntl.html
class AdvisoryLock():
    def __init__(self,
                 path: Path, *,
                 file_exists: bool,
                 open_read: bool,
                 open_write: bool,
                 verbose: bool,
                 debug: bool,):

        self.verbose = verbose
        self.debug = debug
        self.path = path
        self.file_exists = file_exists
        self.open_read = open_read
        self.open_write = open_write
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
        if self.debug:
            ic(self.path, self.fd)
        # race here _unless_ flags has os.O_CREAT | os.O_EXCL
        fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # acquire a non-blocking advisory lock
        if self.debug:
            ic('got lock:', self.path)

        return self.fd

        #file = io.open(self.fd,
        #               mode="w+b",
        #               buffering=-1,
        #               newline=None,
        #               encoding=None,
        #               errors=None)
        #if self.debug:
        #    ic(file)

        #self.tmp = _TemporaryFileWrapper(file=file,
        #                                 name=self.name,
        #                                 delete=False)

        #if self.debug:
        #    ic(self.tmp)
        ##ic(self.fd, self.tmp.name)
        #return self.tmp

    def __exit__(self, etype, value, traceback):
        if self.debug:
            ic(etype)
            ic(value)
            ic(traceback)

        fcntl.lockf(self.fd, fcntl.LOCK_UN)


# import pdb; pdb.set_trace()
# from pudb import set_trace; set_trace(paused=False)

@click.command()
@click.argument("path", type=str, nargs=1)
@click.option('--verbose', is_flag=True)
@click.option('--debug', is_flag=True)
@click.option('--ipython', is_flag=True)
@click.option('--count', is_flag=True)
@click.option('--skip', type=int, default=False)
@click.option('--head', type=int, default=False)
@click.option('--tail', type=int, default=False)
@click.option("--printn", is_flag=True)
@click.pass_context
def cli(ctx,
        path,
        verbose: bool,
        debug: bool,
        ipython: bool,
        count: bool,
        skip: int,
        head: int,
        tail: int,
        printn: bool,):

    null = not printn
    end = '\n'
    if null:
        end = '\x00'
    if sys.stdout.isatty():
        end = '\n'
        assert not ipython

    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['debug'] = debug
    ctx.obj['end'] = end
    ctx.obj['null'] = null
    ctx.obj['count'] = count
    ctx.obj['skip'] = skip
    ctx.obj['head'] = head
    ctx.obj['tail'] = tail

    path = Path(path)
    with AdvisoryLock(path=path,
                      open_read=True,
                      open_write=False,
                      file_exists=True,
                      verbose=verbose,
                      debug=debug,) as fl:
        ic(fl)
        import IPython
        IPython.embed()


    #locks = []
    #iterator = paths
    #for index, path in enumerate_input(iterator=iterator,
    #                                   null=null,
    #                                   progress=progress,
    #                                   skip=skip,
    #                                   head=head,
    #                                   tail=tail,
    #                                   debug=debug,
    #                                   verbose=verbose,):
    #    path = Path(path)

    #    if verbose:
    #        ic(index, path)

    #    with Ad(path, 'rb') as fh:
    #        path_bytes_data = fh.read()

    #    if not count:
    #        print(path, end=end)


#   #     if ipython:
#   #         import IPython; IPython.embed()

#@cli.command()
#@click.argument("urls", type=str, nargs=-1)
#@click.pass_context
#def some_command(ctx, urls):
#    pass
#    iterator = urls
#    for index, url in enumerate_input(iterator=iterator,
#                                      null=ctx.obj['null'],
#                                      progress=ctx.obj['progress'],
#                                      skip=ctx.obj['skip'],
#                                      head=ctx.obj['head'],
#                                      tail=ctx.obj['tail'],
#                                      debug=ctx.obj['debug'],
#                                      verbose=ctx.obj['verbose'],):
#
#        if ctx.obj['verbose']:
#            ic(index, url)





