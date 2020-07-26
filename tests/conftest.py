import contextlib
import pytest
import os
import sqlalchemy as sa
from packaging import version
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock


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


@pytest.fixture(scope='session')
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
            connect_string = ("mssql+pypyodbc://@localhost/Drowsy?"
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
        engine = sa.create_engine(connect_string)
    return engine


@pytest.fixture(scope='function')
def _transaction(request, _db):
    """Create a safe transactional context for tests to run in.

    :param request: A pytest SubRequest object containing info about
        the specific test about to be run.
    :param _db: A SQLAlchemy Engine instance used to initiate a
        transaction.
    :type _db: :class:`~sa.engine.Engine`
    :return: A mocked SQLAlchemy engine object with overrides
        applied to prevent final commit from ever occurring.
    :rtype: :class:`~sa.engine.Engine`

    """
    # Start a transaction
    connection = _db.connect()
    transaction = connection.begin()
    # Bind a session to the transaction. The empty `binds` dict is
    # necessary when specifying a `bind` option.
    options = dict(bind=connection, binds={})
    session = sessionmaker(**options)()
    # Make sure the session, connection, and transaction can't be closed
    # by accident in the codebase
    connection.force_close = connection.close
    transaction.force_rollback = transaction.rollback
    connection.close = lambda: None
    transaction.rollback = lambda: None
    session.close = lambda: None
    # Begin a nested transaction (any new transactions created in the
    # codebase will be held until this outer transaction is committed or
    # closed)
    session.begin_nested()

    # Each time the SAVEPOINT for the nested transaction ends, reopen it
    @sa.event.listens_for(session, 'after_transaction_end')
    def restart_savepoint(session, trans):
        if trans.nested and not trans._parent.nested:
            # ensure that state is expired the way
            # session.commit() at the top level normally does
            session.expire_all()

            session.begin_nested()

    # Force the connection to use nested transactions
    connection.begin = connection.begin_nested

    # If an object gets moved to the 'detached' state by a call to
    # flush the session, add it back into the session (this allows us to
    # see changes made to objects in the context of a test, even when
    # the change was made elsewhere in the codebase)
    @sa.event.listens_for(session, 'persistent_to_detached')
    @sa.event.listens_for(session, 'deleted_to_detached')
    def rehydrate_object(session, obj):
        session.add(obj)

    @request.addfinalizer
    def teardown_transaction():
        # Delete the session
        # session.remove()
        # Rollback the transaction and return the connection to the pool
        transaction.force_rollback()
        connection.force_close()

    return connection, transaction, session


@pytest.fixture(scope='function')
def _engine(request, _transaction):
    """
    Mock out direct access to the semi-global Engine object.
    """
    connection, _, session = _transaction

    # Make sure that any attempts to call `connect()` simply return a
    # reference to the open connection
    engine = MagicMock(spec=sa.engine.Engine)
    engine.connect.return_value = connection

    # Threadlocal engine strategies were deprecated in SQLAlchemy 1.3, which
    # resulted in contextual_connect becoming a private method. See:
    # https://docs.sqlalchemy.org/en/latest/changelog/migration_13.html
    if version.parse(sa.__version__) < version.parse('1.3'):
        engine.contextual_connect.return_value = connection
    else:
        engine._contextual_connect.return_value = connection

    # References to `Engine.dialect` should redirect to the Connection (this
    # is primarily useful for the `autoload` flag in SQLAlchemy, which references
    # the Engine dialect to reflect tables)
    engine.dialect = connection.dialect

    @contextlib.contextmanager
    def begin():
        """
        Open a new nested transaction on the `connection` object.
        """
        with connection.begin_nested():
            yield connection

    # Force the engine object to use the current connection and transaction
    engine.begin = begin
    engine.execute = connection.execute
    engine.name = connection.dialect.name

    # Enforce nested transactions for raw DBAPI connections
    def raw_connection():
        # Start a savepoint
        connection.execute("""SAVEPOINT raw_conn""")

        # Preserve close/commit/rollback methods
        connection.connection.force_close = connection.connection.close
        connection.connection.force_commit = connection.connection.commit
        connection.connection.force_rollback = connection.connection.rollback

        # Prevent the connection from being closed accidentally
        connection.connection.close = lambda: None
        connection.connection.commit = lambda: None
        connection.connection.set_isolation_level = lambda level: None

        # If a rollback is initiated, return to the original savepoint
        connection.connection.rollback = lambda: connection.execute("""ROLLBACK TO SAVEPOINT raw_conn""")

        return connection.connection

    engine.raw_connection = raw_connection

    session.bind = engine

    @request.addfinalizer
    def reset_raw_connection():
        # Return the underlying connection to its original state if it has changed
        if hasattr(connection.connection, 'force_rollback'):
            connection.connection.commit = connection.connection.force_commit
            connection.connection.rollback = connection.connection.force_rollback
            connection.connection.close = connection.connection.force_close

    return engine


@pytest.fixture(scope='function')
def _session(_transaction):
    """
    Mock out Session objects (a common way of interacting with the database using
    the SQLAlchemy ORM) using a transactional context.
    """
    _, _, session = _transaction
    return session


@pytest.fixture(scope='function')
def db_session(_engine, _session, _transaction):
    """
    Make sure all the different ways that we access the database in the code
    are scoped to a transactional context, and return a Session object that
    can interact with the database in the tests.
    Use this fixture in tests when you would like to use the SQLAlchemy ORM
    API, just as you might use a SQLAlchemy Session object.
    """
    return _session


@pytest.fixture(scope='function')
def db_engine(_engine, _session, _transaction):
    """SQLAlchemy database engine fixture.

    Make sure all the different ways that we access the database in the
    code are scoped to a transactional context, and return an alias for
    the transactional Engine object that can interact with the database
    in the tests. Use this fixture in tests when you would like to run
    raw SQL queries using the SQLAlchemy Engine API.

    :param _engine:
    :param _session:
    :param _transaction:

    """
    return _engine
