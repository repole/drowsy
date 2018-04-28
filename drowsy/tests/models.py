## -*- coding: utf-8 -*-\
"""
    drowsy.tests.models.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    SQLAlchemy models for the Chinook database.

    :copyright: (c) 2016-2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, \
    Table, Unicode, orm, and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import ForeignKeyConstraint
from sqlalchemy.sql.sqltypes import NullType


Base = declarative_base()
metadata = Base.metadata


class Album(Base):

    """SQLAlchemy model for the Album table in our database."""

    __tablename__ = 'Album'

    album_id = Column("AlbumId", Integer, primary_key=True)
    title = Column("Title", Unicode(160), nullable=False)
    artist_id = Column(
        "ArtistId", ForeignKey('Artist.ArtistId'), nullable=False, index=True)

    artist = orm.relationship('Artist')


class Artist(Base):

    """SQLAlchemy model for the Artist table in our database."""

    __tablename__ = 'Artist'

    artist_id = Column("ArtistId", Integer, primary_key=True)
    name = Column("Name", Unicode(120))


class Customer(Base):

    """SQLAlchemy model for the Customer table in our database."""

    __tablename__ = 'Customer'

    customer_id = Column("CustomerId", Integer, primary_key=True)
    first_name = Column("FirstName", Unicode(40), nullable=False)
    last_name = Column("LastName", Unicode(20), nullable=False)
    company = Column("Company", Unicode(80))
    address = Column("Address", Unicode(70))
    city = Column("City", Unicode(40))
    state = Column("State", Unicode(40))
    country = Column("Country", Unicode(40))
    postal_code = Column("PostalCode", Unicode(10))
    phone = Column("Phone", Unicode(24))
    fax = Column("Fax", Unicode(24))
    email = Column("Email", Unicode(60), nullable=False)
    support_rep_id = Column(
        "SupportRepId", ForeignKey('Employee.EmployeeId'), index=True)

    employee = orm.relationship('Employee')


class Employee(Base):

    """SQLAlchemy model for the Employee table in our database."""

    __tablename__ = 'Employee'

    employee_id = Column("EmployeeId", Integer, primary_key=True)
    last_name = Column("LastName", Unicode(20), nullable=False)
    first_name = Column("FirstName", Unicode(20), nullable=False)
    title = Column("Title", Unicode(30))
    reports_to = Column(
        "ReportsTo", ForeignKey('Employee.EmployeeId'), index=True)
    birth_date = Column("BirthDate", DateTime)
    hire_date = Column("HireDate", DateTime)
    address = Column("Address", Unicode(70))
    city = Column("City", Unicode(40))
    state = Column("State", Unicode(40))
    country = Column("Country", Unicode(40))
    postal_code = Column("PostalCode", Unicode(10))
    phone = Column("Phone", Unicode(24))
    fax = Column("Fax", Unicode(24))
    email = Column("Email", Unicode(60))

    parent = orm.relationship('Employee', remote_side=[employee_id])


class Genre(Base):

    """SQLAlchemy model for the Genre table in our database."""

    __tablename__ = 'Genre'

    genre_id = Column("GenreId", Integer, primary_key=True)
    name = Column("Name", Unicode(120))


class Invoice(Base):

    """SQLAlchemy model for the Invoice table in our database."""

    __tablename__ = 'Invoice'

    invoice_id = Column("InvoiceId", Integer, primary_key=True)
    customer_id = Column(
        "CustomerId", ForeignKey('Customer.CustomerId'),
        nullable=False, index=True)
    invoice_date = Column("InvoiceDate", DateTime, nullable=False)
    billing_address = Column("BillingAddress", Unicode(70))
    billing_city = Column("BillingCity", Unicode(40))
    billing_state = Column("BillingState", Unicode(40))
    billing_country = Column("BillingCountry", Unicode(40))
    billing_postal_code = Column("BillingPostalCode", Unicode(10))
    total = Column("Total", Numeric(10, 2), nullable=False)

    customer = orm.relationship('Customer', backref="invoices")


class InvoiceLine(Base):

    """SQLAlchemy model for the InvoiceLine table in our database."""

    __tablename__ = 'InvoiceLine'

    invoice_line_id = Column("InvoiceLineId", Integer, primary_key=True)
    invoice_id = Column(
        "InvoiceId", ForeignKey('Invoice.InvoiceId'),
        nullable=False, index=True)
    track_id = Column(
        "TrackId", ForeignKey('Track.TrackId'),
        nullable=False, index=True)
    unit_price = Column("UnitPrice", Numeric(10, 2), nullable=False)
    quantity = Column("Quantity", Integer, nullable=False)

    invoice = orm.relationship('Invoice')
    track = orm.relationship('Track')


class MediaType(Base):

    """SQLAlchemy model for the MediaType table in our database."""

    __tablename__ = 'MediaType'

    media_type_id = Column("MediaTypeId", Integer, primary_key=True)
    name = Column("Name", Unicode(120))


class Playlist(Base):

    """SQLAlchemy model for the Playlist table in our database."""

    __tablename__ = 'Playlist'

    playlist_id = Column("PlaylistId", Integer, primary_key=True)
    name = Column("Name", Unicode(120))

    tracks = orm.relationship(
        'Track', secondary='PlaylistTrack', backref="playlists")


t_PlaylistTrack = Table(
    'PlaylistTrack', metadata,
    Column(
        'PlaylistId',
        ForeignKey('Playlist.PlaylistId'),
        primary_key=True,
        nullable=False),
    Column(
        'TrackId',
        ForeignKey('Track.TrackId'),
        primary_key=True,
        nullable=False,
        index=True)
)


class Track(Base):

    """SQLAlchemy model for the Track table in our database."""

    __tablename__ = 'Track'

    track_id = Column("TrackId", Integer, primary_key=True)
    name = Column("Name", Unicode(200), nullable=False)
    album_id = Column("AlbumId", ForeignKey('Album.AlbumId'), index=True)
    media_type_id = Column(
        "MediaTypeId", ForeignKey('MediaType.MediaTypeId'),
        nullable=False, index=True)
    genre_id = Column("GenreId", ForeignKey('Genre.GenreId'), index=True)
    composer = Column("Composer", Unicode(220))
    milliseconds = Column("Milliseconds", Integer, nullable=False)
    bytes = Column("Bytes", Integer)
    unit_price = Column("UnitPrice", Numeric(10, 2), nullable=False)

    album = orm.relationship('Album', backref="tracks")
    genre = orm.relationship('Genre')
    media_type = orm.relationship('MediaType')


t_CompositeNodeToCompositeNode = Table(
    'CompositeNodeToCompositeNode', metadata,
    Column(
        'NodeId',
        primary_key=True,
        nullable=False),
    Column(
        'CompositeId',
        primary_key=True,
        nullable=False),
    Column(
        'ChildNodeId',
        primary_key=True,
        nullable=False),
    Column(
        'ChildCompositeId',
        primary_key=True,
        nullable=False),
    ForeignKeyConstraint(
        ['NodeId', 'CompositeId'],
        ['CompositeNode.NodeId', 'CompositeNode.CompositeId']),
    ForeignKeyConstraint(
        ['ChildNodeId', 'ChildCompositeId'],
        ['CompositeNode.NodeId', 'CompositeNode.CompositeId'])
)


t_NodeToNode = Table(
    'NodeToNode', metadata,
    Column(
        'NodeId',
        ForeignKey('Node.NodeId'),
        primary_key=True,
        nullable=False),
    Column(
        'ChildNodeId',
        ForeignKey('Node.NodeId'),
        primary_key=True,
        nullable=False)
)


class Node(Base):

    """SQLAlchemy model for the Node table in our database."""

    __tablename__ = 'Node'

    node_id = Column("NodeId", Integer, primary_key=True)

    children = orm.relationship(
        'Node',
        secondary=t_NodeToNode,
        primaryjoin=node_id == t_NodeToNode.c.ChildNodeId,
        secondaryjoin=node_id == t_NodeToNode.c.NodeId,
        backref="parents")


class CompositeNode(Base):

    """SQLAlchemy model for the CompositeNode table in our database."""

    __tablename__ = 'CompositeNode'

    node_id = Column("NodeId", Integer, primary_key=True)
    composite_id = Column("CompositeId", Integer, primary_key=True)

    children = orm.relationship(
        'CompositeNode',
        secondary=t_CompositeNodeToCompositeNode,
        primaryjoin=and_(
            t_CompositeNodeToCompositeNode.c.ChildNodeId == node_id,
            t_CompositeNodeToCompositeNode.c.ChildCompositeId == composite_id),
        secondaryjoin=and_(
            t_CompositeNodeToCompositeNode.c.NodeId == node_id,
            t_CompositeNodeToCompositeNode.c.CompositeId == composite_id),
        backref="parents")


t_sqlite_sequence = Table(
    'sqlite_sequence', metadata,
    Column('name', NullType),
    Column('seq', NullType)
)
