# -*- coding: utf-8 -*-
"""
Provice basic functions for manipulating distinguished names.
"""
__docformat__ = "restructuredtext en"

__copyright__ = """
Copyright (C) 2008-2010 Hendrikx-ITC B.V.

Distributed under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3, or (at your option) any later
version.  The full license is in the file COPYING, distributed as part of
this software.
"""
import re

explode_regex = re.compile("([^,]+)=([^,]+)")


def explode(distinguished_name):
    return explode_regex.findall(distinguished_name)


def implode(parts):
    return ",".join(
        "{0}={1}".format(type_name, name) for type_name, name in parts)


def splitparts(distinguished_name):
    """
    Split the parts of a distinguished name into a list.
    """
    regex = re.compile(r"(?<!\\),")

    return regex.split(distinguished_name)


def escape(part):
    """
    Escape reserved characters in the name part.
    """
    part = part.replace(",", "\\,")

    return part


def type_indexes(parts, type_name):
    """
    Return the indexes of `type_name` in the Distinguished Name parts, counting
    from left to right, starting at 0.
    """
    return [index for index, part in enumerate(parts) if part[0] == type_name]


def entitytype_name_from_dn(dn):
    """
    Return type of last component of distinguished name
    """
    return explode(dn)[-1][0]