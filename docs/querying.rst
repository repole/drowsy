.. _querying:

Querying
========

Say you’re building an API for your music collection, and you want to be
able to accept query params and use them to filter results. An example
using Flask might look like:

.. code:: python

    from flask import Flask
    from flask import request
    import inflection
    from models import *
    from drowsy.schema import ModelSchema
    from drowsy.resource import ModelResource
    from drowsy.router import ModelResurceRouter
    from drowsy import class_registry

    # Should handle this in a separate file and import these...
    # Create schemas for your models
    # Fields are auto generated based on the SQLAlchemy model using
    # drowsy's built in ModelConverter. Any field can easily be
    # overriden to support hiding a field, marking it as read only,
    # or customized in pretty much any other way.
    # Overriding ModelSchema and using a custom ModelConverter is also
    # an option.
    class AlbumSchema(ModelSchema):
       class Meta:
           model = Album

    # Create a resource for your schema
    class AlbumResource(ModelResource):
        class Meta:
            schema_class = AlbumSchema

    # Also be sure to either create schemas and resources for all your
    # other models, or expliclity exclude relationship fields on your
    # schemas that may reference models that don't have associated
    # schemas and resources.
    # Or in simpler terms, if you want to be able to embed tracks in
    # an album resource, you need to have defined a tracks resource.


    @app.route("/api/<path:path>",
               methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
    def api_router(path):
        """Generic API router.

        You'll probably want to be more specific with your routing.

        """
        # get your SQLAlchemy db session however you normally would
        db_session = ...
        # query params are used to parse fields to include, embeds,
        # sorts, and filters.
        query_params = request.values.to_dict()
        errors = None
        status = 200
        try:
            if request.method.lower() == "POST":
                status = 201
            result = router.dispatcher(
                request.method,
                path,
                query_params=query_params,
                data=request.json)
            if result is None:
                status = 209
            else:
                result = simplejson.dumps(
                    result,
                    indent=4,
                    sort_keys=True)
            return Response(
                result,
                mimetype="application/json",
                status=status)
        except UnprocessableEntityError as e:
            status = 433
            errors = e.errors
        except MethodNotAllowedError as e:
            status = 405
        except BadRequestError as e:
            status = 400
        except ResourceNotFoundError as e:
            status = 404
        if e:
            result = {"message": e.message, "code": e.kwargs["code"]}
            if errors:
                result["errors"] = errors
            return Response(
                simplejson.dumps(
                    result,
                    indent=4,
                    sort_keys=True
                ),
                mimetype="application/json",
                status=status)

Note the use of the ``ModelResourceRouter`` is very much optional and is used
purely for brevity here. Separate end points for each resource type could, and
probably should, be used in most situations.

Once a resource has an endpoint set up for it, some very powerful filtering
and resource creating or updating can be done.

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
By default, any field or nested resource field that isn't `load_only` can be
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
Embed full relationships or fields of relationships:

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


Limitations
-----------

Given that we're dependent on SQLAlchemy's ORM, there are a few
limitations to the results that we receive from the API.

1. Attempting to embed (or subfilter) the same relationship multiple times
   in the same query will result in an error. This is something intended to
   be worked around in the future, but given the way SQLAlchemy's
   `contains_eager` relationship loading technique works, it'll require a
   significant change to how Drowsy handles embedding.

2. The MQLAlchemy parser is an iterative process, and has a default limit
   on how complex of a query it will attempt to parse (intended to prevent
   malicious attempts to overload a server). If you find that you're hitting
   this limitation in a real world use case, let us know by filing an issue
   on GitHub.
