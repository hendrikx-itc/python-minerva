# -*- coding: utf-8 -*-
"""Provides Attribute class."""
__docformat__ = "restructuredtext en"

__copyright__ = """
Copyright (C) 2008-2013 Hendrikx-ITC B.V.

Distributed under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3, or (at your option) any later
version.  The full license is in the file COPYING, distributed as part of
this software.
"""
from psycopg2.extensions import adapt, register_adapter

from minerva.storage import datatype


class AttributeDescriptor():
    def __init__(self, name, data_type, description):
        self.name = name
        self.data_type = data_type
        self.description = description


class Attribute():
    """Describes one attribute of an attribute store."""
    def __init__(
            self, id, name, data_type, attribute_store_id,
            description):
        self.id = id
        self.attribute_store_id = attribute_store_id
        self.name = name
        self.description = description
        self.data_type = data_type

    def descriptor(self):
        return AttributeDescriptor(
            self.name, self.data_type, self.description
        )

    @classmethod
    def get(cls, id):
        """Load and return attribute by its Id."""
        def f(cursor):
            query = (
                "SELECT name, datatype, attributestore_id, description "
                "FROM attribute_directory.attribute "
                "WHERE id = %s"
            )
            args = id,
            cursor.execute(query, args)

            name, data_type, attribute_store_id, description = cursor.fetchone()

            return Attribute(
                id, name, datatype.type_map[data_type], attribute_store_id,
                description
            )

        return f

    @staticmethod
    def create(attribute_descriptor):
        """Create the attribute in the database."""
        def f(cursor):
            if attribute_store is None:
                raise Exception("attributestore not set")

            query = (
                "INSERT INTO attribute_directory.attribute "
                "(attributestore_id, name, datatype, description) "
                "VALUES (%s, %s, %s, %s) RETURNING *"
            )

            args = (
                attribute_descriptor.attribute_store.id,
                attribute_descriptor.name,
                attribute_descriptor.data_type.name,
                attribute_descriptor.description
            )

            cursor.execute(query, args)

            attribute_id, name, data_type, description = cursor.fetchone()

            return Attribute(
                attribute_id, name, datatype.type_map[data_type], description
            )

        return f

    def __repr__(self):
        return "<Attribute({0} {1})>".format(self.name, self.data_type)

    def __str__(self):
        return "{0.name}({0.datatype})".format(self)


def adapt_attribute(attribute):
    """Return psycopg2 compatible representation of `attribute`."""
    return adapt((
        attribute.id, attribute.attribute_store_id, attribute.description,
        attribute.name, attribute.data_type.name
    ))


register_adapter(Attribute, adapt_attribute)


def adapt_attribute_descriptor(attribute_descriptor):
    """Return psycopg2 compatible representation of `attribute`."""
    return adapt((
        attribute_descriptor.name,
        attribute_descriptor.data_type.name,
        attribute_descriptor.description
    ))


register_adapter(AttributeDescriptor, adapt_attribute_descriptor)
