
import re
import sqlite3

from backend.app.config import DATASET_DIR


# Which roles can query which database tables
SQL_ROLE_TABLE_ACCESS = {
    "general_counsel": [
        "contracts_register",
        "litigation_cases"
    ],
    "corporate_counsel": [
        "contracts_register"
    ],
    "litigation_counsel": [],
    "compliance_officer": [],
    "paralegal": []
}


# Convert role names into a consistent format
def normalise_role(role: str) -> str:
    return role.strip().lower().replace(" ", "_")


# Return the database tables permitted for a role
def get_allowed_tables(role: str) -> list:
    normalised_role = normalise_role(role)
    return SQL_ROLE_TABLE_ACCESS.get(normalised_role, [])


# Validate that SQL is a read-only SELECT query
def validate_select_query(sql_query: str):
    if not isinstance(sql_query, str) or not sql_query.strip():
        raise ValueError("SQL query cannot be empty")

    # Reject queries containing null characters
    if "\x00" in sql_query:
        raise ValueError("SQL query contains invalid characters")

    # Only SELECT or WITH queries are accepted
    if not re.match(
        r"^\s*(SELECT|WITH)\b",
        sql_query,
        re.IGNORECASE
    ):
        raise ValueError("Only SELECT queries are permitted")


# Execute SQL using role-based and matter-based restrictions
def execute_scoped_select(sql_query: str, user: dict) -> list:

    role = user.get("role", "")
    user_matters = user.get("matters", [])

    # Check which tables this role can access
    allowed_tables = get_allowed_tables(role)

    if not allowed_tables:
        raise PermissionError(
            "Your role is not permitted to access SQL data"
        )

    # Validate the SQL before execution
    validate_select_query(sql_query)

    # Open the database in read-only mode
    database = DATASET_DIR / "veridian_legal.db"

    connection = sqlite3.connect(
        f"{database.as_uri()}?mode=ro",
        uri=True
    )

    connection.row_factory = sqlite3.Row

    try:
        # Create a temporary table containing permitted matters
        connection.execute(
            """
            CREATE TEMP TABLE allowed_matters (
                matter_id TEXT PRIMARY KEY
            )
            """
        )

        # General Counsel has access to every matter
        is_general_counsel = "*" in user_matters

        if not is_general_counsel:
            connection.executemany(
                """
                INSERT INTO allowed_matters (matter_id)
                VALUES (?)
                """,
                [(matter,) for matter in user_matters]
            )

        # Create temporary filtered views for permitted tables
        view_names = set()

        for table_name in allowed_tables:

            view_name = f"{table_name}_scoped"
            view_names.add(view_name)

            if is_general_counsel:
                filter_condition = "1 = 1"

            else:
                filter_condition = """
                    matter_id = 'NONE'
                    OR matter_id IN (
                        SELECT matter_id FROM allowed_matters
                    )
                """

            connection.execute(
                f"""
                CREATE TEMP VIEW {view_name} AS
                SELECT *
                FROM {table_name}
                WHERE {filter_condition}
                """
            )

        # SQLite security authorizer
        def authorise_query(
            action,
            arg1,
            arg2,
            database_name,
            source
        ):

            # Allow SELECT operations
            if action == sqlite3.SQLITE_SELECT:
                return sqlite3.SQLITE_OK

            # Allow recursive SELECT operations
            if action == sqlite3.SQLITE_RECURSIVE:
                return sqlite3.SQLITE_OK

            # Allow normal SQL functions, but block load_extension
            if action == sqlite3.SQLITE_FUNCTION:

                if (arg2 or "").lower() == "load_extension":
                    return sqlite3.SQLITE_DENY

                return sqlite3.SQLITE_OK

            # Control which database tables can be read
            if action == sqlite3.SQLITE_READ:

                # Allow direct reading of permitted temporary views
                if (
                    database_name == "temp"
                    and arg1 in view_names
                    and source is None
                ):
                    return sqlite3.SQLITE_OK

                # Allow original tables only when accessed through
                # their authorised scoped views
                if (
                    database_name == "main"
                    and arg1 in allowed_tables
                    and source in view_names
                ):
                    return sqlite3.SQLITE_OK

                # Allow the matter filter table only inside scoped views
                if (
                    database_name == "temp"
                    and arg1 == "allowed_matters"
                    and source in view_names
                ):
                    return sqlite3.SQLITE_OK

                return sqlite3.SQLITE_DENY

            # Deny every other database operation
            return sqlite3.SQLITE_DENY

        # Activate SQLite's security authorizer
        connection.set_authorizer(authorise_query)

        # sqlite3.execute() accepts only one SQL statement.
        # Multiple statements are rejected by SQLite.
        cursor = connection.execute(sql_query)

        results = [
            dict(row)
            for row in cursor.fetchall()
        ]

        return results

    finally:
        # Always close the database connection
        connection.close()
