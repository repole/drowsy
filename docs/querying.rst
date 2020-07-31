.. _querying:

Querying
========

Querying your Drowsy based API can be done via GET requests and supports a wide
range of filtering, nested embedding, and pagination options.

The examples below will walk you through some query basics and advanced
features using the API described in :ref:`quickstart`. If you want to follow
along, run the example ``chinook_api`` app and try these same get requests
yourself.


Filtering by Unique Identifier
------------------------------

Access individual resources using their primary key value (or setting a custom
field to use as an ID on the ModelResource object):

.. sourcecode:: http

    GET /api/albums/2 HTTP/1.1

.. sourcecode:: http

    HTTP/1.1 200 OK

    {
        "album_id": 2,
        "artist": "/albums/2/artist",
        "self": "/albums/2",
        "title": "Balls to the Wall",
        "tracks": "/albums/2/tracks"
    }


Collection Filtering
--------------------

By default, any field or nested resource field that isn't ``load_only`` can be
queried. This can be turned on or off on a field by field basis if desired.

Query for things that are >, >=, =<, <, != by appending -gt, -gte,
-lt, -lte, -ne respectively to the parameter name.

.. sourcecode:: http

    GET /api/albums?album_id-lte=10&album_id-gt>8 HTTP/1.1

.. sourcecode:: http

    HTTP/1.1 200 OK

    [
        {
            "album_id": 9,
            "artist":  "/albums/9/artist",
            "self": "/albums/9",
            "title": "Plays Metallica By Four Cellos",
            "tracks": "/albums/9/tracks"
        },
        {
            "album_id": 10,
            "artist":  "/albums/10/artist",
            "self": "/albums/10",
            "title": "Audioslave",
            "tracks": "/albums/10/tracks"
        }
    ]


Query text fields for partial matches using -like.

.. sourcecode:: http

    GET /api/albums?albums?title-like=salute HTTP/1.1

.. sourcecode:: http

    HTTP/1.1 200 OK

    [
        {
            "album_id": 1,
            "artist": {
                "self": "/artists/1"
            },
            "self": "/albums/1",
            "title": "For Those About To Rock We Salute You",
            "tracks": "/albums/1/tracks"
        }
    ]


Advanced Filtering
------------------

Query using complex MQLAlchemy style filters:

.. sourcecode:: http

    GET /api/tracks?query={"$and":[{"unit_price":{"$lte":1}},{"album.album_id":2}]} HTTP/1.1

.. sourcecode:: http

    HTTP/1.1 200 OK

    [
        {
            "album": {
                "self": "/albums/2"
            },
            "bytes": 5510424,
            "composer": null,
            "genre": {
                "self": "/genres/1"
            },
            "media_type": {
                "self": "/mediaTypes/2"
            },
            "milliseconds": 342562,
            "name": "Balls to the Wall",
            "playlists": "/tracks/2/playlists",
            "self": "/tracks/2",
            "track_id": 2,
            "unit_price": 0.99
        }
    ]


Embedding Relationships and Fields
----------------------------------

Embed full relationships or fields of relationships by specifying ``embeds``
as a query string parameter:

.. sourcecode:: http

    GET /api/albums/2?embeds=artist,tracks.name&limit=1 HTTP/1.1

.. sourcecode:: http

    HTTP/1.1 200 OK

    {
        "album_id": 2,
        "artist": {
            "artistId": 2,
            "name": "Accept",
            "self": "/artists/2"
        },
        "self": "/albums/2",
        "title": "Balls to the Wall",
        "tracks": [
            {
                "name": "Balls to the Wall"
            }
        ]
    }


Choose fields you want returned explicitly:

.. sourcecode:: http

    GET /api/albums/2?fields=title,album_id HTTP/1.1

.. sourcecode:: http

    HTTP/1.1 200 OK

    {
        "album_id": 2,
        "title": "Balls to the Wall"
    }


Offset, Limit, and Pagination
-----------------------------
Use limit for any end point:

.. sourcecode:: http

    GET /api/albums&limit=2 HTTP/1.1

.. sourcecode:: http

    HTTP/1.1 200 OK

    [
        {
            "album_id": 1,
            "artist": "/albums/1/artist",
            "self": "/albums/1",
            "title": "For Those About To Rock We Salute You",
            "tracks": "/albums/1/tracks"
        },
        {
            "album_id": 2,
            "artist": "/albums/2/artist",
            "self": "/albums/2",
            "title": "Balls to the Wall",
            "tracks": "/albums/2/tracks"
        }
    ]


Use offset for any end point:

.. sourcecode:: http

    GET /api/albums&limit=1&offset=1 HTTP/1.1

.. sourcecode:: http

    HTTP/1.1 200 OK

    [
        {
            "album_id": 2,
            "artist": "/albums/2/artist",
            "self": "/albums/2",
            "title": "Balls to the Wall",
            "tracks": "/albums/2/tracks"
        }
    ]


Paginate any end point (limit can be used to set page size):

.. sourcecode:: http

    GET /api/albums&page=2limit=5 HTTP/1.1

.. sourcecode:: http

    HTTP/1.1 200 OK

    [
         {
            "album_id": 6,
            "artist": "/albums/6/artist",
            "self": "/albums/6",
            "title": "Jagged Little Pill",
            "tracks": "/albums/6/tracks"
        },
        {
            "album_id": 7,
            "artist":  "/albums/7/artist",
            "self": "/albums/7",
            "title": "Facelift",
            "tracks": "/albums/7/tracks"
        },
        {
            "album_id": 8,
            "artist":  "/albums/8/artist",
            "self": "/albums/8",
            "title": "Warner 25 Anos",
            "tracks": "/albums/8/tracks"
        },
        {
            "album_id": 9,
            "artist":  "/albums/9/artist",
            "self": "/albums/9",
            "title": "Plays Metallica By Four Cellos",
            "tracks": "/albums/9/tracks"
        },
        {
            "album_id": 10,
            "artist":  "/albums/10/artist",
            "self": "/albums/10",
            "title": "Audioslave",
            "tracks": "/albums/10/tracks"
        }
    ]


Convert Fields to camelCase
---------------------------

Schemas can easily be defined to serialize and deserialize using lower
camelCase field names to be more JavaScript convention friendly.

.. code:: python

    class AlbumSchema(ModelResourceSchema):
        class Meta:
            model = Album
            converter = CamelModelResourceConverter
            include_relationships = True

.. sourcecode:: http

    GET /api/albums/2 HTTP/1.1

.. sourcecode:: http

    HTTP/1.1 200 OK

    {
        "albumId": 2,
        "artist": "/albums/2/artist",
        "self": "/albums/2",
        "title": "Balls to the Wall",
        "tracks": "/albums/2/tracks"
    }

Note that the ``album_id`` field here has been converted to ``albumId``.


Nested Queries
--------------

One of the more powerful things Drowsy allows is to query nested relationships
of objects. This can take a few different forms, the first of which involves
filtering top level objects based on whether their relationships meet a
particular example:


.. sourcecode:: http

    GET /api/albums?tracks.track_id=1 HTTP/1.1

.. sourcecode:: http

    HTTP/1.1 200 OK

    [
        {
            "album_id": 1,
            "artist": "/albums/1/artist",
            "self": "/albums/1",
            "title": "For Those About To Rock We Salute You",
            "tracks": "/albums/1/tracks"
        }
    ]

Here we're looking for all albums that contain an object in ``tracks`` that
has a ``track_id`` of ``1``. Seeing as a track can only ever be in one
album, a more realistic query much be something like
``/api/albums?tracks.genre.name=Rock``, which would return all albums
that contain a track that has a genre of Rock.

The other way you query nested resources is by filtering the results of your
embeds. For example, perhaps you want to retrieve an album, embed it's tracks,
and only include the tracks with a genre of Rock:

.. sourcecode:: http

    GET /api/albums/112?tracks._subquery_.genre.name=Rock HTTP/1.1

.. sourcecode:: http

    HTTP/1.1 200 OK

    {
        "self": "/albums/112",
        "artist": "/albums/112/artist",
        "tracks": [
            {
                "composer": "Steve Harris",
                "unit_price": 0.99,
                "invoice_lines": "/tracks/1393/invoice_lines",
                "media_type": "/tracks/1393/media_type",
                "self": "/tracks/1393",
                "bytes": 11737216,
                "playlists": "/tracks/1393/playlists",
                "album": "/tracks/1393/album",
                "track_id": 1393,
                "name": "The Number Of The Beast",
                "milliseconds": 293407,
                "genre": "/tracks/1393/genre"
            }
        ],
        "album_id": 112,
        "title": "The Number of The Beast"
    }

This same album contains 9 other tracks (all classified as Metal), but in
our result we get the lone Rock track on the album. Note the use of
``_subquery_`` in the filter can be overridden with some other syntax
if you prefer by providing an alternative to
:meth:`~drowsy.parser.ModelQueryParamParser.parse_subfilters`.

Along with ``_subquery_``, you can also specify a ``_limit_`` and/or
``_offset_``, and optionally ``_sorts_`` to essentially paginate the nested
objects. By default, the nested objects will be sorted by their identifying
data key(s), so if you want the first two tracks of an Album you can try a
query like ``/api/albums/112?tracks._limit_=2``. If you want the next two,
you can use ``/api/albums/112?tracks._limit_=2&tracks._offset_=2``.

Tying all of this together, the below is essentially the second page of Metal
tracks (2 per page) on a particular album, sorted by name descending (note the
``-`` in front of the provided sort).

.. sourcecode:: http

    GET /api/albums/112?tracks._subquery_.genre.name=Metal&tracks._limit_=2&tracks._offset_=2&tracks._sorts_=-name HTTP/1.1

.. sourcecode:: http

    HTTP/1.1 200 OK

    {
        "self": "/albums/112",
        "title": "The Number of The Beast",
        "tracks": [
            {
                "self": "/tracks/1391",
                "track_id": 1391,
                "media_type": "/tracks/1391/media_type",
                "bytes": 2849181,
                "genre": "/tracks/1391/genre",
                "composer": "Steve Harris",
                "name": "Invaders",
                "playlists": "/tracks/1391/playlists",
                "milliseconds": 203180,
                "invoice_lines": "/tracks/1391/invoice_lines",
                "unit_price": 0.99,
                "album": "/tracks/1391/album"
            },
            {
                "self": "/tracks/1390",
                "track_id": 1390,
                "media_type": "/tracks/1390/media_type",
                "bytes": 6006107,
                "genre": "/tracks/1390/genre",
                "composer": "Steve Harris",
                "name": "Hallowed Be Thy Name",
                "playlists": "/tracks/1390/playlists",
                "milliseconds": 428669,
                "invoice_lines": "/tracks/1390/invoice_lines",
                "unit_price": 0.99,
                "album": "/tracks/1390/album"
            }
        ],
        "artist": "/albums/112/artist",
        "album_id": 112
    }

For reference, the ``_sorts_`` parameter can also be a comma separated list if
you want to provide multiple sort criteria.

Lastly, the simplest way to access nested objects is to access them as their own
collection:

.. sourcecode:: http

    GET /api/albums/264/tracks HTTP/1.1

.. sourcecode:: http

    HTTP/1.1 200 OK

    [
        {
            "self": "/tracks/3352",
            "track_id": 3352,
            "media_type": "/tracks/3352/media_type",
            "bytes": 5327463,
            "genre": "/tracks/3352/genre",
            "composer": "Karsh Kale/Vishal Vaid",
            "name": "Distance",
            "playlists": "/tracks/3352/playlists",
            "milliseconds": 327122,
            "invoice_lines": "/tracks/3352/invoice_lines",
            "unit_price": 0.99,
            "album": "/tracks/3352/album"
        },
        {
            "self": "/tracks/3358",
            "track_id": 3358,
            "media_type": "/tracks/3358/media_type",
            "bytes": 6034098,
            "genre": "/tracks/3358/genre",
            "composer": "Karsh Kale",
            "name": "One Step Beyond",
            "playlists": "/tracks/3358/playlists",
            "milliseconds": 366085,
            "invoice_lines": "/tracks/3358/invoice_lines",
            "unit_price": 0.99,
            "album": "/tracks/3358/album"
        }
    ]

You can also supply filters, sorts, pagination, or any other parameters to such
a request the same way you would any other query.


Limitations
-----------

While Drowsy is incredibly flexible in how much it will let you do in one
single query, there are a few limitations to note:

1. Attempting to embed (or subquery) the same relationship multiple times
   in the same query will result in an error. This is something intended to
   be worked around in the future, but given the way SQLAlchemy's
   ``contains_eager`` relationship loading technique works, it'll require a
   significant change to how Drowsy handles embedding.

2. The MQLAlchemy parser used by Drowsy is an iterative process, and has a
   default limit on how complex of a query it will attempt to parse (intended
   to prevent malicious attempts to overload a server). If you find that
   you're hitting this limitation in a real world use case, let us know by
   filing an issue on GitHub.


More Examples
-------------

The included test suite, in particular the
`test_query_builder.py <_modules/tests/test_query_builder.html#TestDrowsyResource>`_
file contains more in depth examples that may be useful to look through.
