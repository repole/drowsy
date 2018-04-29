"""
    drowsy.tests.test_query_builder
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Query builder tests for Drowsy.

    :copyright: (c) 2016-2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from __future__ import unicode_literals
import json
from drowsy.exc import BadRequestError
from drowsy.query_builder import QueryBuilder
from drowsy.parser import SubfilterInfo, OffsetLimitInfo, SortInfo
from drowsy.tests.base import DrowsyTests
from drowsy.tests.models import Album, CompositeNode, Track, Customer
from drowsy.tests.resources import (
    AlbumResource, PlaylistResource, TrackResource, CompositeNodeResource,
    CustomerResource)

from sqlalchemy.inspection import inspect


class DrowsyQueryBuilderTests(DrowsyTests):

    """Test drowsy query building."""

    def test_apply_sorts_simple(self):
        """Test applying a single sort."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album)
        query = query_builder.apply_sorts(
            query=query,
            sorts=[SortInfo(attr="album_id", direction="ASC")]
        )
        results = query.all()
        last_album_id = -1
        for result in results:
            self.assertTrue(result.album_id >= last_album_id)
            last_album_id = result.album_id

    def test_apply_sorts_fail(self):
        """Test applying a single sort."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album)
        self.assertRaises(
            AttributeError,
            query_builder.apply_sorts,
            query=query,
            sorts=[SortInfo(attr="badattr", direction="ASC")]
        )

    def test_simple_subfilter(self):
        """Test applying a simple subfilter."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": 5}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters=subfilters,
            embeds=[]
        )
        albums = query.all()
        for album in albums:
            self.assertTrue(len(album.tracks) <= 1)
            if album.tracks:
                self.assertTrue(album.tracks[0].track_id == 5)

    def test_simple_subfilter_limit_offset(self):
        """Test offset and limit in a subresource."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 5}},
                offset_limit_info=OffsetLimitInfo(offset=1, limit=1)
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )
        expected_query = (
            "SELECT Album.AlbumId AS Album_AlbumId, Album.Title AS "
            "Album_Title, Album.ArtistId AS Album_ArtistId, anon_1.TrackId "
            "AS anon_1_TrackId, anon_1.Name AS anon_1_Name, anon_1.AlbumId AS "
            "anon_1_AlbumId, anon_1.MediaTypeId AS anon_1_MediaTypeId, "
            "anon_1.GenreId AS anon_1_GenreId, anon_1.Composer AS "
            "anon_1_Composer, anon_1.Milliseconds AS anon_1_Milliseconds, "
            "anon_1.Bytes AS anon_1_Bytes, anon_1.UnitPrice AS "
            "anon_1_UnitPrice "
            "FROM Album LEFT OUTER JOIN (SELECT q1.TrackId AS TrackId, "
            "q1.Name AS Name, q1.AlbumId AS AlbumId, q1.MediaTypeId AS "
            "MediaTypeId, q1.GenreId AS GenreId, q1.Composer AS Composer, "
            "q1.Milliseconds AS Milliseconds, q1.Bytes AS Bytes, "
            "q1.UnitPrice AS UnitPrice, q1.row_number AS row_number "
            "FROM (SELECT Track1.TrackId AS TrackId, Track1.Name AS Name, "
            "Track1.AlbumId AS AlbumId, Track1.MediaTypeId AS MediaTypeId, "
            "Track1.GenreId AS GenreId, Track1.Composer AS Composer, "
            "Track1.Milliseconds AS Milliseconds, Track1.Bytes AS Bytes, "
            "Track1.UnitPrice AS UnitPrice, row_number() OVER (PARTITION "
            "BY Track1.AlbumId ORDER BY Track1.TrackId ASC) AS row_number "
            "FROM Track AS Track1) AS q1, Track AS Track1 "
            "WHERE q1.row_number >= ? AND q1.row_number <= ? AND "
            "Track1.TrackId >= ?) AS anon_1 ON Album.AlbumId = anon_1.AlbumId"
        )
        result = str(query).replace('"', "").replace("\n", "")
        self.assertTrue(result == expected_query)

    def test_subfilter_limit_offset_sorts(self):
        """Test subfiltering with sorts works with limit and offset."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 5}},
                offset_limit_info=OffsetLimitInfo(offset=1, limit=1),
                sorts=[SortInfo(attr="name", direction="ASC")]
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )
        expected_query = (
            "SELECT Album.AlbumId AS Album_AlbumId, Album.Title AS "
            "Album_Title, Album.ArtistId AS Album_ArtistId, anon_1.TrackId "
            "AS anon_1_TrackId, anon_1.Name AS anon_1_Name, anon_1.AlbumId AS "
            "anon_1_AlbumId, anon_1.MediaTypeId AS anon_1_MediaTypeId, "
            "anon_1.GenreId AS anon_1_GenreId, anon_1.Composer AS "
            "anon_1_Composer, anon_1.Milliseconds AS anon_1_Milliseconds, "
            "anon_1.Bytes AS anon_1_Bytes, anon_1.UnitPrice AS "
            "anon_1_UnitPrice "
            "FROM Album LEFT OUTER JOIN (SELECT q1.TrackId AS TrackId, "
            "q1.Name AS Name, q1.AlbumId AS AlbumId, q1.MediaTypeId AS "
            "MediaTypeId, q1.GenreId AS GenreId, q1.Composer AS Composer, "
            "q1.Milliseconds AS Milliseconds, q1.Bytes AS Bytes, "
            "q1.UnitPrice AS UnitPrice, q1.row_number AS row_number "
            "FROM (SELECT Track1.TrackId AS TrackId, Track1.Name AS Name, "
            "Track1.AlbumId AS AlbumId, Track1.MediaTypeId AS MediaTypeId, "
            "Track1.GenreId AS GenreId, Track1.Composer AS Composer, "
            "Track1.Milliseconds AS Milliseconds, Track1.Bytes AS Bytes, "
            "Track1.UnitPrice AS UnitPrice, row_number() OVER (PARTITION "
            "BY Track1.AlbumId ORDER BY Track1.Name ASC) AS row_number "
            "FROM Track AS Track1) AS q1, Track AS Track1 "
            "WHERE q1.row_number >= ? AND q1.row_number <= ? AND "
            "Track1.TrackId >= ?) AS anon_1 ON Album.AlbumId = anon_1.AlbumId"
        )
        result = str(query).replace('"', "")
        result = result.replace("\n", "")
        self.assertTrue(result == expected_query)

    def test_subfilter_sorts_no_limit_offset_fail(self):
        """Check that subresource sorts without limit or offset fail."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                sorts=[SortInfo(attr="track_id", direction="ASC")]
            )
        }
        self.assertRaisesCode(
            BadRequestError,
            "invalid_subresource_sorts",
            query_builder.apply_subquery_loads,
            query=query,
            resource=AlbumResource(
                session=self.db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )

    def test_simple_subfilter_limit_too_big(self):
        """Check that a limit too large on subresource fails."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Customer)
        subfilters = {
            "invoices": SubfilterInfo(
                offset_limit_info=OffsetLimitInfo(offset=1, limit=10000)
            )
        }
        self.assertRaisesCode(
            BadRequestError,
            "invalid_subresource_limit",
            query_builder.apply_subquery_loads,
            query=query,
            resource=CustomerResource(
                session=self.db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )

    def test_subfilter_invalid_fail(self):
        """Check that bad subresource filters fail."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$bad": 5}}
            )
        }
        self.assertRaisesCode(
            BadRequestError,
            "invalid_subresource_filters",
            query_builder.apply_subquery_loads,
            query=query,
            resource=AlbumResource(
                session=self.db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )

    def test_subfilter_invalid_ignore(self):
        """Check that non strict bad subresource filters is ignored."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$bad": 5}}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(
                session=self.db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=False,
            strict=False
        )
        result = query.all()
        self.assertTrue(len(result) > 0)

    def test_many_to_one_limit_fail(self):
        """Test a limit/offset on a many to one relationship fails."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Track)
        subfilters = {
            "album": SubfilterInfo(
                offset_limit_info=OffsetLimitInfo(offset=1, limit=None)
            )
        }
        self.assertRaisesCode(
            BadRequestError,
            "invalid_subresource_options",
            query_builder.apply_subquery_loads,
            query=query,
            resource=TrackResource(
                session=self.db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )

    def test_subresource_bad_dialect_fail(self):
        """Test a sublimit/offset fails with unsupported dialect."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                offset_limit_info=OffsetLimitInfo(offset=1, limit=10)
            )
        }
        self.assertRaisesCode(
            BadRequestError,
            "invalid_subresource_options",
            query_builder.apply_subquery_loads,
            query=query,
            resource=AlbumResource(
                session=self.db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=False
        )

    def test_non_strict_bad_sublimits(self):
        """Test bad sublimits don't cause failure when not strict."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Customer)
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CustomerResource(session=self.db_session),
            subfilters={
                "invoices": SubfilterInfo(
                    offset_limit_info=OffsetLimitInfo(offset=1, limit=10000)
                )
            },
            embeds=[],
            strict=False,
            dialect_override=True
        )
        expected_query = (
            "SELECT Customer.CustomerId AS Customer_CustomerId, "
            "Customer.FirstName AS Customer_FirstName, Customer.LastName AS "
            "Customer_LastName, Customer.Company AS Customer_Company, "
            "Customer.Address AS Customer_Address, Customer.City AS "
            "Customer_City, Customer.State AS Customer_State, "
            "Customer.Country AS Customer_Country, Customer.PostalCode AS "
            "Customer_PostalCode, Customer.Phone AS Customer_Phone, "
            "Customer.Fax AS Customer_Fax, Customer.Email AS Customer_Email, "
            "Customer.SupportRepId AS Customer_SupportRepId, anon_1.InvoiceId "
            "AS anon_1_InvoiceId, anon_1.CustomerId AS anon_1_CustomerId, "
            "anon_1.InvoiceDate AS anon_1_InvoiceDate, anon_1.BillingAddress "
            "AS anon_1_BillingAddress, anon_1.BillingCity AS "
            "anon_1_BillingCity, anon_1.BillingState AS anon_1_BillingState, "
            "anon_1.BillingCountry AS anon_1_BillingCountry, "
            "anon_1.BillingPostalCode AS anon_1_BillingPostalCode, "
            "anon_1.Total AS anon_1_Total FROM Customer LEFT OUTER JOIN "
            "(SELECT q1.InvoiceId AS InvoiceId, q1.CustomerId AS CustomerId, "
            "q1.InvoiceDate AS InvoiceDate, q1.BillingAddress AS "
            "BillingAddress, q1.BillingCity AS BillingCity, q1.BillingState "
            "AS BillingState, q1.BillingCountry AS BillingCountry, "
            "q1.BillingPostalCode AS BillingPostalCode, q1.Total AS Total, "
            "q1.row_number AS row_number FROM (SELECT Invoice1.InvoiceId AS "
            "InvoiceId, Invoice1.CustomerId AS CustomerId, "
            "Invoice1.InvoiceDate AS InvoiceDate, Invoice1.BillingAddress AS "
            "BillingAddress, Invoice1.BillingCity AS BillingCity, "
            "Invoice1.BillingState AS BillingState, Invoice1.BillingCountry "
            "AS BillingCountry, Invoice1.BillingPostalCode AS "
            "BillingPostalCode, Invoice1.Total AS Total, row_number() OVER "
            "(PARTITION BY Invoice1.CustomerId ORDER BY Invoice1.InvoiceId "
            "ASC) AS row_number FROM Invoice AS Invoice1) AS q1 WHERE "
            "q1.row_number >= ? AND q1.row_number <= ?) AS anon_1 ON "
            "Customer.CustomerId = anon_1.CustomerId"
        )
        result = str(query).replace('"', "")
        result = result.replace("\n", "")
        self.assertTrue(result == expected_query)

    def test_subquery_embeds(self):
        """Test that a simple subquery can work alongside an embed."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album)
        subfilters = {
            "artist": SubfilterInfo(
                filters={"artist_id": 1}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters=subfilters,
            embeds=["tracks", "artist"]
        )
        albums = query.all()
        for album in albums:
            res = inspect(album)
            self.assertTrue("tracks" not in res.unloaded)
            if album.artist:
                self.assertTrue(album.artist.artist_id == 1)

    def test_same_subquery_embeds(self):
        """Test that a simple subquery works with a duplicate embed."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": 1}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters=subfilters,
            embeds=["tracks"]
        )
        albums = query.all()
        for album in albums:
            res = inspect(album)
            self.assertTrue("tracks" not in res.unloaded)
            if album.tracks:
                self.assertTrue(len(album.tracks) == 1)
                self.assertTrue(album.tracks[0].track_id == 1)

    def test_simple_embeds(self):
        """Test that a simple embed works."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album)
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters={},
            embeds=["tracks"]
        )
        albums = query.all()
        for album in albums:
            res = inspect(album)
            self.assertTrue("tracks" not in res.unloaded)

    def test_property_embeds(self):
        """Test that property embed works."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album)
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters={},
            embeds=["tracks.track_id"]
        )
        albums = query.all()
        for album in albums:
            res = inspect(album)
            self.assertTrue("tracks" not in res.unloaded)

    def test_bad_embeds(self):
        """Test that a bad property embed fails."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album)
        self.assertRaisesCode(
            BadRequestError,
            "invalid_embed",
            query_builder.apply_subquery_loads,
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters={},
            embeds=["tracks.track_id.playlistId"]
        )

    def test_bad_embeds_ignore(self):
        """Test that a non strict bad property embed is ignored."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album)
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters={},
            embeds=["tracks.track_id.playlistId"],
            strict=False
        )
        result = query.all()
        self.assertTrue(len(result) > 0)

    def test_bad_subfilters(self):
        """Test that a bad property subfilter fails."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album)
        self.assertRaisesCode(
            BadRequestError,
            "invalid_subresource",
            query_builder.apply_subquery_loads,
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters={
                "tracks.track_id": SubfilterInfo(
                    filters={"track_id": 5}
                )
            },
            embeds=[]
        )

    def test_bad_subfilters_value(self):
        """Test that a bad property subfilter value fails."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album)
        self.assertRaises(
            ValueError,
            query_builder.apply_subquery_loads,
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters={
                "tracks.track_id": "test"
            },
            embeds=[]
        )

    def test_non_strict_bad_subfilters(self):
        """Test bad subfitlers don't cause failure when not strict."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album)
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters={
                "tracks.track_id": SubfilterInfo(
                    filters={"track_id": 5}
                )
            },
            embeds=[],
            strict=False
        )
        albums = query.all()
        for album in albums:
            res = inspect(album)
            self.assertTrue("tracks" in res.unloaded)

    def test_self_referential_composite_id_subquery(self):
        """Test a self referential, composite id subquery"""
        query_builder = QueryBuilder()
        query = self.db_session.query(CompositeNode)
        subfilters = {
            "children": SubfilterInfo(
                filters={"node_id": 1}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CompositeNodeResource(session=self.db_session),
            subfilters=subfilters,
            embeds=[]
        )
        composite_nodes = query.all()
        for composite_node in composite_nodes:
            res = inspect(composite_node)
            self.assertTrue("children" not in res.unloaded)
            for child in composite_node.children:
                self.assertTrue(child.node_id == 1)

    def test_composite_id_subquery_with_limit(self):
        """Test a composite id subquery with a limit"""
        query_builder = QueryBuilder()
        query = self.db_session.query(CompositeNode)
        subfilters = {
            "children": SubfilterInfo(
                filters={"node_id": 1},
                offset_limit_info=OffsetLimitInfo(
                    offset=1, limit=1
                )
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CompositeNodeResource(session=self.db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )
        expected_query = (
            "SELECT CompositeNode.NodeId AS CompositeNode_NodeId, "
            "CompositeNode.CompositeId AS CompositeNode_CompositeId, "
            "anon_1.NodeId AS anon_1_NodeId, anon_1.CompositeId AS "
            "anon_1_CompositeId FROM CompositeNode LEFT OUTER JOIN "
            "(CompositeNodeToCompositeNode AS CompositeNodeToCompositeNode_1 "
            "JOIN (SELECT q1.NodeId AS NodeId, q1.CompositeId AS CompositeId, "
            "q1.row_number AS row_number FROM (SELECT CompositeNode1.NodeId "
            "AS NodeId, CompositeNode1.CompositeId AS CompositeId, "
            "row_number() OVER (PARTITION BY "
            "CompositeNodeToCompositeNode.NodeId, "
            "CompositeNodeToCompositeNode.CompositeId ORDER BY "
            "CompositeNode1.NodeId ASC, CompositeNode1.CompositeId ASC) AS "
            "row_number FROM CompositeNode AS CompositeNode1 JOIN "
            "CompositeNodeToCompositeNode ON "
            "CompositeNodeToCompositeNode.ChildNodeId = CompositeNode1.NodeId "
            "AND CompositeNodeToCompositeNode.ChildCompositeId = "
            "CompositeNode1.CompositeId) AS q1, CompositeNode AS "
            "CompositeNode1 WHERE q1.row_number >= ? AND q1.row_number <= ? "
            "AND CompositeNode1.NodeId = ?) AS anon_1 ON "
            "CompositeNodeToCompositeNode_1.NodeId = anon_1.NodeId AND "
            "CompositeNodeToCompositeNode_1.CompositeId = anon_1.CompositeId) "
            "ON CompositeNodeToCompositeNode_1.ChildNodeId = "
            "CompositeNode.NodeId AND "
            "CompositeNodeToCompositeNode_1.ChildCompositeId = "
            "CompositeNode.CompositeId"
        )
        result = str(query).replace('"', "").replace("\n", "")
        self.assertTrue(expected_query == result)
