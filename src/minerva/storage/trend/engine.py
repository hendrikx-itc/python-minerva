from contextlib import closing
from operator import contains
from functools import partial

from minerva.util import k, identity
from minerva.directory import EntityType
from minerva.storage import Engine
from minerva.storage.trend import TableTrendStore


class TrendEngine(Engine):
    @staticmethod
    def store_cmd(package, transform_package=k(identity)):
        """
        Return a function to bind a data source to the store command.

        :param package: A DataPackageBase subclass instance
        :param transform_package: (TableTrendStore) -> (DataPackage) -> DataPackage
        :return: function that binds a data source to the store command
        :rtype: (data_source) -> (conn) -> None
        """
        def bind_data_source(data_source):
            def execute(conn):
                trend_store = trend_store_for_package(
                    data_source, package
                )(conn)

                trend_store.store(
                    transform_package(trend_store)(package)
                ).run(conn)

            return execute

        return bind_data_source


def trend_store_for_package(data_source, package):
    def f(conn):
        entity_type_name = package.entity_type_name()

        with closing(conn.cursor()) as cursor:
            entity_type = EntityType.get_by_name(entity_type_name)(
                cursor
            )

            return TableTrendStore.get(
                data_source, entity_type, package.granularity
            )(cursor)

    return f


def filter_existing_trends(trend_store):
    """
    Return function that transforms a data package to only contain trends that
    are defined by *trend_store*.

    :param trend_store: trend store with defined trends
    :return: (DataPackage) -> DataPackage
    """
    existing_trend_names = {trend.name for trend in trend_store.trends}

    def f(package):
        return package.filter_trends(partial(contains, existing_trend_names))

    return f
