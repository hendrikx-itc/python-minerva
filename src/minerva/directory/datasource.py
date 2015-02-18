class DataSource():
    """
    A DataSource describes where a certain set of data comes from.
    """
    def __init__(self, id, name, description):
        self.id = id
        self.name = name
        self.description = description

    def __str__(self):
        return self.name

    @staticmethod
    def create(name, description):
        """
        Create new datasource
        :param cursor: cursor instance used to store into the Minerva database.
        :param name: identifying name of data source.
        :param description: A short description.
        """
        def f(cursor):
            query = (
                "INSERT INTO directory.datasource "
                "(id, name, description) "
                "VALUES (DEFAULT, %s, %s) RETURNING *"
            )

            args = name, description

            cursor.execute(query, args)

            return DataSource(*cursor.fetchone())

        return f

    @staticmethod
    def get(datasource_id):
        def f(cursor):
            """Return the datasource with the specified Id."""
            query = (
                "SELECT id, name, description "
                "FROM directory.datasource "
                "WHERE id=%s"
            )

            args = (datasource_id,)

            cursor.execute(query, args)

            if cursor.rowcount > 0:
                return DataSource(*cursor.fetchone())

        return f

    @staticmethod
    def get_by_name(name):
        def f(cursor):
            """Return the datasource with the specified name."""
            query = (
                "SELECT id, name, description "
                "FROM directory.datasource "
                "WHERE lower(name)=lower(%s)"
            )

            args = (name,)

            cursor.execute(query, args)

            if cursor.rowcount > 0:
                return DataSource(*cursor.fetchone())

        return f

    @staticmethod
    def from_name(name):
        def f(cursor):
            """Return new or existing datasource with name `name`."""
            cursor.callproc("directory.name_to_datasource", (name,))

            if cursor.rowcount > 0:
                return DataSource(*cursor.fetchone())

        return f