# -*- coding: utf-8 -*-
__docformat__ = "restructuredtext en"

__copyright__ = """
Copyright (C) 2008-2013 Hendrikx-ITC B.V.

Distributed under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3, or (at your option) any later
version.  The full license is in the file COPYING, distributed as part of
this software.
"""
import logging


def log_call_basic(fn):
    """Return decorated function that logs each call."""
    def wrapper(*args, **kwargs):
        """Return result of wrapped function and log call."""
        all_args = list(args) + kwargs.values()

        type_names = [t.__name__ for t in map(type, all_args)]

        logging.debug("--> {}({})".format(fn.__name__, ", ".join(type_names)))
        return fn(*args, **kwargs)

    return wrapper


def log_call(log_fn=logging.debug):
    """Return a decorator using specified logger function."""
    def dec_fn(fn):
        """Return decorated function that logs each call."""
        if hasattr(fn, "__name__"):
            name = fn.__name__
        else:
            name = "<anonymous function>"

        def wrapper(*args, **kwargs):
            """Return result of wrapped function and log call."""
            log_fn("--- enter {} ---".format(name))
            log_fn("args({}): {}".format(len(args), ", ".join(map(str, args))))
            result = fn(*args, **kwargs)

            log_fn("result: {}".format(result))
            log_fn("--- exit {} ---".format(name))

            return result

        return wrapper

    return dec_fn


def log_call_on_exception(log_fn=logging.debug):
    def dec_fn(fn):
        if hasattr(fn, "__name__"):
            name = fn.__name__
        else:
            name = "<anonymous function>"

        def wrapper(*args, **kwargs):
            lines = [
                "--- enter {} ---".format(name),
                "args({}): {}".format(len(args), ", ".join(map(str, args)))]
            try:
                result = fn(*args, **kwargs)
            except:
                map(log_fn, lines)

                raise
            else:
                return result

        return wrapper

    return dec_fn
