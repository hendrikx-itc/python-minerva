CREATE CAST (trend_directory.trendstore AS text) WITH FUNCTION trend_directory.to_char(trend_directory.trendstore) AS IMPLICIT;

CREATE CAST (trend_directory.view AS text) WITH FUNCTION trend_directory.to_char(trend_directory.view) AS IMPLICIT;
