"""
    tests.conftest
    ~~~~~~~~~~~~~~

    PyTest configuration for Drowsy tests.

    This is partially adapted from pytest-flask-sqlalchemy:
    https://github.com/jeancochrane/pytest-flask-sqlalchemy/

    Corresponding license (MIT) of that code can be found at:
    https://github.com/jeancochrane/pytest-flask-sqlalchemy/blob/master/LICENSE

"""
import contextlib
import pytest
import os
import sqlalchemy as sa
from packaging import version
from sqlalchemy.orm import sessionmaker, scoped_session
from unittest.mock import MagicMock
from sqlalchemy.engine.base import RootTransaction


def pytest_addoption(parser):
    """Add command line options for the test suite.

    :param parser: An argument parser object from pytest.
    :return: None

    """
    parser.addoption(
        "--db_types", action="store", default="sqlite",
        help="List of comma separated database types: all, sqlite, or mssql"
    )


def pytest_generate_tests(metafunc):
    """Generate tests for different database types.

    Uses command line `--db_types` option to figure out which tests
    to run against which database backends.

    :param metafunc: A Metafunc object from pytest, containing
        info about the test function or method being parameterized.
    :return: None

    """
    all_db_types = ["sqlite", "mssql", "postgres"]
    db_types = metafunc.config.getoption("db_types")
    db_types = db_types.lower().replace(" ", "").split(",")
    if metafunc.cls:
        if hasattr(metafunc.cls, "backends"):
            backends = metafunc.cls.backends
        else:
            backends = ["sqlite"]
    else:
        # default to sqlite when no class level backends provided
        backends = ["sqlite"]
    if "all" in db_types:
        db_types = all_db_types
    targets = list(set(db_types) & set(backends))
    if "_db" in metafunc.fixturenames:
        metafunc.parametrize("_db", targets, indirect=True)


@pytest.fixture(scope='function')
def _db(request):
    """Set up a database engine for this test run.

    Not meant for general use, is intended to be picked up by the
    :meth:`_transaction` fixture, and only that fixture.

    :param request: A pytest SubRequest object containing info about
        the specific test about to be run. Can be used to decide which
        database backend will be needed for this run.
    :return: A SQLAlchemy engine object.
    :rtype: :class:`~sa.engine.Engine`

    """
    server_types = ["mssql", "postgres"]
    if request.param in server_types:
        if request.param == 'mssql':
            connect_string = ("mssql+pyodbc://@localhost/Drowsy?"
                              "trusted_connection=yes&"
                              "driver=ODBC+Driver+17+for+SQL+Server")
            sqlstr_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "chinook_sqlserver.sql")
        elif request.param == 'postgres':
            connect_string = (
                "postgresql+psycopg2://postgres:drowsy@localhost/Drowsy")
            sqlstr_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "chinook_postgres.sql")
        else:
            raise ValueError("Database type tests not implemented.")
        engine = sa.create_engine(connect_string)
        tables = engine.execute(
            "SELECT Table_Name FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_TYPE='BASE TABLE'")
        tables_exist = False
        for table in tables:
            if table[0].lower() == "artist":
                tables_exist = True
                break
        if not tables_exist:
            with open(sqlstr_path, 'r', encoding='utf-8-sig') as sqlstr_file:
                sqlstr = sqlstr_file.read()
            with engine.begin() as conn:
                statements = sqlstr.split(";\n")
                for statement in statements:
                    if statement.strip():
                        conn.execute(statement)
    else:
        # default to sqlite
        db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "chinook.sqlite")
        connect_string = "sqlite+pysqlite:///" + db_path
        engine = sa.create_engine(connect_string, echo=True)
    return engine


@pytest.fixture(scope='function')
def db_session(_db):
    """Create a database session with automatic rollback.
    
    This fixture works with your existing _db fixture to provide
    a clean database session for each test. All changes made during
    the test will be automatically rolled back.
    
    :param _db: The database engine from your existing _db fixture
    :return: A SQLAlchemy session with rollback capability
    :rtype: :class:`~sqlalchemy.orm.Session`
    """
    # Create a sessionmaker bound to the engine
    SessionLocal = sessionmaker(bind=_db)
    
    # Start a connection and transaction
    connection = _db.connect()
    transaction = connection.begin()
    
    # Create session bound to the connection
    session = SessionLocal(bind=connection)
    
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
