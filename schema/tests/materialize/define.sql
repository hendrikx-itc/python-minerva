BEGIN;

SELECT plan(2);


SELECT trend.create_trendstore(
    'test-data',
    'Node',
    '900',
    ARRAY[
        ('x', 'integer', 'some column with integer values')
    ]::trend.trend_descr[]
);


SELECT materialization.define(
    trend.create_view(
        trend.define_view(
        trend.attributes_to_view_trendstore('vtest', 'Node', '900'),
        $view_def$SELECT
    id(directory.dn_to_entity('Network=G01,Node=A001')) entity_id,
    '2015-01-21 15:00'::timestamp with time zone AS timestamp,
    now() AS modified,
    42 AS x$view_def$
        )
    )
);


SELECT has_table(
    'trend',
    'test_Node_qtr',
    'materialized trend table should exist'
);


SELECT throws_matching(
    $query$
    SELECT materialization.define(
        trend.create_view(
            trend.define_view(
            trend.attributes_to_view_trendstore('test-wrong-name', 'Node', '900'),
            $$SELECT
        id(directory.dn_to_entity('Network=G01,Node=A001')) entity_id,
        '2015-01-21 15:00'::timestamp with time zone AS timestamp,
        now() AS modified,
        42 AS x$$
            )
        )
    );
    $query$,
    'does not start with a ''v'''
);

SELECT * FROM finish();
ROLLBACK;
