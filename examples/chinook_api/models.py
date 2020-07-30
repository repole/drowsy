"""
    chinook_api.models
    ~~~~~~~~~~~~~~~~~~

    SQLAlchemy models for the Chinook database.

"""
# :copyright: (c) 2020 by Nicholas Repole and contributors.
#             See AUTHORS for more details.
# :license: MIT - See LICENSE for more details.
from sqlalchemy import (
    Column, DateTime, ForeignKey, Integer, Table, Unicode, orm, and_, Float
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref
from sqlalchemy.schema import ForeignKeyConstraint

Base = declarative_base()
metadata = Base.metadata


class Album(Base):

    """SQLAlchemy model for the Album table in our database."""

    __tablename__ = 'Album'

    album_id = Column("AlbumId", Integer, primary_key=True)
    title = Column("Title", Unicode(160), nullable=False)
    artist_id = Column(
        "ArtistId", ForeignKey('Artist.ArtistId'), nullable=False, index=True)

    artist = orm.relationship('Artist', backref="albums")


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
    state = Column("State", Unicode(40), doc="Two Character Abbreviation")
    country = Column("Country", Unicode(40))
    postal_code = Column("PostalCode", Unicode(10))
    phone = Column("Phone", Unicode(24))
    fax = Column("Fax", Unicode(24))
    email = Column("Email", Unicode(60), nullable=False)
    support_rep_id = Column(
        "SupportRepId", ForeignKey('Employee.EmployeeId'), index=True)

    employee = orm.relationship('Employee', backref="customers")


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

    manager = orm.relationship('Employee', remote_side=[employee_id],
                               backref="subordinates")


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
    total = Column("Total", Float, nullable=False)

    customer = orm.relationship(
        'Customer',
        backref="invoices",
        primaryjoin=customer_id == Customer.customer_id)


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
    unit_price = Column("UnitPrice", Float, nullable=False)
    quantity = Column("Quantity", Integer, nullable=False)

    invoice = orm.relationship('Invoice', backref=backref(
        "invoice_lines", cascade="all, delete-orphan"))
    track = orm.relationship('Track', backref=backref(
        "invoice_lines", cascade="all, delete-orphan"))


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
    unit_price = Column("UnitPrice", Float, nullable=False)

    album = orm.relationship('Album', backref=backref(
        "tracks", cascade="all, delete-orphan"))
    genre = orm.relationship('Genre', backref="tracks")
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
        primaryjoin=node_id == t_NodeToNode.c.NodeId,
        secondaryjoin=node_id == t_NodeToNode.c.ChildNodeId,
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
            t_CompositeNodeToCompositeNode.c.NodeId == node_id,
            t_CompositeNodeToCompositeNode.c.CompositeId == composite_id),
        secondaryjoin=and_(
            t_CompositeNodeToCompositeNode.c.ChildNodeId == node_id,
            t_CompositeNodeToCompositeNode.c.ChildCompositeId == composite_id),
        backref="parents")


class CompositeOne(Base):

    """Dummy model for one side of one to many composite key testing."""

    __tablename__ = "CompositeOne"

    one_id = Column("OneId", Integer, primary_key=True)
    composite_one_id = Column("CompositeOneId", Integer, primary_key=True)


class CompositeMany(Base):
    """Model for many side of one to many composite key testing."""

    __tablename__ = "CompositeMany"

    many_id = Column("ManyId", Integer, primary_key=True)
    one_id = Column("OneId", Integer)
    composite_one_id = Column("CompositeOneId", Integer)

    one = orm.relationship('CompositeOne', backref="many")

    __table_args__ = (
        ForeignKeyConstraint(
            ['OneId', 'CompositeOneId'],
            ['CompositeOne.OneId', 'CompositeOne.CompositeOneId']
        ),
    )
