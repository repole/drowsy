"""
    drowsy.tests.test_query_builder
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Query builder tests for Drowsy.

    :copyright: (c) 2016-2020 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from pytest import raises
from sqlalchemy.inspection import inspect
from drowsy.exc import BadRequestError
from drowsy.query_builder import QueryBuilder, ModelResourceQueryBuilder
from drowsy.parser import SubfilterInfo, SortInfo
from tests.base import DrowsyDatabaseTests
from tests.models import (
    Album, CompositeOne, CompositeNode, Customer, Employee, Playlist, Track
)
from tests.resources import (
    AlbumResource, TrackResource, CompositeNodeResource,
    CompositeOneResource, CustomerResource, EmployeeResource,
    PlaylistResource
)


class TestDrowsyQueryBuilder(DrowsyDatabaseTests):

    """Test drowsy query building across all databases."""

    @staticmethod
    def test_apply_sorts_simple(db_session):
        """Test applying a single sort."""
        query_builder = QueryBuilder()
        query = db_session.query(Album)
        query = query_builder.apply_sorts(
            query=query,
            sorts=[SortInfo(attr="album_id", direction="ASC")]
        )
        results = query.all()
        last_album_id = -1
        for result in results:
            assert result.album_id >= last_album_id
            last_album_id = result.album_id

    @staticmethod
    def test_apply_sorts_fail(db_session):
        """Test applying a single sort."""
        query_builder = QueryBuilder()
        query = db_session.query(Album)
        with raises(AttributeError):
            query_builder.apply_sorts(
                query=query,
                sorts=[SortInfo(attr="badattr", direction="ASC")]
            )

    @staticmethod
    def test_apply_limit_negative_limit_fail(db_session):
        """Test that a negative limit fails."""
        query_builder = QueryBuilder()
        query = db_session.query(Album)
        with raises(ValueError):
            query_builder.apply_limit(
                query=query,
                limit=-1)

    @staticmethod
    def test_apply_offset_negative_offset_fail(db_session):
        """Test that a negative offset fails."""
        query_builder = QueryBuilder()
        query = db_session.query(Album)
        with raises(ValueError):
            query_builder.apply_offset(
                query=query,
                offset=-1)

    @staticmethod
    def test_simple_subfilter(db_session):
        """Test applying a simple subfilter."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": 5}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=[]
        )
        albums = query.all()
        for album in albums:
            assert len(album.tracks) <= 1
            if album.tracks:
                assert album.tracks[0].track_id == 5

    @staticmethod
    def test_apply_sorts_bad_query(db_session):
        """Test applying sorts with a bad query fails."""
        query_builder = QueryBuilder()
        query = db_session.query(Album, Track)
        with raises(ValueError):
            query_builder.apply_sorts(
                query,
                sorts=[])

    @staticmethod
    def test_subfilter_sorts_no_limit_offset_fail(db_session):
        """Check that subresource sorts without limit or offset fail."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                sorts=[SortInfo(attr="track_id", direction="ASC")]
            )
        }
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(
                    session=db_session),
                subfilters=subfilters,
                embeds=[],
                dialect_override=True
            )
        assert excinf.value.code == "invalid_subresource_sorts"

    @staticmethod
    def test_simple_subfilter_limit_too_big(db_session):
        """Check that a limit too large on subresource fails."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Customer)
        subfilters = {
            "invoices": SubfilterInfo(
                offset=1,
                limit=10000
            )
        }
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=CustomerResource(
                    session=db_session),
                subfilters=subfilters,
                embeds=[],
                dialect_override=True
            )
        assert excinf.value.code == "invalid_subresource_limit"

    @staticmethod
    def test_subfilter_invalid_fail(db_session):
        """Check that bad subresource filters fail."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$bad": 5}}
            )
        }
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(
                    session=db_session),
                subfilters=subfilters,
                embeds=[],
                dialect_override=True
            )
        assert excinf.value.code == "filters_field_op_error"

    @staticmethod
    def test_subfilter_invalid_ignore(db_session):
        """Check that non strict bad subresource filters is ignored."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$bad": 5}}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(
                session=db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=False,
            strict=False
        )
        result = query.all()
        assert len(result) > 0

    @staticmethod
    def test_subfilter_invalid_limit_fail(db_session):
        """Check subresource query with an invalid root limit fails."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                sorts=[SortInfo(attr="track_id", direction="ASC")]
            )
        }
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(
                    session=db_session),
                subfilters=subfilters,
                embeds=[],
                dialect_override=True,
                limit=-1
            )
        assert excinf.value.code == "invalid_limit_value"

    @staticmethod
    def test_subfilter_invalid_limit_ignore(db_session):
        """Check subresource query with invalid root limit ignored."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                sorts=[SortInfo(attr="track_id", direction="ASC")]
            )
        }
        query = query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(
                    session=db_session),
                subfilters=subfilters,
                embeds=[],
                dialect_override=True,
                limit=-1,
                strict=False
            )
        assert query is not None

    @staticmethod
    def test_subfilter_invalid_sort_fail(db_session):
        """Check subresource query with an invalid root sort fails."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                sorts=[SortInfo(attr="track_id")]
            )
        }
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(
                    session=db_session),
                sorts=[SortInfo(attr="TEST")],
                subfilters=subfilters,
                embeds=[],
                dialect_override=True
            )
        assert excinf.value.code == "invalid_sort_field"

    @staticmethod
    def test_subfilter_invalid_sort_ignore(db_session):
        """Check subresource query with invalid root sort is ignored."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                sorts=[SortInfo(attr="track_id")]
            )
        }
        query = query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(
                    session=db_session),
                subfilters=subfilters,
                sorts=[SortInfo(attr="TEST")],
                embeds=[],
                dialect_override=True,
                strict=False
            )
        assert query is not None

    @staticmethod
    def test_subfilter_root_sort(db_session):
        """Check subresource query with root sort works."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                sorts=[SortInfo(attr="track_id")]
            )
        }
        query = query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(
                    session=db_session),
                subfilters=subfilters,
                sorts=[SortInfo(attr="title")],
                embeds=[],
                dialect_override=True,
                strict=False
            )
        result = query.first()
        assert result.title == "...And Justice For All"

    @staticmethod
    def test_subfilter_invalid_offset_fail(db_session):
        """Check subresource query with an invalid root offset fails."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                sorts=[SortInfo(attr="track_id", direction="ASC")]
            )
        }
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(
                    session=db_session),
                subfilters=subfilters,
                embeds=[],
                dialect_override=True,
                offset=-1
            )
        assert excinf.value.code == "invalid_offset_value"

    @staticmethod
    def test_subfilter_invalid_offset_ignore(db_session):
        """Check subresource query with invalid root offset ignored."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                sorts=[SortInfo(attr="track_id", direction="ASC")]
            )
        }
        query = query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(
                    session=db_session),
                subfilters=subfilters,
                embeds=[],
                dialect_override=True,
                offset=-1,
                strict=False
            )
        assert query is not None

    @staticmethod
    def test_many_to_one_limit_fail(db_session):
        """Test a limit/offset on a many to one relationship fails."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Track)
        subfilters = {
            "album": SubfilterInfo(
                offset=1,
                limit=None
            )
        }
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=TrackResource(
                    session=db_session),
                subfilters=subfilters,
                embeds=[],
                dialect_override=True
            )
        assert excinf.value.code == "invalid_subresource_options"

    @staticmethod
    def test_subquery_embeds(db_session):
        """Test that a simple subquery can work alongside an embed."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "artist": SubfilterInfo(
                filters={"artist_id": 1}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=["tracks", "artist"]
        )
        albums = query.all()
        for album in albums:
            res = inspect(album)
            assert "tracks" not in res.unloaded
            if album.artist:
                assert album.artist.artist_id == 1

    @staticmethod
    def test_same_subquery_embeds(db_session):
        """Test that a simple subquery works with a duplicate embed."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": 1}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=["tracks"]
        )
        albums = query.all()
        for album in albums:
            res = inspect(album)
            assert "tracks" not in res.unloaded
            if album.tracks:
                assert len(album.tracks) == 1
                assert album.tracks[0].track_id == 1

    @staticmethod
    def test_simple_embeds(db_session):
        """Test that a simple embed works."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters={},
            embeds=["tracks"]
        )
        albums = query.all()
        for album in albums:
            res = inspect(album)
            assert "tracks" not in res.unloaded

    @staticmethod
    def test_property_embeds(db_session):
        """Test that property embed works."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters={},
            embeds=["tracks.track_id"]
        )
        albums = query.all()
        for album in albums:
            res = inspect(album)
            assert "tracks" not in res.unloaded

    @staticmethod
    def test_bad_embeds(db_session):
        """Test that a bad property embed fails."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(session=db_session),
                subfilters={},
                embeds=["tracks.track_id.playlistId"]
            )
        assert excinf.value.code == "invalid_embed"

    @staticmethod
    def test_bad_embeds_ignore(db_session):
        """Test that a non strict bad property embed is ignored."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters={},
            embeds=["tracks.track_id.playlistId"],
            strict=False
        )
        result = query.all()
        assert len(result) > 0

    @staticmethod
    def test_too_complex(db_session):
        """Test that an overly complex query fails."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        with raises(BadRequestError) as excinf:
            query_builder.build(
                query=query,
                resource=AlbumResource(session=db_session),
                filters={"tracks.track_id": 5},
                subfilters={},
                stack_size_limit=1
            )
        assert excinf.value.code == "filters_too_complex"

    @staticmethod
    def test_no_op_error_message(db_session):
        """Test that filters trigger an error message with no $op."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        with raises(BadRequestError) as excinf:
            query_builder.build(
                query=query,
                resource=AlbumResource(session=db_session),
                filters={"tracks": {}},
                subfilters={},
                stack_size_limit=1
            )
        assert excinf.value.code == "filters_field_error"

    @staticmethod
    def test_bad_subfilters(db_session):
        """Test that a bad property subfilter fails."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(session=db_session),
                subfilters={
                    "tracks.track_id": SubfilterInfo(
                        filters={"track_id": 5}
                    )
                },
                embeds=[]
            )
        assert excinf.value.code == "invalid_subresource"

    @staticmethod
    def test_bad_subfilters_value(db_session):
        """Test that a bad property subfilter value fails."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        with raises(ValueError):
            query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(session=db_session),
                subfilters={
                    "tracks.track_id": "test"
                },
                embeds=[]
            )

    @staticmethod
    def test_non_strict_bad_subfilters(db_session):
        """Test bad subfitlers don't cause failure when not strict."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters={
                "tracks.track_id": SubfilterInfo(
                    filters={"track_id": 5}
                )
            },
            embeds=[],
            strict=False
        )
        albums = query.all()
        assert len(albums) == 347
        # TODO - review whether we want this to not load subresource
        # for album in albums:
        #     res = inspect(album)
        #     assert "tracks" in res.unloaded)

    @staticmethod
    def test_whitelist_fail(db_session):
        """Test a missing whitelist key causes permission error."""
        from drowsy.exc import PermissionDeniedError
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Employee)
        resource = EmployeeResource(session=db_session)
        with raises(PermissionDeniedError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=resource,
                subfilters={
                    "customers": SubfilterInfo(
                        filters={"phone": 5}
                    )
                },
                embeds=[],
                strict=True
            )
        assert excinf.value.code == "filters_permission_error"

    @staticmethod
    def test_self_referential_composite_id_subquery(db_session):
        """Test a self referential, composite id subquery"""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(CompositeNode)
        subfilters = {
            "children": SubfilterInfo(
                filters={"node_id": 1}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CompositeNodeResource(session=db_session),
            subfilters=subfilters,
            embeds=[]
        )
        composite_nodes = query.all()
        for composite_node in composite_nodes:
            res = inspect(composite_node)
            assert "children" not in res.unloaded
            for child in composite_node.children:
                assert child.node_id == 1

    @staticmethod
    def test_root_composite_id_limit_with_subquery(db_session):
        """Limit to a composite id root resource using subqueries."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(CompositeNode)
        subfilters = {
            "children": SubfilterInfo(
                filters={"node_id": 6}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CompositeNodeResource(session=db_session),
            subfilters=subfilters,
            limit=1,
            offset=0,
            embeds=[]
        )
        result = query.all()
        assert result is not None
        assert len(result) == 1
        assert result[0].node_id == 1
        assert len(result[0].children) == 1
        assert result[0].children[0].node_id == 6

    @staticmethod
    def test_root_limit_with_subquery(db_session):
        """Test applying a limit to a root resource using subqueries."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": 2}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            limit=1,
            offset=1,
            embeds=[]
        )
        result = query.all()
        assert result is not None
        assert len(result) == 1
        assert result[0].album_id == 2
        assert len(result[0].tracks) == 1
        assert result[0].tracks[0].track_id == 2


class TestDrowsyQueryBuilderSqlite(DrowsyDatabaseTests):

    """Sqlite specific query builder tests."""

    backends = ['sqlite']

    @staticmethod
    def test_subresource_bad_dialect_fail(db_session):
        """Test a sublimit/offset fails with unsupported dialect."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                offset=1,
                limit=10
            )
        }
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(
                    session=db_session),
                subfilters=subfilters,
                embeds=[],
                dialect_override=False
            )
        assert excinf.value.code == "invalid_subresource_options"

    @staticmethod
    def test_composite_root_limit_with_subquery_limit(db_session):
        """Apply limit to both root + subresource with composite id."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(CompositeOne)
        subfilters = {
            "many": SubfilterInfo(
                filters={"many_id": 1},
                offset=1,
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CompositeOneResource(session=db_session),
            subfilters=subfilters,
            limit=1,
            offset=1,
            embeds=[],
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                anon_1."CompositeOne_OneId" AS "anon_1_CompositeOne_OneId", 
                anon_1."CompositeOne_CompositeOneId" AS 
                    "anon_1_CompositeOne_CompositeOneId", 
                "CompositeMany1"."ManyId" AS "CompositeMany1_ManyId", 
                "CompositeMany1"."OneId" AS "CompositeMany1_OneId", 
                "CompositeMany1"."CompositeOneId" AS 
                    "CompositeMany1_CompositeOneId"
            FROM 
                (
                    SELECT 
                        "CompositeOne"."OneId" AS "CompositeOne_OneId", 
                        "CompositeOne"."CompositeOneId" AS 
                            "CompositeOne_CompositeOneId", 
                        row_number() OVER (ORDER BY 
                            "CompositeOne"."OneId" ASC, 
                            "CompositeOne"."CompositeOneId" ASC) AS row_number 
                    FROM "CompositeOne"
                ) AS anon_1 
                LEFT OUTER JOIN 
                (
                    SELECT 
                        q1."ManyId" AS "ManyId", 
                        q1."OneId" AS "OneId", 
                        q1."CompositeOneId" AS "CompositeOneId", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "CompositeMany1"."ManyId" AS "ManyId", 
                                "CompositeMany1"."OneId" AS "OneId", 
                                "CompositeMany1"."CompositeOneId" AS 
                                    "CompositeOneId", 
                                row_number() OVER (
                                    PARTITION BY 
                                        "CompositeMany1"."OneId", 
                                        "CompositeMany1"."CompositeOneId" 
                                    ORDER BY 
                                        "CompositeMany1"."ManyId" ASC
                                ) AS row_number 
                            FROM 
                                "CompositeMany" AS "CompositeMany1"
                            WHERE
                                "CompositeMany1"."ManyId" = ?
                        ) AS q1
                    WHERE 
                        q1.row_number >= ? 
                        AND 
                        q1.row_number <= ?
                ) AS "CompositeMany1" ON 
                    anon_1."CompositeOne_OneId" = "CompositeMany1"."OneId" 
                    AND 
                    anon_1."CompositeOne_CompositeOneId" = 
                        "CompositeMany1"."CompositeOneId" 
            WHERE 
                anon_1.row_number >= ? 
                AND 
                anon_1.row_number <= ? 
            ORDER BY 
                anon_1.row_number
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        assert expected_query == result

    @staticmethod
    def test_simple_subfilter_limit_offset(db_session):
        """Test offset and limit in a subresource."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 5}},
                offset=1,
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                "Album"."AlbumId" AS "Album_AlbumId", 
                "Album"."Title" AS "Album_Title", 
                "Album"."ArtistId" AS "Album_ArtistId", 
                "Track1"."TrackId" AS "Track1_TrackId", 
                "Track1"."Name" AS "Track1_Name", 
                "Track1"."AlbumId" AS "Track1_AlbumId", 
                "Track1"."MediaTypeId" AS "Track1_MediaTypeId", 
                "Track1"."GenreId" AS "Track1_GenreId", 
                "Track1"."Composer" AS "Track1_Composer", 
                "Track1"."Milliseconds" AS "Track1_Milliseconds", 
                "Track1"."Bytes" AS "Track1_Bytes", 
                "Track1"."UnitPrice" AS "Track1_UnitPrice" 
            FROM 
                "Album" 
                LEFT OUTER JOIN 
                (
                    SELECT 
                        q1."TrackId" AS "TrackId", 
                        q1."Name" AS "Name", 
                        q1."AlbumId" AS "AlbumId", 
                        q1."MediaTypeId" AS "MediaTypeId", 
                        q1."GenreId" AS "GenreId", 
                        q1."Composer" AS "Composer", 
                        q1."Milliseconds" AS "Milliseconds", 
                        q1."Bytes" AS "Bytes", 
                        q1."UnitPrice" AS "UnitPrice", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "Track1"."TrackId" AS "TrackId", 
                                "Track1"."Name" AS "Name", 
                                "Track1"."AlbumId" AS "AlbumId", 
                                "Track1"."MediaTypeId" AS "MediaTypeId", 
                                "Track1"."GenreId" AS "GenreId", 
                                "Track1"."Composer" AS "Composer", 
                                "Track1"."Milliseconds" AS "Milliseconds", 
                                "Track1"."Bytes" AS "Bytes", 
                                "Track1"."UnitPrice" AS "UnitPrice", 
                                row_number() OVER (
                                    PARTITION BY 
                                        "Track1"."AlbumId" 
                                    ORDER BY 
                                        "Track1"."TrackId" ASC
                                ) AS row_number 
                            FROM 
                                "Track" AS "Track1"
                            WHERE 
                                "Track1"."TrackId" >= ?
                        ) AS q1
                    WHERE 
                        q1.row_number >= ? 
                        AND 
                        q1.row_number <= ? 
                ) AS "Track1" ON 
                    "Album"."AlbumId" = "Track1"."AlbumId" 
            ORDER BY 
                "Album"."AlbumId" ASC
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        assert expected_query == result

    @staticmethod
    def test_subfilter_limit_offset_sorts(db_session):
        """Test subfiltering with sorts works with limit and offset."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 5}},
                offset=1,
                limit=1,
                sorts=[SortInfo(attr="name", direction="ASC")]
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                "Album"."AlbumId" AS "Album_AlbumId", 
                "Album"."Title" AS "Album_Title", 
                "Album"."ArtistId" AS "Album_ArtistId", 
                "Track1"."TrackId" AS "Track1_TrackId", 
                "Track1"."Name" AS "Track1_Name", 
                "Track1"."AlbumId" AS "Track1_AlbumId", 
                "Track1"."MediaTypeId" AS "Track1_MediaTypeId", 
                "Track1"."GenreId" AS "Track1_GenreId", 
                "Track1"."Composer" AS "Track1_Composer", 
                "Track1"."Milliseconds" AS "Track1_Milliseconds", 
                "Track1"."Bytes" AS "Track1_Bytes", 
                "Track1"."UnitPrice" AS "Track1_UnitPrice" 
            FROM 
                "Album" 
                LEFT OUTER JOIN 
                (
                    SELECT 
                        q1."TrackId" AS "TrackId", 
                        q1."Name" AS "Name", 
                        q1."AlbumId" AS "AlbumId", 
                        q1."MediaTypeId" AS "MediaTypeId", 
                        q1."GenreId" AS "GenreId", 
                        q1."Composer" AS "Composer", 
                        q1."Milliseconds" AS "Milliseconds", 
                        q1."Bytes" AS "Bytes", 
                        q1."UnitPrice" AS "UnitPrice", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "Track1"."TrackId" AS "TrackId", 
                                "Track1"."Name" AS "Name", 
                                "Track1"."AlbumId" AS "AlbumId", 
                                "Track1"."MediaTypeId" AS "MediaTypeId", 
                                "Track1"."GenreId" AS "GenreId", 
                                "Track1"."Composer" AS "Composer", 
                                "Track1"."Milliseconds" AS "Milliseconds", 
                                "Track1"."Bytes" AS "Bytes", 
                                "Track1"."UnitPrice" AS "UnitPrice", 
                                row_number() OVER (
                                    PARTITION BY 
                                        "Track1"."AlbumId" 
                                    ORDER BY 
                                        "Track1"."Name" ASC
                                ) AS row_number 
                            FROM 
                                "Track" AS "Track1"
                            WHERE
                                "Track1"."TrackId" >= ?
                        ) AS q1
                    WHERE 
                        q1.row_number >= ? 
                        AND 
                        q1.row_number <= ?  
                ) AS "Track1" ON 
                    "Album"."AlbumId" = "Track1"."AlbumId" 
            ORDER BY 
                "Album"."AlbumId" ASC
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        assert expected_query == result

    @staticmethod
    def test_non_strict_bad_sublimits(db_session):
        """Test bad sublimits don't cause failure when not strict."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Customer)
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CustomerResource(session=db_session),
            subfilters={
                "invoices": SubfilterInfo(
                    offset=1,
                    limit=10000
                )
            },
            embeds=[],
            strict=False,
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                "Customer"."CustomerId" AS "Customer_CustomerId", 
                "Customer"."FirstName" AS "Customer_FirstName", 
                "Customer"."LastName" AS "Customer_LastName", 
                "Customer"."Company" AS "Customer_Company", 
                "Customer"."Address" AS "Customer_Address", 
                "Customer"."City" AS "Customer_City", 
                "Customer"."State" AS "Customer_State", 
                "Customer"."Country" AS "Customer_Country", 
                "Customer"."PostalCode" AS "Customer_PostalCode", 
                "Customer"."Phone" AS "Customer_Phone", 
                "Customer"."Fax" AS "Customer_Fax", 
                "Customer"."Email" AS "Customer_Email", 
                "Customer"."SupportRepId" AS "Customer_SupportRepId", 
                "Invoice1"."InvoiceId" AS "Invoice1_InvoiceId", 
                "Invoice1"."CustomerId" AS "Invoice1_CustomerId", 
                "Invoice1"."InvoiceDate" AS "Invoice1_InvoiceDate", 
                "Invoice1"."BillingAddress" AS "Invoice1_BillingAddress", 
                "Invoice1"."BillingCity" AS "Invoice1_BillingCity", 
                "Invoice1"."BillingState" AS "Invoice1_BillingState", 
                "Invoice1"."BillingCountry" AS "Invoice1_BillingCountry", 
                "Invoice1"."BillingPostalCode" AS "Invoice1_BillingPostalCode", 
                "Invoice1"."Total" AS "Invoice1_Total" 
            FROM 
                "Customer" 
                LEFT OUTER JOIN 
                (
                    SELECT 
                        q1."InvoiceId" AS "InvoiceId", 
                        q1."CustomerId" AS "CustomerId", 
                        q1."InvoiceDate" AS "InvoiceDate", 
                        q1."BillingAddress" AS "BillingAddress", 
                        q1."BillingCity" AS "BillingCity", 
                        q1."BillingState" AS "BillingState", 
                        q1."BillingCountry" AS "BillingCountry", 
                        q1."BillingPostalCode" AS "BillingPostalCode", 
                        q1."Total" AS "Total", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "Invoice1"."InvoiceId" AS "InvoiceId", 
                                "Invoice1"."CustomerId" AS "CustomerId", 
                                "Invoice1"."InvoiceDate" AS "InvoiceDate", 
                                "Invoice1"."BillingAddress" AS 
                                    "BillingAddress", 
                                "Invoice1"."BillingCity" AS "BillingCity", 
                                "Invoice1"."BillingState" AS "BillingState", 
                                "Invoice1"."BillingCountry" AS 
                                    "BillingCountry", 
                                "Invoice1"."BillingPostalCode" AS 
                                    "BillingPostalCode", 
                                "Invoice1"."Total" AS "Total", 
                                row_number() OVER (
                                    PARTITION BY 
                                        "Invoice1"."CustomerId" 
                                    ORDER BY 
                                        "Invoice1"."InvoiceId" ASC
                                ) AS row_number 
                            FROM 
                                "Invoice" AS "Invoice1"
                        ) AS q1 
                    WHERE 
                        q1.row_number >= ? 
                        AND 
                        q1.row_number <= ?
                ) AS "Invoice1" ON 
                    "Invoice1"."CustomerId" = "Customer"."CustomerId" 
            ORDER BY 
                "Customer"."CustomerId" ASC
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        assert expected_query == result

    @staticmethod
    def test_composite_id_subquery_with_limit(db_session):
        """Test a composite id subquery with a limit"""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(CompositeNode)
        subfilters = {
            "children": SubfilterInfo(
                filters={"node_id": 1},
                offset=1,
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CompositeNodeResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                "CompositeNode"."NodeId" AS "CompositeNode_NodeId", 
                "CompositeNode"."CompositeId" AS "CompositeNode_CompositeId", 
                "CompositeNode1"."NodeId" AS "CompositeNode1_NodeId", 
                "CompositeNode1"."CompositeId" AS "CompositeNode1_CompositeId" 
            FROM 
                "CompositeNode" 
                LEFT OUTER JOIN 
                "CompositeNodeToCompositeNode" AS 
                        "CompositeNodeToCompositeNode_1" ON 
                    "CompositeNodeToCompositeNode_1"."NodeId" = 
                        "CompositeNode"."NodeId" 
                    AND 
                    "CompositeNodeToCompositeNode_1"."CompositeId" = 
                        "CompositeNode"."CompositeId" 
                LEFT OUTER JOIN 
                    (
                        SELECT 
                            q1."NodeId" AS "NodeId", 
                            q1."CompositeId" AS "CompositeId", 
                            q1.row_number AS row_number 
                        FROM 
                        (
                            SELECT 
                                "CompositeNode1"."NodeId" AS "NodeId", 
                                "CompositeNode1"."CompositeId" AS 
                                    "CompositeId", 
                                row_number() OVER (
                                    PARTITION BY 
                                        "CompositeNodeToCompositeNode".
                                            "NodeId", 
                                        "CompositeNodeToCompositeNode".
                                            "CompositeId" 
                                    ORDER BY 
                                        "CompositeNode1"."NodeId" ASC, 
                                        "CompositeNode1"."CompositeId" ASC
                                ) AS row_number 
                            FROM 
                                "CompositeNode" AS "CompositeNode1" 
                                JOIN 
                                "CompositeNodeToCompositeNode" ON 
                                    "CompositeNodeToCompositeNode".
                                        "ChildNodeId" = 
                                            "CompositeNode1"."NodeId" 
                                    AND 
                                    "CompositeNodeToCompositeNode".
                                        "ChildCompositeId" = 
                                            "CompositeNode1"."CompositeId"
                            WHERE
                                "CompositeNode1"."NodeId" = ?
                        ) AS q1
                        WHERE 
                            q1.row_number >= ? 
                            AND 
                            q1.row_number <= ? 
                    ) AS "CompositeNode1" ON 
                        "CompositeNodeToCompositeNode_1"."ChildNodeId" = 
                            "CompositeNode1"."NodeId" 
                        AND 
                        "CompositeNodeToCompositeNode_1"."ChildCompositeId" = 
                            "CompositeNode1"."CompositeId" 
            ORDER BY 
                "CompositeNode"."NodeId" ASC, 
                "CompositeNode"."CompositeId" ASC
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        assert expected_query == result

    @staticmethod
    def test_composite_id_subquery_one_to_many(db_session):
        """Test a composite id subquery with a many to one relation."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(CompositeOne)
        subfilters = {
            "many": SubfilterInfo(
                filters={"many_id": 1},
                offset=1,
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CompositeOneResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                "CompositeOne"."OneId" AS "CompositeOne_OneId", 
                "CompositeOne"."CompositeOneId" AS 
                    "CompositeOne_CompositeOneId", 
                "CompositeMany1"."ManyId" AS "CompositeMany1_ManyId", 
                "CompositeMany1"."OneId" AS "CompositeMany1_OneId", 
                "CompositeMany1"."CompositeOneId" AS 
                    "CompositeMany1_CompositeOneId" 
            FROM 
                "CompositeOne" 
                LEFT OUTER JOIN 
                (
                    SELECT 
                        q1."ManyId" AS "ManyId", 
                        q1."OneId" AS "OneId", 
                        q1."CompositeOneId" AS "CompositeOneId", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "CompositeMany1"."ManyId" AS "ManyId", 
                                "CompositeMany1"."OneId" AS "OneId", 
                                "CompositeMany1"."CompositeOneId" AS 
                                    "CompositeOneId", 
                                row_number() OVER (
                                    PARTITION BY 
                                        "CompositeMany1"."OneId", 
                                        "CompositeMany1"."CompositeOneId" 
                                    ORDER BY 
                                        "CompositeMany1"."ManyId" ASC
                                ) AS row_number 
                            FROM 
                                "CompositeMany" AS "CompositeMany1"
                            WHERE
                                "CompositeMany1"."ManyId" = ?
                        ) AS q1
                    WHERE 
                        q1.row_number >= ? 
                        AND 
                        q1.row_number <= ? 
                ) AS "CompositeMany1" ON 
                    "CompositeOne"."OneId" = "CompositeMany1"."OneId" 
                    AND 
                    "CompositeOne"."CompositeOneId" = 
                        "CompositeMany1"."CompositeOneId" 
            ORDER BY 
                "CompositeOne"."OneId" ASC, 
                "CompositeOne"."CompositeOneId" ASC
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        assert expected_query == result


class TestDrowsyQueryBuilderSqlServer(DrowsyDatabaseTests):

    """Sqlite specific query builder tests."""

    backends = ['mssql']

    @staticmethod
    def test_root_and_nested_limit_offset(db_session):
        """Test offset and limit in both root and nested collections."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 15}},
                offset=1,
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            limit=10,
            offset=1
        )
        results = query.all()
        assert len(results) == 10
        for album in results:
            assert len(album.tracks) <= 1
            for track in album.tracks:
                # root offset check
                assert album.album_id != 1
                if album.album_id == 2:
                    # subresource offset check
                    assert track.track_id == 16
                assert track.track_id >= 5

    @staticmethod
    def test_subfilter_limit_offset_sorts(db_session):
        """Test subfiltering with sorts works with limit and offset."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 5}},
                offset=1,
                limit=1,
                sorts=[SortInfo(attr="name", direction="ASC")]
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=[]
        )
        results = query.all()
        assert len(results) == 347
        for album in results:
            # limit test
            assert len(album.tracks) <= 1
            if album.album_id == 1:
                # offset test
                assert album.tracks[0].name == "C.O.D."

    @staticmethod
    def test_non_strict_bad_sublimits(db_session):
        """Test bad sublimits don't cause failure when not strict."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Customer)
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CustomerResource(session=db_session),
            subfilters={
                "invoices": SubfilterInfo(
                    offset=1,
                    limit=10000
                )
            },
            embeds=[],
            strict=False
        )
        results = query.all()
        assert len(results) == 59
        assert results[0].customer_id == 1
        # offset check
        assert len(results[0].invoices) == 6
        assert results[0].invoices[0].invoice_id == 121

    @staticmethod
    def test_self_ref_composite_id_subquery_with_limit(db_session):
        """Self referential a composite id subquery with a limit"""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(CompositeNode).filter(CompositeNode.node_id == 1)
        subfilters = {
            "children": SubfilterInfo(
                filters={"node_id": {"$in": [1, 2]}},
                offset=1,
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CompositeNodeResource(session=db_session),
            subfilters=subfilters,
            embeds=[]
        )
        results = query.all()
        assert len(results) == 1
        assert results[0].node_id == 1
        assert results[0].children[0].node_id == 2

    @staticmethod
    def test_multilevel_subfilter_limit(db_session):
        """Test subfiltering with sorts works with limit and offset."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 5}},
                limit=4,
                sorts=[SortInfo(attr="name", direction="ASC")]
            ),
            "tracks.playlists": SubfilterInfo(
                filters={"playlist_id": {"$gte": 6}},
                limit=5,
                sorts=[SortInfo(attr="name", direction="ASC")]
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            limit=3
        )
        results = query.all()
        assert len(results) == 3
        for album in results:
            # limit test
            assert len(album.tracks) <= 4
            for track in album.tracks:
                assert track.track_id >= 5
                # limit test
                assert len(track.playlists) <= 5
                for playlist in track.playlists:
                    assert playlist.playlist_id >= 6


    @staticmethod
    def test_many_to_many_subresource_limit(db_session):
        """Many to many relationships with limits loaded properly."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Playlist)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 5}},
                limit=5,
                sorts=[SortInfo(attr="name", direction="ASC")]
            ),
            "tracks.playlists": SubfilterInfo(
                filters={"playlist_id": {"$lte": 6}},
                limit=4,
                sorts=[SortInfo(attr="name", direction="ASC")]
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=PlaylistResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            limit=3
        )
        results = query.all()
        assert len(results) == 3
        for playlist in results:
            assert len(playlist.tracks) <= 5
            for track in playlist.tracks:
                assert track.track_id >= 5
                assert len(track.playlists) <= 4
                for pl in track.playlists:
                    assert pl.playlist_id <= 6
