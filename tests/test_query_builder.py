"""
    tests.test_query_builder
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Query builder tests for Drowsy.

"""
# :copyright: (c) 2016-2020 by Nicholas Repole and contributors.
#             See AUTHORS for more details.
# :license: MIT - See LICENSE for more details.
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
                sorts=[SortInfo(attr="album_id", direction="DESC")],
                embeds=[],
                dialect_override=True,
                strict=False
            )
        result = query.first()
        assert result.album_id == 347

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
    def test_root_composite_id_limit_with_subquery(caplog, db_session):
        """Limit to a composite id root resource using subqueries."""
        import logging
        logging.basicConfig()
        logger = logging.getLogger('sqlalchemy')
        logger.addHandler(logging.StreamHandler())
        logger.addHandler(logging.FileHandler(filename="test.log"))
        logger.setLevel(logging.INFO)
        caplog.set_level(logging.INFO, logger='sqlalchemy')
        with caplog.at_level(logging.INFO, logger="sqlalchemy"):
            logger.info("WTF")
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
        return

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

    @staticmethod
    def test_circular_relationship_fails(db_session):
        """Referencing the same relationship multiple times fails."""
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
            ),
            "tracks.playlists.tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 5}},
                limit=5,
                sorts=[SortInfo(attr="name", direction="ASC")]
            ),
        }
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=PlaylistResource(session=db_session),
                subfilters=subfilters,
                embeds=[],
                limit=3,
                dialect_override=True
            )
        assert excinf.value.code == "invalid_subresource_multi_embed"

    @staticmethod
    def test_bad_subfilter_with_limit(db_session):
        """Test bad subfilter using a limit fails."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$bad": 5}},
                limit=1
            )
        }
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(session=db_session),
                subfilters=subfilters,
                embeds=[],
                dialect_override=True,
                strict=True
            )
        assert excinf.value.code == "filters_field_op_error"


class TestDrowsyQueryBuilderSqlite(DrowsyDatabaseTests):

    """Sqlite specific query builder tests."""

    backends = ['sqlite']

    @staticmethod
    def test_root_limit_with_subquery(db_session):
        """Apply limit to root resource with subqueries & no row_num."""
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
            embeds=[],
            dialect_override=False
        )
        result = query.all()
        assert result is not None
        assert len(result) == 1
        assert result[0].album_id == 2
        assert len(result[0].tracks) == 1
        assert result[0].tracks[0].track_id == 2

    @staticmethod
    def test_root_composite_id_limit_with_subquery(db_session):
        """Limit composite id root using subqueries without row_num."""
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
            embeds=[],
            dialect_override=False
        )
        result = query.all()
        assert result is not None
        assert len(result) == 1
        assert result[0].node_id == 1
        assert len(result[0].children) == 1
        assert result[0].children[0].node_id == 6

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
            offset=1,
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                anon_1."Album_AlbumId" AS "anon_1_Album_AlbumId", 
                anon_1."Album_Title" AS "anon_1_Album_Title", 
                anon_1."Album_ArtistId" AS "anon_1_Album_ArtistId", 
                "Track1"."Track1_TrackId" AS "Track1_Track1_TrackId", 
                "Track1"."Track1_Name" AS "Track1_Track1_Name", 
                "Track1"."Track1_AlbumId" AS "Track1_Track1_AlbumId", 
                "Track1"."Track1_MediaTypeId" AS "Track1_Track1_MediaTypeId", 
                "Track1"."Track1_GenreId" AS "Track1_Track1_GenreId", 
                "Track1"."Track1_Composer" AS "Track1_Track1_Composer", 
                "Track1"."Track1_Milliseconds" AS "Track1_Track1_Milliseconds", 
                "Track1"."Track1_Bytes" AS "Track1_Track1_Bytes", 
                "Track1"."Track1_UnitPrice" AS "Track1_Track1_UnitPrice" 
            FROM 
                (
                    SELECT 
                        "Album"."AlbumId" AS "Album_AlbumId", 
                        "Album"."Title" AS "Album_Title", 
                        "Album"."ArtistId" AS "Album_ArtistId", 
                        row_number() OVER (
                            ORDER BY "Album"."AlbumId" ASC) AS row_number 
                    FROM 
                        "Album"
                ) AS anon_1 
                LEFT OUTER JOIN 
                (
                    SELECT 
                        q1."Track1_TrackId" AS "Track1_TrackId", 
                        q1."Track1_Name" AS "Track1_Name", 
                        q1."Track1_AlbumId" AS "Track1_AlbumId", 
                        q1."Track1_MediaTypeId" AS "Track1_MediaTypeId", 
                        q1."Track1_GenreId" AS "Track1_GenreId", 
                        q1."Track1_Composer" AS "Track1_Composer", 
                        q1."Track1_Milliseconds" AS "Track1_Milliseconds", 
                        q1."Track1_Bytes" AS "Track1_Bytes", 
                        q1."Track1_UnitPrice" AS "Track1_UnitPrice", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "Track1"."TrackId" AS "Track1_TrackId", 
                                "Track1"."Name" AS "Track1_Name", 
                                "Track1"."AlbumId" AS "Track1_AlbumId", 
                                "Track1"."MediaTypeId" AS "Track1_MediaTypeId", 
                                "Track1"."GenreId" AS "Track1_GenreId", 
                                "Track1"."Composer" AS "Track1_Composer", 
                                "Track1"."Milliseconds" AS 
                                    "Track1_Milliseconds", 
                                "Track1"."Bytes" AS "Track1_Bytes", 
                                "Track1"."UnitPrice" AS "Track1_UnitPrice", 
                                row_number() OVER (
                                    PARTITION BY "Track1"."AlbumId" 
                                    ORDER BY "Track1"."TrackId" ASC
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
                    anon_1."Album_AlbumId" = "Track1"."Track1_AlbumId" 
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
                "Track1"."Track1_TrackId" AS "Track1_Track1_TrackId", 
                "Track1"."Track1_Name" AS "Track1_Track1_Name", 
                "Track1"."Track1_AlbumId" AS "Track1_Track1_AlbumId", 
                "Track1"."Track1_MediaTypeId" AS "Track1_Track1_MediaTypeId", 
                "Track1"."Track1_GenreId" AS "Track1_Track1_GenreId", 
                "Track1"."Track1_Composer" AS "Track1_Track1_Composer", 
                "Track1"."Track1_Milliseconds" AS "Track1_Track1_Milliseconds", 
                "Track1"."Track1_Bytes" AS "Track1_Track1_Bytes", 
                "Track1"."Track1_UnitPrice" AS "Track1_Track1_UnitPrice" 
            FROM 
                "Album" 
                LEFT OUTER JOIN (
                    SELECT 
                        q1."Track1_TrackId" AS "Track1_TrackId", 
                        q1."Track1_Name" AS "Track1_Name", 
                        q1."Track1_AlbumId" AS "Track1_AlbumId", 
                        q1."Track1_MediaTypeId" AS "Track1_MediaTypeId", 
                        q1."Track1_GenreId" AS "Track1_GenreId", 
                        q1."Track1_Composer" AS "Track1_Composer", 
                        q1."Track1_Milliseconds" AS "Track1_Milliseconds", 
                        q1."Track1_Bytes" AS "Track1_Bytes", 
                        q1."Track1_UnitPrice" AS "Track1_UnitPrice", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "Track1"."TrackId" AS "Track1_TrackId", 
                                "Track1"."Name" AS "Track1_Name", 
                                "Track1"."AlbumId" AS "Track1_AlbumId", 
                                "Track1"."MediaTypeId" AS "Track1_MediaTypeId", 
                                "Track1"."GenreId" AS "Track1_GenreId", 
                                "Track1"."Composer" AS "Track1_Composer", 
                                "Track1"."Milliseconds" AS 
                                    "Track1_Milliseconds", 
                                "Track1"."Bytes" AS "Track1_Bytes", 
                                "Track1"."UnitPrice" AS "Track1_UnitPrice", 
                                row_number() OVER (
                                    PARTITION BY "Track1"."AlbumId" 
                                    ORDER BY "Track1"."TrackId" ASC
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
                ) AS "Track1" ON "Album"."AlbumId" = "Track1"."Track1_AlbumId" 
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
                "Track1"."Track1_TrackId" AS "Track1_Track1_TrackId", 
                "Track1"."Track1_Name" AS "Track1_Track1_Name", 
                "Track1"."Track1_AlbumId" AS "Track1_Track1_AlbumId", 
                "Track1"."Track1_MediaTypeId" AS "Track1_Track1_MediaTypeId", 
                "Track1"."Track1_GenreId" AS "Track1_Track1_GenreId", 
                "Track1"."Track1_Composer" AS "Track1_Track1_Composer", 
                "Track1"."Track1_Milliseconds" AS "Track1_Track1_Milliseconds", 
                "Track1"."Track1_Bytes" AS "Track1_Track1_Bytes", 
                "Track1"."Track1_UnitPrice" AS "Track1_Track1_UnitPrice" 
            FROM 
                "Album" 
                LEFT OUTER JOIN (
                    SELECT 
                        q1."Track1_TrackId" AS "Track1_TrackId", 
                        q1."Track1_Name" AS "Track1_Name", 
                        q1."Track1_AlbumId" AS "Track1_AlbumId", 
                        q1."Track1_MediaTypeId" AS "Track1_MediaTypeId", 
                        q1."Track1_GenreId" AS "Track1_GenreId", 
                        q1."Track1_Composer" AS "Track1_Composer", 
                        q1."Track1_Milliseconds" AS "Track1_Milliseconds", 
                        q1."Track1_Bytes" AS "Track1_Bytes", 
                        q1."Track1_UnitPrice" AS "Track1_UnitPrice", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "Track1"."TrackId" AS "Track1_TrackId", 
                                "Track1"."Name" AS "Track1_Name", 
                                "Track1"."AlbumId" AS "Track1_AlbumId", 
                                "Track1"."MediaTypeId" AS "Track1_MediaTypeId", 
                                "Track1"."GenreId" AS "Track1_GenreId", 
                                "Track1"."Composer" AS "Track1_Composer", 
                                "Track1"."Milliseconds" AS 
                                    "Track1_Milliseconds", 
                                "Track1"."Bytes" AS "Track1_Bytes", 
                                "Track1"."UnitPrice" AS "Track1_UnitPrice", 
                                row_number() OVER (
                                    PARTITION BY "Track1"."AlbumId" 
                                    ORDER BY "Track1"."Name" ASC
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
                ) AS "Track1" ON "Album"."AlbumId" = "Track1"."Track1_AlbumId" 
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
                "Invoice1"."Invoice1_InvoiceId" AS 
                    "Invoice1_Invoice1_InvoiceId", 
                "Invoice1"."Invoice1_CustomerId" AS 
                    "Invoice1_Invoice1_CustomerId", 
                "Invoice1"."Invoice1_InvoiceDate" AS 
                    "Invoice1_Invoice1_InvoiceDate", 
                "Invoice1"."Invoice1_BillingAddress" AS 
                    "Invoice1_Invoice1_BillingAddress", 
                "Invoice1"."Invoice1_BillingCity" AS 
                    "Invoice1_Invoice1_BillingCity", 
                "Invoice1"."Invoice1_BillingState" AS 
                    "Invoice1_Invoice1_BillingState", 
                "Invoice1"."Invoice1_BillingCountry" AS 
                    "Invoice1_Invoice1_BillingCountry", 
                "Invoice1"."Invoice1_BillingPostalCode" AS 
                    "Invoice1_Invoice1_BillingPostalCode", 
                "Invoice1"."Invoice1_Total" AS "Invoice1_Invoice1_Total" 
            FROM 
                "Customer" 
                LEFT OUTER JOIN (
                    SELECT 
                        q1."Invoice1_InvoiceId" AS "Invoice1_InvoiceId", 
                        q1."Invoice1_CustomerId" AS "Invoice1_CustomerId", 
                        q1."Invoice1_InvoiceDate" AS "Invoice1_InvoiceDate", 
                        q1."Invoice1_BillingAddress" AS 
                            "Invoice1_BillingAddress", 
                        q1."Invoice1_BillingCity" AS "Invoice1_BillingCity", 
                        q1."Invoice1_BillingState" AS "Invoice1_BillingState", 
                        q1."Invoice1_BillingCountry" AS 
                            "Invoice1_BillingCountry", 
                        q1."Invoice1_BillingPostalCode" AS 
                            "Invoice1_BillingPostalCode", 
                        q1."Invoice1_Total" AS "Invoice1_Total", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "Invoice1"."InvoiceId" AS "Invoice1_InvoiceId", 
                                "Invoice1"."CustomerId" AS 
                                    "Invoice1_CustomerId", 
                                "Invoice1"."InvoiceDate" AS 
                                    "Invoice1_InvoiceDate", 
                                "Invoice1"."BillingAddress" AS 
                                    "Invoice1_BillingAddress", 
                                "Invoice1"."BillingCity" AS 
                                    "Invoice1_BillingCity", 
                                "Invoice1"."BillingState" AS 
                                    "Invoice1_BillingState", 
                                "Invoice1"."BillingCountry" AS 
                                    "Invoice1_BillingCountry", 
                                "Invoice1"."BillingPostalCode" AS 
                                    "Invoice1_BillingPostalCode", 
                                "Invoice1"."Total" AS "Invoice1_Total", 
                                row_number() OVER (
                                    PARTITION BY "Invoice1"."CustomerId" 
                                    ORDER BY "Invoice1"."InvoiceId" ASC
                                ) AS row_number 
                            FROM 
                                "Invoice" AS "Invoice1"
                        ) AS q1 
                    WHERE 
                        q1.row_number >= ? 
                        AND 
                        q1.row_number <= ?
                ) AS "Invoice1" ON 
                    "Invoice1"."Invoice1_CustomerId" = "Customer"."CustomerId" 
            ORDER BY 
                "Customer"."CustomerId" ASC
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        assert expected_query == result

    @staticmethod
    def test_self_ref_composite_id_subquery_with_limit(db_session):
        """Self referential a composite id subquery with a limit"""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(CompositeNode)
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
            embeds=[],
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                "CompositeNode"."NodeId" AS "CompositeNode_NodeId", 
                "CompositeNode"."CompositeId" AS "CompositeNode_CompositeId", 
                "CompositeNode1"."CompositeNode1_NodeId" AS 
                    "CompositeNode1_CompositeNode1_NodeId", 
                "CompositeNode1"."CompositeNode1_CompositeId" AS 
                    "CompositeNode1_CompositeNode1_CompositeId" 
            FROM 
                "CompositeNode" 
                LEFT OUTER JOIN (
                    SELECT 
                        q1."CompositeNode1_NodeId" AS "CompositeNode1_NodeId", 
                        q1."CompositeNode1_CompositeId" AS 
                            "CompositeNode1_CompositeId", 
                        q1."CompositeNodeToCompositeNode_NodeId" AS 
                            "CompositeNodeToCompositeNode_NodeId", 
                        q1."CompositeNodeToCompositeNode_CompositeId" AS 
                            "CompositeNodeToCompositeNode_CompositeId", 
                        q1."CompositeNodeToCompositeNode_ChildNodeId" AS 
                            "CompositeNodeToCompositeNode_ChildNodeId", 
                        q1."CompositeNodeToCompositeNode_ChildCompositeId" AS 
                            "CompositeNodeToCompositeNode_ChildCompositeId", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "CompositeNode1"."NodeId" AS 
                                    "CompositeNode1_NodeId", 
                                "CompositeNode1"."CompositeId" AS 
                                    "CompositeNode1_CompositeId", 
                                "CompositeNodeToCompositeNode"."NodeId" AS 
                                    "CompositeNodeToCompositeNode_NodeId", 
                                "CompositeNodeToCompositeNode"."CompositeId" AS 
                                    "CompositeNodeToCompositeNode_CompositeId", 
                                "CompositeNodeToCompositeNode"."ChildNodeId" AS 
                                    "CompositeNodeToCompositeNode_ChildNodeId", 
                                "CompositeNodeToCompositeNode".
                                    "ChildCompositeId" AS 
                                        "CompositeNodeToCompositeNode_
                                            ChildCompositeId", 
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
                                JOIN "CompositeNodeToCompositeNode" ON 
                                    "CompositeNodeToCompositeNode".
                                        "ChildNodeId" = 
                                    "CompositeNode1"."NodeId" 
                                    AND 
                                    "CompositeNodeToCompositeNode".
                                        "ChildCompositeId" = 
                                    "CompositeNode1"."CompositeId" 
                            WHERE 
                                "CompositeNode1"."NodeId" IN (?, ?)
                        ) AS q1 
                    WHERE 
                        q1.row_number >= ? 
                        AND 
                        q1.row_number <= ?
                ) AS "CompositeNode1" ON 
                    "CompositeNode"."NodeId" = 
                    "CompositeNode1"."CompositeNodeToCompositeNode_NodeId" 
                    AND 
                    "CompositeNode"."CompositeId" = 
                    "CompositeNode1"."CompositeNodeToCompositeNode_CompositeId" 
            ORDER BY 
                "CompositeNode"."NodeId" ASC, 
                "CompositeNode"."CompositeId" ASC
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "").replace(
            "[POSTCOMPILE_NodeId_1]", "?,?")
        assert expected_query == result

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
            limit=3,
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                anon_1."Album_AlbumId" AS "anon_1_Album_AlbumId", 
                anon_1."Album_Title" AS "anon_1_Album_Title", 
                anon_1."Album_ArtistId" AS "anon_1_Album_ArtistId", 
                "Track1"."Track1_TrackId" AS "Track1_Track1_TrackId", 
                "Track1"."Track1_Name" AS "Track1_Track1_Name", 
                "Track1"."Track1_AlbumId" AS "Track1_Track1_AlbumId", 
                "Track1"."Track1_MediaTypeId" AS "Track1_Track1_MediaTypeId", 
                "Track1"."Track1_GenreId" AS "Track1_Track1_GenreId", 
                "Track1"."Track1_Composer" AS "Track1_Track1_Composer", 
                "Track1"."Track1_Milliseconds" AS "Track1_Track1_Milliseconds", 
                "Track1"."Track1_Bytes" AS "Track1_Track1_Bytes", 
                "Track1"."Track1_UnitPrice" AS "Track1_Track1_UnitPrice", 
                "Playlist1"."Playlist1_PlaylistId" AS 
                    "Playlist1_Playlist1_PlaylistId", 
                "Playlist1"."Playlist1_Name" AS "Playlist1_Playlist1_Name" 
            FROM 
                (
                    SELECT 
                        "Album"."AlbumId" AS "Album_AlbumId", 
                        "Album"."Title" AS "Album_Title", 
                        "Album"."ArtistId" AS "Album_ArtistId", 
                        row_number() OVER (
                            ORDER BY 
                                "Album"."AlbumId" ASC
                        ) AS row_number 
                    FROM 
                        "Album"
                ) AS anon_1 
                LEFT OUTER JOIN (
                    SELECT 
                        q1."Track1_TrackId" AS "Track1_TrackId", 
                        q1."Track1_Name" AS "Track1_Name", 
                        q1."Track1_AlbumId" AS "Track1_AlbumId", 
                        q1."Track1_MediaTypeId" AS "Track1_MediaTypeId", 
                        q1."Track1_GenreId" AS "Track1_GenreId", 
                        q1."Track1_Composer" AS "Track1_Composer", 
                        q1."Track1_Milliseconds" AS "Track1_Milliseconds", 
                        q1."Track1_Bytes" AS "Track1_Bytes", 
                        q1."Track1_UnitPrice" AS "Track1_UnitPrice", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "Track1"."TrackId" AS "Track1_TrackId", 
                                "Track1"."Name" AS "Track1_Name", 
                                "Track1"."AlbumId" AS "Track1_AlbumId", 
                                "Track1"."MediaTypeId" AS "Track1_MediaTypeId", 
                                "Track1"."GenreId" AS "Track1_GenreId", 
                                "Track1"."Composer" AS "Track1_Composer", 
                                "Track1"."Milliseconds" AS 
                                    "Track1_Milliseconds", 
                                "Track1"."Bytes" AS "Track1_Bytes", 
                                "Track1"."UnitPrice" AS "Track1_UnitPrice", 
                                row_number() OVER (
                                    PARTITION BY "Track1"."AlbumId" 
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
                        AND q1.row_number <= ?
                ) AS "Track1" ON 
                    anon_1."Album_AlbumId" = "Track1"."Track1_AlbumId" 
                LEFT OUTER JOIN (
                    SELECT 
                        q1."Playlist1_PlaylistId" AS "Playlist1_PlaylistId", 
                        q1."Playlist1_Name" AS "Playlist1_Name", 
                        q1."PlaylistTrack_PlaylistId" AS 
                            "PlaylistTrack_PlaylistId", 
                        q1."PlaylistTrack_TrackId" AS "PlaylistTrack_TrackId", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "Playlist1"."PlaylistId" AS 
                                    "Playlist1_PlaylistId", 
                                "Playlist1"."Name" AS "Playlist1_Name", 
                                "PlaylistTrack"."PlaylistId" AS 
                                    "PlaylistTrack_PlaylistId", 
                                "PlaylistTrack"."TrackId" AS 
                                    "PlaylistTrack_TrackId", 
                                row_number() OVER (
                                    PARTITION BY "PlaylistTrack"."TrackId" 
                                    ORDER BY 
                                        "Playlist1"."Name" ASC
                                ) AS row_number 
                            FROM 
                                "Playlist" AS "Playlist1" 
                                JOIN "PlaylistTrack" ON 
                                    "PlaylistTrack"."PlaylistId" = 
                                    "Playlist1"."PlaylistId" 
                            WHERE 
                                "Playlist1"."PlaylistId" >= ?
                        ) AS q1 
                    WHERE 
                        q1.row_number >= ? 
                        AND q1.row_number <= ?
                ) AS "Playlist1" ON 
                    "Playlist1"."PlaylistTrack_TrackId" = 
                    "Track1"."Track1_TrackId" 
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
            limit=3,
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                anon_1."Playlist_PlaylistId" AS "anon_1_Playlist_PlaylistId", 
                anon_1."Playlist_Name" AS "anon_1_Playlist_Name", 
                "Track1"."Track1_TrackId" AS "Track1_Track1_TrackId", 
                "Track1"."Track1_Name" AS "Track1_Track1_Name", 
                "Track1"."Track1_AlbumId" AS "Track1_Track1_AlbumId", 
                "Track1"."Track1_MediaTypeId" AS "Track1_Track1_MediaTypeId", 
                "Track1"."Track1_GenreId" AS "Track1_Track1_GenreId", 
                "Track1"."Track1_Composer" AS "Track1_Track1_Composer", 
                "Track1"."Track1_Milliseconds" AS "Track1_Track1_Milliseconds", 
                "Track1"."Track1_Bytes" AS "Track1_Track1_Bytes", 
                "Track1"."Track1_UnitPrice" AS "Track1_Track1_UnitPrice", 
                "Playlist1"."Playlist1_PlaylistId" AS 
                    "Playlist1_Playlist1_PlaylistId", 
                "Playlist1"."Playlist1_Name" AS "Playlist1_Playlist1_Name" 
            FROM 
                (
                    SELECT 
                        "Playlist"."PlaylistId" AS "Playlist_PlaylistId", 
                        "Playlist"."Name" AS "Playlist_Name", 
                        row_number() OVER (
                            ORDER BY 
                                "Playlist"."PlaylistId" ASC
                        ) AS row_number 
                    FROM 
                        "Playlist"
                ) AS anon_1 
                LEFT OUTER JOIN (
                    SELECT 
                        q1."Track1_TrackId" AS "Track1_TrackId", 
                        q1."Track1_Name" AS "Track1_Name", 
                        q1."Track1_AlbumId" AS "Track1_AlbumId", 
                        q1."Track1_MediaTypeId" AS "Track1_MediaTypeId", 
                        q1."Track1_GenreId" AS "Track1_GenreId", 
                        q1."Track1_Composer" AS "Track1_Composer", 
                        q1."Track1_Milliseconds" AS "Track1_Milliseconds", 
                        q1."Track1_Bytes" AS "Track1_Bytes", 
                        q1."Track1_UnitPrice" AS "Track1_UnitPrice", 
                        q1."PlaylistTrack_PlaylistId" AS 
                            "PlaylistTrack_PlaylistId", 
                        q1."PlaylistTrack_TrackId" AS "PlaylistTrack_TrackId", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "Track1"."TrackId" AS "Track1_TrackId", 
                                "Track1"."Name" AS "Track1_Name", 
                                "Track1"."AlbumId" AS "Track1_AlbumId", 
                                "Track1"."MediaTypeId" AS "Track1_MediaTypeId", 
                                "Track1"."GenreId" AS "Track1_GenreId", 
                                "Track1"."Composer" AS "Track1_Composer", 
                                "Track1"."Milliseconds" AS 
                                    "Track1_Milliseconds", 
                                "Track1"."Bytes" AS "Track1_Bytes", 
                                "Track1"."UnitPrice" AS "Track1_UnitPrice", 
                                "PlaylistTrack"."PlaylistId" AS 
                                    "PlaylistTrack_PlaylistId", 
                                "PlaylistTrack"."TrackId" AS 
                                    "PlaylistTrack_TrackId", 
                                row_number() OVER (
                                    PARTITION BY 
                                        "PlaylistTrack"."PlaylistId" 
                                    ORDER BY 
                                        "Track1"."Name" ASC
                                ) AS row_number 
                            FROM 
                                "Track" AS "Track1" 
                                JOIN 
                                "PlaylistTrack" ON 
                                    "PlaylistTrack"."TrackId" = 
                                    "Track1"."TrackId" 
                            WHERE 
                                "Track1"."TrackId" >= ?
                        ) AS q1 
                    WHERE 
                        q1.row_number >= ? 
                        AND 
                        q1.row_number <= ?
                ) AS "Track1" ON 
                    anon_1."Playlist_PlaylistId" = 
                    "Track1"."PlaylistTrack_PlaylistId" 
                LEFT OUTER JOIN (
                    SELECT 
                        q1."Playlist1_PlaylistId" AS "Playlist1_PlaylistId", 
                        q1."Playlist1_Name" AS "Playlist1_Name", 
                        q1."PlaylistTrack_PlaylistId" AS 
                            "PlaylistTrack_PlaylistId", 
                        q1."PlaylistTrack_TrackId" AS "PlaylistTrack_TrackId", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "Playlist1"."PlaylistId" AS 
                                    "Playlist1_PlaylistId", 
                                "Playlist1"."Name" AS "Playlist1_Name", 
                                "PlaylistTrack"."PlaylistId" AS 
                                    "PlaylistTrack_PlaylistId", 
                                "PlaylistTrack"."TrackId" AS 
                                    "PlaylistTrack_TrackId", 
                                row_number() OVER (
                                    PARTITION BY 
                                        "PlaylistTrack"."TrackId" 
                                    ORDER BY 
                                        "Playlist1"."Name" ASC
                                ) AS row_number 
                            FROM 
                                "Playlist" AS "Playlist1" 
                                JOIN 
                                "PlaylistTrack" ON 
                                    "PlaylistTrack"."PlaylistId" = 
                                    "Playlist1"."PlaylistId" 
                            WHERE 
                                "Playlist1"."PlaylistId" <= ?
                        ) AS q1 
                    WHERE 
                        q1.row_number >= ? 
                        AND 
                        q1.row_number <= ?
                ) AS "Playlist1" ON 
                    "Playlist1"."PlaylistTrack_TrackId" = 
                    "Track1"."Track1_TrackId" 
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
                "CompositeMany1"."CompositeMany1_ManyId" AS 
                    "CompositeMany1_CompositeMany1_ManyId", 
                "CompositeMany1"."CompositeMany1_OneId" AS 
                    "CompositeMany1_CompositeMany1_OneId", 
                "CompositeMany1"."CompositeMany1_CompositeOneId" AS 
                    "CompositeMany1_CompositeMany1_CompositeOneId" 
            FROM 
                (
                    SELECT 
                        "CompositeOne"."OneId" AS "CompositeOne_OneId", 
                        "CompositeOne"."CompositeOneId" AS 
                            "CompositeOne_CompositeOneId", 
                        row_number() OVER (
                            ORDER BY 
                                "CompositeOne"."OneId" ASC, 
                                "CompositeOne"."CompositeOneId" ASC
                        ) AS row_number 
                    FROM 
                        "CompositeOne"
                ) AS anon_1 
                LEFT OUTER JOIN (
                    SELECT 
                        q1."CompositeMany1_ManyId" AS "CompositeMany1_ManyId", 
                        q1."CompositeMany1_OneId" AS "CompositeMany1_OneId", 
                        q1."CompositeMany1_CompositeOneId" AS 
                            "CompositeMany1_CompositeOneId", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "CompositeMany1"."ManyId" AS 
                                    "CompositeMany1_ManyId", 
                                "CompositeMany1"."OneId" AS 
                                    "CompositeMany1_OneId", 
                                "CompositeMany1"."CompositeOneId" AS 
                                    "CompositeMany1_CompositeOneId", 
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
                        AND q1.row_number <= ?
                ) AS "CompositeMany1" ON 
                    anon_1."CompositeOne_OneId" = 
                    "CompositeMany1"."CompositeMany1_OneId" 
                    AND 
                    anon_1."CompositeOne_CompositeOneId" = 
                    "CompositeMany1"."CompositeMany1_CompositeOneId" 
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
                "CompositeMany1"."CompositeMany1_ManyId" AS 
                    "CompositeMany1_CompositeMany1_ManyId", 
                "CompositeMany1"."CompositeMany1_OneId" AS 
                    "CompositeMany1_CompositeMany1_OneId", 
                "CompositeMany1"."CompositeMany1_CompositeOneId" AS 
                    "CompositeMany1_CompositeMany1_CompositeOneId" 
            FROM 
                "CompositeOne" 
                LEFT OUTER JOIN (
                    SELECT 
                        q1."CompositeMany1_ManyId" AS "CompositeMany1_ManyId", 
                        q1."CompositeMany1_OneId" AS "CompositeMany1_OneId", 
                        q1."CompositeMany1_CompositeOneId" AS 
                            "CompositeMany1_CompositeOneId", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "CompositeMany1"."ManyId" AS 
                                    "CompositeMany1_ManyId", 
                                "CompositeMany1"."OneId" AS 
                                    "CompositeMany1_OneId", 
                                "CompositeMany1"."CompositeOneId" AS 
                                    "CompositeMany1_CompositeOneId", 
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
                        AND q1.row_number <= ?
                ) AS "CompositeMany1" ON 
                    "CompositeOne"."OneId" = 
                    "CompositeMany1"."CompositeMany1_OneId" 
                    AND 
                    "CompositeOne"."CompositeOneId" = 
                    "CompositeMany1"."CompositeMany1_CompositeOneId" 
            ORDER BY 
                "CompositeOne"."OneId" ASC, 
                "CompositeOne"."CompositeOneId" ASC
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        assert expected_query == result

    @staticmethod
    def test_self_ref_one_to_many_limit(db_session):
        """Self referential one to many subquery with a limit"""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Employee)
        subfilters = {
            "subordinates": SubfilterInfo(
                filters={"employee_id": {"$nin": [1, 2]}},
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=EmployeeResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                "Employee"."EmployeeId" AS "Employee_EmployeeId", 
                "Employee"."LastName" AS "Employee_LastName", 
                "Employee"."FirstName" AS "Employee_FirstName", 
                "Employee"."Title" AS "Employee_Title", 
                "Employee"."ReportsTo" AS "Employee_ReportsTo", 
                "Employee"."BirthDate" AS "Employee_BirthDate", 
                "Employee"."HireDate" AS "Employee_HireDate", 
                "Employee"."Address" AS "Employee_Address", 
                "Employee"."City" AS "Employee_City", 
                "Employee"."State" AS "Employee_State", 
                "Employee"."Country" AS "Employee_Country", 
                "Employee"."PostalCode" AS "Employee_PostalCode", 
                "Employee"."Phone" AS "Employee_Phone", 
                "Employee"."Fax" AS "Employee_Fax", 
                "Employee"."Email" AS "Employee_Email", 
                "Employee1"."Employee1_EmployeeId" AS 
                    "Employee1_Employee1_EmployeeId", 
                "Employee1"."Employee1_LastName" AS 
                    "Employee1_Employee1_LastName", 
                "Employee1"."Employee1_FirstName" AS 
                    "Employee1_Employee1_FirstName", 
                "Employee1"."Employee1_Title" AS "Employee1_Employee1_Title", 
                "Employee1"."Employee1_ReportsTo" AS 
                    "Employee1_Employee1_ReportsTo", 
                "Employee1"."Employee1_BirthDate" AS 
                    "Employee1_Employee1_BirthDate", 
                "Employee1"."Employee1_HireDate" AS 
                    "Employee1_Employee1_HireDate", 
                "Employee1"."Employee1_Address" AS 
                    "Employee1_Employee1_Address", 
                "Employee1"."Employee1_City" AS "Employee1_Employee1_City", 
                "Employee1"."Employee1_State" AS "Employee1_Employee1_State", 
                "Employee1"."Employee1_Country" AS 
                    "Employee1_Employee1_Country", 
                "Employee1"."Employee1_PostalCode" AS 
                    "Employee1_Employee1_PostalCode", 
                "Employee1"."Employee1_Phone" AS "Employee1_Employee1_Phone", 
                "Employee1"."Employee1_Fax" AS "Employee1_Employee1_Fax", 
                "Employee1"."Employee1_Email" AS "Employee1_Employee1_Email" 
            FROM 
                "Employee" 
                LEFT OUTER JOIN (
                    SELECT 
                        q1."Employee1_EmployeeId" AS "Employee1_EmployeeId", 
                        q1."Employee1_LastName" AS "Employee1_LastName", 
                        q1."Employee1_FirstName" AS "Employee1_FirstName", 
                        q1."Employee1_Title" AS "Employee1_Title", 
                        q1."Employee1_ReportsTo" AS "Employee1_ReportsTo", 
                        q1."Employee1_BirthDate" AS "Employee1_BirthDate", 
                        q1."Employee1_HireDate" AS "Employee1_HireDate", 
                        q1."Employee1_Address" AS "Employee1_Address", 
                        q1."Employee1_City" AS "Employee1_City", 
                        q1."Employee1_State" AS "Employee1_State", 
                        q1."Employee1_Country" AS "Employee1_Country", 
                        q1."Employee1_PostalCode" AS "Employee1_PostalCode", 
                        q1."Employee1_Phone" AS "Employee1_Phone", 
                        q1."Employee1_Fax" AS "Employee1_Fax", 
                        q1."Employee1_Email" AS "Employee1_Email", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "Employee1"."EmployeeId" AS 
                                    "Employee1_EmployeeId", 
                                "Employee1"."LastName" AS "Employee1_LastName", 
                                "Employee1"."FirstName" AS 
                                    "Employee1_FirstName", 
                                "Employee1"."Title" AS "Employee1_Title", 
                                "Employee1"."ReportsTo" AS 
                                    "Employee1_ReportsTo", 
                                "Employee1"."BirthDate" AS 
                                    "Employee1_BirthDate", 
                                "Employee1"."HireDate" AS "Employee1_HireDate", 
                                "Employee1"."Address" AS "Employee1_Address", 
                                "Employee1"."City" AS "Employee1_City", 
                                "Employee1"."State" AS "Employee1_State", 
                                "Employee1"."Country" AS "Employee1_Country", 
                                "Employee1"."PostalCode" AS 
                                    "Employee1_PostalCode", 
                                "Employee1"."Phone" AS "Employee1_Phone", 
                                "Employee1"."Fax" AS "Employee1_Fax", 
                                "Employee1"."Email" AS "Employee1_Email", 
                                row_number() OVER (
                                    PARTITION BY "Employee1"."ReportsTo" 
                                    ORDER BY 
                                        "Employee1"."EmployeeId" ASC
                                ) AS row_number 
                            FROM 
                                "Employee" AS "Employee1" 
                            WHERE 
                                "Employee1"."EmployeeId" NOT IN (
                                    [POSTCOMPILE_EmployeeId_1])
                        ) AS q1 
                    WHERE 
                        q1.row_number >= ? 
                        AND q1.row_number <= ?
                ) AS "Employee1" ON 
                    "Employee"."EmployeeId" = "Employee1"."Employee1_ReportsTo" 
            ORDER BY 
                "Employee"."EmployeeId" ASC
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        assert expected_query == result

    @staticmethod
    def test_bad_subfilter_ignore_with_limit(db_session):
        """Bad subfilter using a limit gets ignored when not strict."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$bad": 5}},
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True,
            strict=False
        )
        expected_query = (
            """
            SELECT 
                "Album"."AlbumId" AS "Album_AlbumId", 
                "Album"."Title" AS "Album_Title", 
                "Album"."ArtistId" AS "Album_ArtistId", 
                "Track1"."Track1_TrackId" AS "Track1_Track1_TrackId", 
                "Track1"."Track1_Name" AS "Track1_Track1_Name", 
                "Track1"."Track1_AlbumId" AS "Track1_Track1_AlbumId", 
                "Track1"."Track1_MediaTypeId" AS "Track1_Track1_MediaTypeId", 
                "Track1"."Track1_GenreId" AS "Track1_Track1_GenreId", 
                "Track1"."Track1_Composer" AS "Track1_Track1_Composer", 
                "Track1"."Track1_Milliseconds" AS "Track1_Track1_Milliseconds", 
                "Track1"."Track1_Bytes" AS "Track1_Track1_Bytes", 
                "Track1"."Track1_UnitPrice" AS "Track1_Track1_UnitPrice" 
            FROM 
                "Album" 
                LEFT OUTER JOIN (
                    SELECT 
                        q1."Track1_TrackId" AS "Track1_TrackId", 
                        q1."Track1_Name" AS "Track1_Name", 
                        q1."Track1_AlbumId" AS "Track1_AlbumId", 
                        q1."Track1_MediaTypeId" AS "Track1_MediaTypeId", 
                        q1."Track1_GenreId" AS "Track1_GenreId", 
                        q1."Track1_Composer" AS "Track1_Composer", 
                        q1."Track1_Milliseconds" AS "Track1_Milliseconds", 
                        q1."Track1_Bytes" AS "Track1_Bytes", 
                        q1."Track1_UnitPrice" AS "Track1_UnitPrice", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "Track1"."TrackId" AS "Track1_TrackId", 
                                "Track1"."Name" AS "Track1_Name", 
                                "Track1"."AlbumId" AS "Track1_AlbumId", 
                                "Track1"."MediaTypeId" AS "Track1_MediaTypeId", 
                                "Track1"."GenreId" AS "Track1_GenreId", 
                                "Track1"."Composer" AS "Track1_Composer", 
                                "Track1"."Milliseconds" AS 
                                    "Track1_Milliseconds", 
                                "Track1"."Bytes" AS "Track1_Bytes", 
                                "Track1"."UnitPrice" AS "Track1_UnitPrice", 
                                row_number() OVER (
                                    PARTITION BY "Track1"."AlbumId" 
                                    ORDER BY 
                                        "Track1"."TrackId" ASC
                                ) AS row_number 
                            FROM 
                                "Track" AS "Track1"
                        ) AS q1 
                    WHERE 
                        q1.row_number >= ? 
                        AND q1.row_number <= ?
                ) AS "Track1" ON "Album"."AlbumId" = "Track1"."Track1_AlbumId" 
            ORDER BY 
                "Album"."AlbumId" ASC
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        assert expected_query == result


class TestDrowsyQueryBuilderRowNumSupport(DrowsyDatabaseTests):

    """Query builder tests for dialects supporting row_number."""

    backends = ['mssql', 'postgres']

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
            embeds=[]
        )
        results = query.all()
        # offset test
        assert results[0].album_id == 1
        assert results[0].tracks[0].track_id == 7
        for album in results:
            assert len(album.tracks) <= 1
            for track in album.tracks:
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

    @staticmethod
    def test_self_ref_one_to_many_limit(db_session):
        """Self referential one to many subquery with a limit"""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Employee)
        subfilters = {
            "subordinates": SubfilterInfo(
                filters={"employee_id": {"$nin": [1, 2]}},
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=EmployeeResource(session=db_session),
            subfilters=subfilters,
            embeds=[]
        )
        results = query.all()
        assert len(results) == 8
        for manager in results:
            assert len(manager.subordinates) <= 1
            for subordinate in manager.subordinates:
                assert subordinate.employee_id not in [1, 2]

    @staticmethod
    def test_bad_subfilter_ignore_with_limit(db_session):
        """Bad subfilter using a limit gets ignored when not strict."""
        query_builder = ModelResourceQueryBuilder()
        query = db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$bad": 5}},
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            strict=False
        )
        results = query.all()
        assert len(results) > 0
        for album in results:
            assert len(album.tracks) <= 1
