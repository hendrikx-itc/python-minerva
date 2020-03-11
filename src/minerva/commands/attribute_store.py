import json
from contextlib import closing
import argparse
import sys

import psycopg2
import yaml

from minerva.db import connect
from minerva.util.tabulate import render_table


class DuplicateAttributeStore(Exception):
    def __init__(self, data_source, entity_type):
        self.data_source = data_source
        self.entity_type = entity_type

    def __str__(self):
        return 'Duplicate attribute store {}, {}'.format(
            self.data_source,
            self.entity_type,
        )


def setup_command_parser(subparsers):
    cmd = subparsers.add_parser(
        'attribute-store', help='command for administering attribute stores'
    )

    cmd_subparsers = cmd.add_subparsers()

    setup_create_parser(cmd_subparsers)
    setup_delete_parser(cmd_subparsers)
    setup_add_attribute_parser(cmd_subparsers)
    setup_remove_attribute_parser(cmd_subparsers)
    setup_show_parser(cmd_subparsers)
    setup_list_parser(cmd_subparsers)
    setup_materialization_parser(cmd_subparsers)


def setup_create_parser(subparsers):
    cmd = subparsers.add_parser(
        'create', help='command for creating attribute stores'
    )

    cmd.add_argument(
        '--data-source',
        help='name of the data source of the new attribute store'
    )

    cmd.add_argument(
        '--entity-type',
        help='name of the entity type of the new attribute store'
    )

    cmd.add_argument(
        '--from-json', type=argparse.FileType('r'),
        help='use json description for attribute store'
    )

    cmd.add_argument(
        '--from-yaml', type=argparse.FileType('r'),
        help='use yaml description for attribute store'
    )

    cmd.set_defaults(cmd=create_attribute_store_cmd)


def create_attribute_store_cmd(args):
    if args.from_json:
        attribute_store_config = json.load(args.from_json)
    elif args.from_yaml:
        attribute_store_config = yaml.load(
            args.from_yaml, Loader=yaml.SafeLoader
        )
    else:
        attribute_store_config = {
            'data_source': 'example_source',
            'entity_type': 'example_type',
            'attributes': []
        }

    if args.data_source:
        attribute_store_config['data_source'] = args.data_source

    if args.entity_type:
        attribute_store_config['entity_type'] = args.entity_type

    attribute_store_name = '{}_{}'.format(
        attribute_store_config['data_source'],
        attribute_store_config['entity_type']
    )

    sys.stdout.write(
        "Creating attribute store '{}'... ".format(attribute_store_name)
    )

    try:
        create_attribute_store_from_json(attribute_store_config)
        sys.stdout.write("OK\n")
    except DuplicateAttributeStore as exc:
        sys.stdout.write(exc)
    except Exception as exc:
        sys.stdout.write("Error:\n{}".format(exc))


def create_attribute_store_from_json(data):
    query = (
        'SELECT attribute_directory.create_attribute_store('
        '%s::text, %s::text, {}'
        ')'
    ).format(
        'ARRAY[{}]::attribute_directory.attribute_descr[]'.format(','.join([
            "('{}', '{}', '{}')".format(
                attribute['name'],
                attribute['data_type'],
                attribute.get('description', '')
            )
            for attribute in data['attributes']
        ]))
    )

    query_args = (
        data['data_source'], data['entity_type']
    )

    with closing(connect()) as conn:
        with closing(conn.cursor()) as cursor:
            try:
                cursor.execute(query, query_args)
            except psycopg2.errors.UniqueViolation as exc:
                raise DuplicateAttributeStore(
                    data['data_source'], data['entity_type']
                ) from exc

        conn.commit()


def setup_delete_parser(subparsers):
    cmd = subparsers.add_parser(
        'delete', help='command for deleting attribute stores'
    )

    cmd.add_argument('name', help='name of attribute store')

    cmd.set_defaults(cmd=delete_attribute_store_cmd)


def delete_attribute_store_cmd(args):
    query = (
        'SELECT attribute_directory.delete_attribute_store(%s::name)'
    )

    query_args = (
        args.name,
    )

    with closing(connect()) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute(query, query_args)

        conn.commit()


def setup_add_attribute_parser(subparsers):
    cmd = subparsers.add_parser(
        'add-attribute', help='add an attribute to an attribute store'
    )

    cmd.add_argument('-t', '--data-type')

    cmd.add_argument('-n', '--attribute-name')

    cmd.add_argument('-d', '--description')

    cmd.add_argument(
        'attribute_store',
        help='name of the attribute store where the attribute will be added'
    )

    cmd.set_defaults(cmd=add_attribute_to_attribute_store_cmd)


def add_attribute_to_attribute_store_cmd(args):
    query = (
        'SELECT attribute_directory.create_attribute('
        'attribute_store, %s::name, %s::text, %s::text'
        ') '
        'FROM attribute_directory.attribute_store '
        'WHERE attribute_store::text = %s'
    )

    query_args = (
        args.attribute_name, args.data_type, args.description,
        args.attribute_store
    )

    with closing(connect()) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute(query, query_args)

            print(cursor.fetchone())

        conn.commit()


def setup_remove_attribute_parser(subparsers):
    cmd = subparsers.add_parser(
        'remove-attribute', help='add an attribute to an attribute store'
    )

    cmd.add_argument(
        'attribute_store',
        help='attribute store from where the attribute should be removed'
    )

    cmd.add_argument(
        'attribute_name',
        help='name of the attribute that should be removed'
    )

    cmd.set_defaults(cmd=remove_attribute_from_attribute_store_cmd)


def remove_attribute_from_attribute_store_cmd(args):
    query = (
        'SELECT attribute_directory.drop_attribute('
        'attribute_store, %s::name'
        ') '
        'FROM attribute_directory.attribute_store '
        'WHERE attribute_store::text = %s'
    )

    query_args = (
        args.attribute_name, args.attribute_store
    )

    with closing(connect()) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute(query, query_args)

            print("Attribute removed")

        conn.commit()


def setup_show_parser(subparsers):
    cmd = subparsers.add_parser(
        'show', help='show information on attribute stores'
    )

    cmd.add_argument('attribute_store', help='Attribute store to show')

    cmd.add_argument(
        '--id', help='id of trend store', type=int
    )

    cmd.set_defaults(cmd=show_attribute_store_cmd)


def show_rows(column_names, rows):
    column_align = "<" * len(column_names)
    column_sizes = ["max"] * len(column_names)

    for line in render_table(column_names, column_align, column_sizes, rows):
        print(line)


def show_rows_from_cursor(cursor):
    show_rows([c.name for c in cursor.description], cursor.fetchall())


def show_attribute_store_cmd(args):
    query = (
        'SELECT '
        'atts.id, '
        'entity_type.name AS entity_type, '
        'data_source.name AS data_source '
        'FROM attribute_directory.attribute_store atts '
        'JOIN directory.entity_type ON entity_type.id = entity_type_id '
        'JOIN directory.data_source ON data_source.id = data_source_id'
    )

    query_args = []

    if args.id:
        query += ' WHERE atts.id = %s'
        query_args.append(args.id)
    else:
        query += ' WHERE atts::text = %s'
        query_args.append(args.attribute_store)

    with closing(connect()) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute(query, query_args)

            show_rows_from_cursor(cursor)


def setup_list_parser(subparsers):
    cmd = subparsers.add_parser(
        'list', help='list attribute stores'
    )

    cmd.set_defaults(cmd=list_attribute_stores_cmd)


def list_attribute_stores_cmd(args):
    query = (
        'SELECT '
        'atts::text as attribute_store, '
        'data_source.name as data_source, '
        'entity_type.name as entity_type '
        'FROM attribute_directory.attribute_store atts '
        'JOIN directory.data_source ON data_source.id = atts.data_source_id '
        'JOIN directory.entity_type ON entity_type.id = atts.entity_type_id'
    )

    query_args = []

    with closing(connect()) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute(query, query_args)

            show_rows_from_cursor(cursor)


def setup_materialization_parser(subparsers):
    cmd = subparsers.add_parser(
        'materialization', help='command for managing attribute materialization'
    )

    cmd_subparsers = cmd.add_subparsers()

    setup_create_materialization_parser(cmd_subparsers)
    setup_list_materialization_parser(cmd_subparsers)
    setup_run_materialization_parser(cmd_subparsers)


def setup_create_materialization_parser(subparsers):
    cmd = subparsers.add_parser(
        'create', help='command for creating attribute materialization'
    )

    cmd.add_argument(
        '--format', choices=['yaml', 'json'], default='yaml',
        help='format of definition'
    )

    cmd.add_argument(
        'definition', type=argparse.FileType('r'),
        help='file containing materialization definition'
    )

    cmd.set_defaults(cmd=create_materialization_cmd)


class SampledViewMaterialization:
    def __init__(self, attribute_store, query):
        self.attribute_store = attribute_store
        self.query = query

    def __str__(self):
        return '{}_{}'.format(
            self.attribute_store['data_source'],
            self.attribute_store['entity_type']
        )

    @staticmethod
    def from_json(data):
        return SampledViewMaterialization(
            data['attribute_store'],
            data['query']
        )

    def create(self, conn):
        view_name = '_{}_{}'.format(
            self.attribute_store['data_source'],
            self.attribute_store['entity_type']
        )

        query = (
            'CREATE VIEW attribute."{}" AS {}'
        ).format(view_name, self.query)

        insert_materialization_query = (
            'INSERT INTO attribute_directory.sampled_view_materialization(attribute_store_id, src_view) '
            'SELECT attribute_store.id, %s '
            'FROM attribute_directory.attribute_store '
            'JOIN directory.data_source ON attribute_store.data_source_id = data_source.id '
            'JOIN directory.entity_type ON attribute_store.entity_type_id = entity_type.id '
            'WHERE data_source.name = %s AND entity_type.name = %s'
        )

        insert_materialization_args = (
            'attribute."{}"'.format(view_name),
            self.attribute_store['data_source'],
            self.attribute_store['entity_type']
        )

        with closing(conn.cursor()) as cursor:
            cursor.execute(query)

            cursor.execute(
                insert_materialization_query,
                insert_materialization_args
            )


def create_materialization_cmd(args):
    print('Create attribute store materialization')

    if args.format == 'json':
        definition = json.load(args.definition)
    elif args.format == 'yaml':
        definition = yaml.load(args.definition, Loader=yaml.SafeLoader)

    materialization = SampledViewMaterialization.from_json(definition)

    with closing(connect()) as conn:
        conn.autocommit = True

        materialization.create(conn)


def setup_list_materialization_parser(subparsers):
    cmd = subparsers.add_parser(
        'list', help='command for listing attribute materializations'
    )

    group = cmd.add_mutually_exclusive_group()
    group.add_argument(
        '--name-only', action='store_true', default=False,
        help='output only names of materializations'
    )
    group.add_argument(
        '--id-only', action='store_true', default=False,
        help='output only Ids of materializations'
    )

    cmd.set_defaults(cmd=list_materializations_cmd)


def list_materializations_cmd(args):
    query = (
        "SELECT svm.id, svm.src_view, attribute_store::text "
        "FROM attribute_directory.sampled_view_materialization svm "
        "JOIN attribute_directory.attribute_store ON attribute_store.id = svm.attribute_store_id"
    )

    with closing(connect()) as conn:
        conn.autocommit = True

        with closing(conn.cursor()) as cursor:
            cursor.execute(query)

            rows = cursor.fetchall()

    if args.name_only:
        for id, src_view, attribute_store in rows:
            print(attribute_store)
    elif args.id_only:
        for id, src_view, attribute_store in rows:
            print(id)
    else:
        show_rows(
            ['id', 'src_view', 'attribute_store'],
            [
                (id, src_view, attribute_store)
                for id, src_view, attribute_store in rows
            ]
        )


def setup_run_materialization_parser(subparsers):
    cmd = subparsers.add_parser(
        'run', help='command for running attribute materializations'
    )

    cmd.add_argument('--id', help='Id of attribute materialization to run')

    cmd.add_argument(
        '--name',
        help='Name of target attribute store for which to run a materialization'
    )

    cmd.add_argument(
        '--materialize-curr', default=False, action='store_true',
        help='Update the attribute current pointer table after loading'
    )

    cmd.set_defaults(cmd=run_materialization_cmd)


def run_materialization_cmd(args):
    query = (
        "SELECT attribute_store::text, attribute_directory.materialize(svm) "
        "FROM attribute_directory.sampled_view_materialization svm "
        "JOIN attribute_directory.attribute_store "
        "ON attribute_store.id = svm.attribute_store_id "
    )

    if args.id:
        query += "WHERE svm.id = %s"
        query_args = (args.id,)
    elif args.name:
        query += "WHERE attribute_store::text = %s"
        query_args = (args.name,)

    with closing(connect()) as conn:
        conn.autocommit = True

        with conn.cursor() as cursor:
            cursor.execute(query, query_args)

            rows = cursor.fetchall()

        for attribute_store, row_count in rows:
            print('{}: {}'.format(attribute_store, row_count))

            if args.materialize_curr:
                print('Materializing curr ptr for {}'.format(attribute_store))
                materialize_curr_ptr(conn, attribute_store)


def materialize_curr_ptr(conn, attribute_store: str):
    materialize_curr_query = (
        'SELECT '
        'attribute_directory.materialize_curr_ptr(attribute_store) '
        'FROM attribute_directory.attribute_store '
        'WHERE attribute_store::text = %s'
    )

    with conn.cursor() as cursor:
        cursor.execute(materialize_curr_query, (attribute_store,))

    conn.commit()