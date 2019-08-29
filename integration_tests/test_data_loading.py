# -*- coding: utf-8 -*-
"""
Comprehensive tests of loading data into a Minerva database.
"""
import datetime
import unittest
from contextlib import closing

import pytz

from minerva.storage.inputdescriptor import InputDescriptor
from minerva.storage.trend.tabletrendstorepart import TableTrendStorePart
from minerva.test import connect, clear_database
from minerva.directory import EntityType, DataSource
from minerva.storage.trend.granularity import create_granularity
from minerva.storage.trend.tabletrendstore import TableTrendStore
from minerva.storage.trend.trend import Trend
from minerva.storage.trend.datapackage import DefaultPackage
from minerva.storage import datatype
from minerva.util import merge_dicts


class TestStoreTrend(unittest.TestCase):
    def setUp(self):
        self.conn = clear_database(connect())

    def tearDown(self):
        self.conn.close()

    def test_defaults(self):
        data_descr = [
            {
                'name': 'x',
                'data_type': 'integer',
                'description': 'some integer value'
            },
            {
                'name': 'y',
                'data_type': 'double precision',
                'description': 'some floating point value'
            }
        ]
    
        data = [
            ('n=001', ['45', '4.332']),
            ('n=002', ['10', '1.001']),
            ('n=003', ['6089', '133.03']),
            ('n=004', ['', '234.33'])
        ]
    
        input_descriptors = [
            InputDescriptor.load(d) for d in data_descr
        ]
    
        parsed_data = [
            (dn, [
                descriptor.parse(raw_value)
                for raw_value, descriptor
                in zip(values, input_descriptors)
            ])
            for dn, values in data
        ]
    
        granularity = create_granularity("900 second")
        timestamp = pytz.utc.localize(datetime.datetime(2015, 2, 24, 20, 0))

        table_trend_store_part_descr = TableTrendStorePart.Descriptor(
            'test-trend-store',
            [
                Trend.Descriptor(
                    d['name'],
                    datatype.registry[d['data_type']],
                    d['description']
                )
                for d in data_descr
            ]
        )
    
        with closing(self.conn.cursor()) as cursor:
            data_source = DataSource.create("test-source", '')(cursor)
            entity_type = EntityType.create("test_type", '')(cursor)
    
            trend_store = TableTrendStore.create(TableTrendStore.Descriptor(
                data_source, entity_type, granularity,
                [table_trend_store_part_descr], 3600
            ))(cursor)
    
            trend_store.partition('test-trend-store', timestamp).create(cursor)
    
        self.conn.commit()
    
        data_package = DefaultPackage(
            granularity,
            timestamp,
            [d['name'] for d in data_descr],
            parsed_data
        )
    
        trend_store.store(data_package)(self.conn)
    
        self.conn.commit()
    
        # Check outcome
    
        query = (
            'SELECT x, y '
            'FROM trend."{}" '
            'ORDER BY entity_id'
        ).format(trend_store.part_by_name['test-trend-store'].base_table_name())
    
        with closing(self.conn.cursor()) as cursor:
            cursor.execute(query)
    
            rows = cursor.fetchall()
    
        self.assertEqual(len(rows), 4)
    
        self.assertEqual(rows[3][0], None)
        
    def test_nulls(self):
        data_descr = [
            {
                'name': 'x',
                'data_type': 'integer',
                'description': 'some integer value',
            },
            {
                'name': 'y',
                'data_type': 'double precision',
                'description': 'some floating point value',
            }
        ]
    
        input_descr = [
            {
                'name': 'y',
                'parser_config': {
                    'null_value': 'NULL'
                }
    
            }
        ]
    
        input_descr_lookup = {d['name']: d for d in input_descr}
    
        data = [
            ('test_nulls=001', ['45', '4.332']),
            ('test_nulls=002', ['10', '1.001']),
            ('test_nulls=003', ['6089', '133.03']),
            ('test_nulls=004', ['', 'NULL'])
        ]
    
        input_descriptors = [
            InputDescriptor.load(
                merge_dicts(d, input_descr_lookup.get(d['name']))
            )
            for d in data_descr
        ]
    
        parsed_data = [
            (dn, [
                descriptor.parse(raw_value)
                for raw_value, descriptor
                in zip(values, input_descriptors)
            ])
            for dn, values in data
        ]
    
        granularity = create_granularity("900 second")
        timestamp = pytz.utc.localize(datetime.datetime(2015, 2, 24, 20, 0))

        table_trend_store_part = TableTrendStorePart.Descriptor(
            'test-trend-store',
            [
                Trend.Descriptor(
                    d['name'],
                    datatype.registry[d['data_type']],
                    d['description']
                )
                for d in data_descr
            ]
        )

        with closing(self.conn.cursor()) as cursor:
            data_source = DataSource.create("test-source", '')(cursor)
            entity_type = EntityType.create("test_type", '')(cursor)
    
            trend_store = TableTrendStore.create(TableTrendStore.Descriptor(
                data_source, entity_type, granularity,
                [table_trend_store_part], 3600
            ))(cursor)
    
            trend_store.partition('test-trend-store', timestamp).create(cursor)
    
        self.conn.commit()
    
        data_package = DefaultPackage(
            granularity,
            timestamp,
            [d['name'] for d in data_descr],
            parsed_data
        )
    
        trend_store.store(data_package)(self.conn)
    
        self.conn.commit()
    
        # Check outcome
    
        query = (
            'SELECT x, y '
            'FROM trend."{}" '
            'ORDER BY entity_id'
        ).format(trend_store.part_by_name['test-trend-store'].base_table_name())
    
        with closing(self.conn.cursor()) as cursor:
            cursor.execute(query)
    
            rows = cursor.fetchall()
    
        self.assertEqual(len(rows), 4)
    
        self.assertEqual(rows[3][0], None)