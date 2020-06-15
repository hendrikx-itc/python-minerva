# -*- coding: utf-8 -*-
from __future__ import annotations
from contextlib import closing
from typing import List, Callable, Any

from psycopg2.extensions import cursor

from minerva.db.query import Column, Eq, ands

from minerva.storage.trend import schema
from minerva.directory import DataSource, EntityType
from minerva.storage.trend.granularity import create_granularity, Granularity
from minerva.storage.trend.trendstorepart import TrendStorePart
from minerva.util import string_fns


class NoSuchTrendStore(Exception):
    data_source: DataSource
    entity_type: EntityType
    granularity: Granularity

    def __init__(self, data_source: DataSource, entity_type: EntityType, granularity: Granularity):
        self.data_source = data_source
        self.entity_type = entity_type
        self.granularity = granularity

    def __str__(self) -> str:
        return 'No such trend store {}, {}, {}'.format(
            self.data_source.name,
            self.entity_type.name,
            self.granularity
        )


class TrendStore:
    class Descriptor:
        data_source: DataSource
        entity_type: EntityType
        granularity: Granularity
        parts: List[TrendStorePart.Descriptor]
        partition_size: int

        def __init__(
                self, data_source: DataSource, entity_type: EntityType,
                granularity: Granularity,
                parts: List[TrendStorePart.Descriptor],
                partition_size: int):
            self.data_source = data_source
            self.entity_type = entity_type
            self.granularity = granularity
            self.parts = parts
            self.partition_size = partition_size

    partition_size: int
    parts: List[TrendStorePart]

    column_names = [
        "id", "entity_type_id", "data_source_id", "granularity",
        "partition_size", "retention_period"
    ]

    columns = list(map(Column, column_names))

    get_query = schema.trend_store.select(columns).where_(ands([
        Eq(Column("data_source_id")),
        Eq(Column("entity_type_id")),
        Eq(Column("granularity"))
    ]))

    get_by_id_query = schema.trend_store.select(
        columns
    ).where_(Eq(Column("id")))

    def __init__(
            self, id_: int, data_source: DataSource, entity_type: EntityType,
            granularity: Granularity, partition_size: int, retention_period):
        self.id = id_
        self.data_source = data_source
        self.entity_type = entity_type
        self.granularity = granularity
        self.partition_size = partition_size
        self.retention_period = retention_period
        self.parts = []
        self.part_by_name = None
        self._trend_part_mapping = None

    @staticmethod
    def create(descriptor: Descriptor) -> Callable[[cursor], TrendStore]:
        def f(cursor):
            parts_sql = "ARRAY[{}]::trend_directory.trend_store_part_descr[]".format(
                ','.join([
                    "('{}', {})".format(
                        part.name,
                        'ARRAY[{}]::trend_directory.trend_descr[]'.format(
                            ','.join([
                                "('{}', '{}', '')".format(
                                    trend_descriptor.name,
                                    trend_descriptor.data_type.name,
                                    ''
                                )
                                for trend_descriptor in part.trend_descriptors
                            ]))
                    )
                    for part in descriptor.parts
                ]))

            args = (
                descriptor.data_source.name,
                descriptor.entity_type.name,
                str(descriptor.granularity),
                descriptor.partition_size
            )

            query = (
                "SELECT * FROM trend_directory.create_trend_store("
                "%s, %s, %s, %s, {parts}"
                ")"
            ).format(parts=parts_sql)

            cursor.execute(query, args)

            return TrendStore.from_record(cursor.fetchone())(cursor)

        return f

    def load_parts(self, cursor):
        query = (
            "SELECT id, trend_store_id, name "
            "FROM trend_directory.trend_store_part "
            "WHERE trend_store_id = %s"
        )

        args = (self.id,)

        cursor.execute(query, args)

        self.parts = [
            TrendStorePart.from_record(record, self)(cursor)
            for record in cursor.fetchall()
        ]

        self.part_by_name = {
            part.name: part for part in self.parts
        }

        self._trend_part_mapping = {
            trend.name: part for part in self.parts for trend in part.trends
        }

        return self

    @staticmethod
    def from_record(record) -> Callable[[Any], Any]:
        """
        Return function that can instantiate a TrendStore from a
        trend_store type record.
        :param record: An iterable that represents a trend_store record
        :return: function that creates and returns TrendStore object
        """
        def f(cursor):
            (
                trend_store_id, entity_type_id, data_source_id,
                granularity_str, partition_size, retention_period
            ) = record

            entity_type = EntityType.get(entity_type_id)(cursor)
            data_source = DataSource.get(data_source_id)(cursor)

            return TrendStore(
                trend_store_id, data_source, entity_type,
                create_granularity(granularity_str), partition_size,
                retention_period
            ).load_parts(cursor)

        return f

    @classmethod
    def get(cls, data_source, entity_type, granularity):
        def f(cursor):
            args = data_source.id, entity_type.id, str(granularity)

            cls.get_query.execute(cursor, args)

            if cursor.rowcount > 1:
                raise Exception(
                    "more than 1 ({}) trend store matches".format(
                        cursor.rowcount
                    )
                )
            elif cursor.rowcount == 1:
                return TrendStore.from_record(cursor.fetchone())(cursor)

        return f

    @classmethod
    def get_by_id(cls, id_):
        def f(conn):
            args = (id_,)

            with closing(conn.cursor()) as cursor:
                cls.get_by_id_query.execute(cursor, args)

                if cursor.rowcount == 1:
                    return TrendStore.from_record(cursor.fetchone())(cursor)

        return f

    def save(self, cursor):
        args = (
            self.data_source.id, self.entity_type.id, self.granularity.name,
            self.partition_size, self.id
        )

        query = (
            "UPDATE trend_directory.trend_store SET "
            "data_source_id = %s, "
            "entity_type_id = %s, "
            "granularity = %s, "
            "partition_size = %s "
            "WHERE id = %s"
        )

        cursor.execute(query, args)

        return self

    def store(self, data_package, description):
        return string_fns([
            part.store(package_part, description)
            for part, package_part in self.split_package_by_parts(data_package)
        ])

    def split_package_by_parts(self, data_package):
        def group_fn(trend_name):
            try:
                return self._trend_part_mapping[trend_name].name
            except KeyError:
                return None

        return [
            (self.part_by_name[part_name], package)
            for part_name, package in data_package.split(group_fn) if part_name
        ]

    def clear_timestamp(self, timestamp):
        def f(cursor):
            query = (
                "SELECT trend_directory.clear_timestamp(trend_store, %s) "
                "FROM trend_directory.trend_store "
                "WHERE id = %s"
            )

            args = timestamp, self.id

            cursor.execute(query, args)

        return f
