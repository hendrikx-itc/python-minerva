import subprocess


def test_create_data_source(start_db_container):
    data_source_name = "test"

    proc = subprocess.run(['minerva', 'data-source', 'create', data_source_name])

    conn = start_db_container

    with conn.cursor() as cursor:
        cursor.execute("SELECT name FROM directory.data_source WHERE name = %s", (data_source_name,))

        name, = cursor.fetchone()

        assert name == data_source_name

    assert proc.returncode == 0

    proc = subprocess.run(['minerva', 'data-source', 'delete', data_source_name])

    with conn.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM directory.data_source WHERE name = %s", (data_source_name,))

        count, = cursor.fetchone()

        assert count == 0

    assert proc.returncode == 0
