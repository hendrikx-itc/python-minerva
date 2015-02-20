# -*- coding: utf-8 -*-
__docformat__ = "restructuredtext en"

__copyright__ = """
Copyright (C) 2011-2015 Hendrikx-ITC B.V.

Distributed under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3, or (at your option) any later
version.  The full license is in the file COPYING, distributed as part of
this software.
"""


class DataSet():
    description = "Set this property in child classes to describe the data set"

    def load(self, cursor):
        """
        Override this method in child class to load the test set.
        """
        raise NotImplementedError()
