-- View 'tagged_runnable_materializations'

CREATE VIEW materialization.tagged_runnable_materializations AS
    SELECT mstate.type_id, timestamp, t.name as tag
        FROM materialization.state mstate
        JOIN materialization.type_tag_link mtl ON mtl.type_id = mstate.type_id
        JOIN directory.tag t ON t.id = mtl.tag_id
        JOIN materialization.type mt ON mt.id = mstate.type_id
        JOIN trend_directory.trendstore ts ON ts.id = mt.dst_trendstore_id
        LEFT JOIN system.job j ON j.id = mstate.job_id
        WHERE
            materialization.requires_update(mstate)
            AND (j.id IS NULL OR NOT j.state IN ('queued', 'running'))
            AND materialization.runnable(mt, timestamp, max_modified)
        ORDER BY ts.granularity ASC, timestamp DESC;

ALTER VIEW materialization.tagged_runnable_materializations OWNER TO minerva_admin;

GRANT SELECT ON materialization.tagged_runnable_materializations TO minerva;


-- View 'materializable_source_state'

CREATE VIEW materialization.materializable_source_state AS
        SELECT
            mt.id AS type_id,
            trend_directory.get_timestamp_for(dst.granularity, mdf.timestamp) AS timestamp,
            mdf.trendstore_id,
            mdf.timestamp AS src_timestamp,
            mdf."end" AS modified
        FROM trend_directory.modified mdf
        JOIN trend_directory.view_trendstore_link vtl ON
                vtl.trendstore_id = mdf.trendstore_id
        JOIN trend_directory.view v ON
        v.id = vtl.view_id
        JOIN materialization.type mt ON
                mt.src_trendstore_id = v.trendstore_id
        JOIN trend_directory.trendstore dst ON
                dst.id = mt.dst_trendstore_id;

ALTER VIEW materialization.materializable_source_state OWNER TO minerva_admin;

GRANT SELECT ON materialization.materializable_source_state TO minerva;


-- View 'materializables'

CREATE VIEW materialization.materializables AS
    SELECT
        type_id,
        timestamp,
        max(modified) AS max_modified,
        array_agg(
            (
                (trendstore_id, src_timestamp)::materialization.source_fragment,
                modified
            )::materialization.source_fragment_state
            ORDER BY trendstore_id, src_timestamp
        ) AS source_states
    FROM materialization.materializable_source_state
    GROUP BY type_id, timestamp;

ALTER VIEW materialization.materializables OWNER TO minerva_admin;

GRANT ALL ON materialization.materializables TO minerva_admin;
GRANT SELECT ON materialization.materializables TO minerva;


-- View 'new_materializables'

CREATE VIEW materialization.new_materializables AS
    SELECT
        mzb.type_id,
        mzb.timestamp,
        mzb.max_modified,
        mzb.source_states
    FROM materialization.materializables mzb
    LEFT JOIN materialization.state ON
        state.type_id = mzb.type_id AND
        state.timestamp = mzb.timestamp
    WHERE state.type_id IS NULL;

ALTER VIEW materialization.new_materializables OWNER TO minerva_admin;

GRANT ALL ON materialization.new_materializables TO minerva_admin;
GRANT SELECT ON materialization.new_materializables TO minerva;


-- View 'modified_materializables'

CREATE VIEW materialization.modified_materializables AS
    SELECT
        mzb.type_id,
        mzb.timestamp,
        mzb.max_modified,
        mzb.source_states
    FROM materialization.materializables mzb
    JOIN materialization.state ON
        state.type_id = mzb.type_id AND
        state.timestamp = mzb.timestamp AND
        (state.source_states <> mzb.source_states OR state.source_states IS NULL);

ALTER VIEW materialization.modified_materializables OWNER TO minerva_admin;

GRANT ALL ON materialization.modified_materializables TO minerva_admin;
GRANT SELECT ON materialization.modified_materializables TO minerva;


-- View 'obsolete_state'

CREATE VIEW materialization.obsolete_state AS
    SELECT
        state.type_id,
        state.timestamp
    FROM materialization.state
    LEFT JOIN materialization.materializables mzs ON
        mzs.type_id = state.type_id AND
        mzs.timestamp = state.timestamp
    WHERE mzs.type_id IS NULL;

ALTER VIEW materialization.obsolete_state OWNER TO minerva_admin;

GRANT SELECT ON materialization.obsolete_state TO minerva;


-- View 'trend_ext'

CREATE VIEW materialization.trend_ext AS
SELECT
    t.id,
    t.name,
    ds.name AS datasource_name,
    et.name AS entitytype_name,
    ts.granularity,
    CASE
        WHEN m.src_trendstore_id IS NULL THEN false
        ELSE true
    END AS materialized
    FROM trend_directory.trend t
    JOIN trend_directory.trendstore ts ON ts.id = t.trendstore_id
    JOIN directory.datasource ds ON ds.id = ts.datasource_id
    JOIN directory.entitytype et ON et.id = ts.entitytype_id
    LEFT JOIN materialization.type m ON m.src_trendstore_id = ts.id;


ALTER VIEW materialization.trend_ext OWNER TO minerva_admin;

GRANT SELECT ON TABLE materialization.trend_ext TO minerva;


-- View 'required_resources_by_group'

CREATE VIEW materialization.required_resources_by_group AS
SELECT ttl.tag_id, sum((rm.type).cost) as required
FROM materialization.runnable_materializations rm
JOIN materialization.type_tag_link ttl ON ttl.type_id = (rm.type).id
JOIN materialization.group_priority gp ON gp.tag_id = ttl.tag_id
GROUP BY ttl.tag_id;

ALTER VIEW materialization.required_resources_by_group OWNER TO minerva_admin;
