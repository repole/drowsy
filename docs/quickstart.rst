.. _quickstart:

Quickstart
==========

This page is intended to help get you off and running with Drowsy as quickly as
possible. To do that, we'll be walking through the creation of an example API
using the Chinook Sqlite database that comes bundled with Drowsy's tests, and
Flask as our web framework. Note that Drowsy is web framework agnostic, and
that Flask is by no means a requirement.

Some familiarity with SQLAlchemy and Marshmallow is assumed prior to working
with Drowsy.

A working version of all of the below code can be found in the examples that
come bundled in the Drowsy distribution, under the chinook_api folder.


Defining Models
---------------

The first thing you'll need to do is define your SQLAlchemy models. Hopefully
you're familiar with SQLAlchemy already, but as a quick example, we'll define
a few models here:

.. code:: python

    from sqlalchemy import Column, ForeignKey, Integer, Unicode, orm
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.schema import ForeignKeyConstraint


    Base = declarative_base()
    metadata = Base.metadata


    class Album(Base):

        """SQLAlchemy model for the Album table in our database."""

        __tablename__ = 'Album'

        album_id = Column("AlbumId", Integer, primary_key=True)
        title = Column("Title", Unicode(160), nullable=False)
        artist_id = Column(
            "ArtistId", ForeignKey('Artist.ArtistId'),
            nullable=False, index=True)

        artist = orm.relationship('Artist', backref="albums")


    class Artist(Base):

        """SQLAlchemy model for the Artist table in our database."""

        __tablename__ = 'Artist'

        artist_id = Column("ArtistId", Integer, primary_key=True)
        name = Column("Name", Unicode(120)

A complete set of example model definitions can be seen in
`models.py <../examples/chinook_api/models.py>`_.


Defining Schemas
----------------

Once you've defined some models, the next step is to define some schemas.
Schemas handle a number of important tasks, including serializing data from
model instances, and validating and deserializing user input into model
instances.

Drowsy provides the :class:`~drowsy.schema.ModelResourceSchema` class as the
main building block to creating schemas around your models.

.. code:: python

    from drowsy.convert import CamelModelResourceConverter
    from drowsy.schema import ModelResourceSchema
    from chinook_api.models import (
        Album, Artist, CompositeOne, CompositeMany, CompositeNode,
        Customer, Employee, Genre, Invoice, InvoiceLine, MediaType,
        Node, Playlist, Track
    )


    class AlbumSchema(ModelResourceSchema):
        class Meta:
            model = Album
            model_converter = CamelModelResourceConverter


    class ArtistSchema(ModelResourceSchema):
        class Meta:
            model = Artist
            model_converter = CamelModelResourceConverter


Here we're using a :class:`~drowsy.convert.CamelModelResourceConverter` to
do a lot of work behind the scenes for us. The job of the converter is to take
fields from the specified ``model`` and turn them into fields for the schema.
In this case, using the :class:`~drowsy.convert.CamelModelResourceConverter`
rather than the standard :class:`~drowsy.convert.ModelResourceConverter` will
convert field names like ``album_id`` to ``albumId``, to make the serialized
result conform to standard JSON best practices.

There's a good chance you'll want to extend one of the included converters
and create your own, as currently they include child resources by default
and are very permissive. Also note that you can always explicitly define schema
fields individually as you would in any other Marshmallow schema, if using
one of the converters feels too much like magic for your taste.

A complete set of example schema definitions can be seen in
`schemas.py <../examples/chinook_api/schemas.py>`_.


Defining Resources
------------------

After defining some schemas, the next step is to define our resources.
Resources utilize schemas to perform CRUD style operations, and help manage any
nested resource embedding in API query results.

.. code:: python

    from drowsy.resource import ModelResource
    from chinook_api.schemas import AlbumSchema, ArtistSchema


    class AlbumResource(ModelResource):
        class Meta:
            schema_cls = AlbumSchema


    class ArtistResource(ModelResource):
        class Meta:
            schema_cls = ArtistSchema


A complete set of example resource definitions can be seen in
`resources.py <../examples/chinook_api/resources.py>`_.


Routing
-------

The bulk of work is now done, and now we just need to tie it all together.
We'll be using Flask here, but again, the same principals will apply in any
other Python web framework.

To put everything together, we'll create a single endpoint that relies on a
:class:`~drowsy.router.ModelResourceRouter` to use the URL and determine
which :class:`~drowsy.resource.ModelResource` the request should go to. The
router also makes use of :class:`~drowsy.parser.ModelQueryParamParser` to
parse out user supplied filters, embeds, and more from query parameters.

.. code:: python

    import os
    import json
    from flask import Flask
    from flask import request, Response
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from drowsy.exc import (
        UnprocessableEntityError, BadRequestError, MethodNotAllowedError,
        ResourceNotFoundError
    )
    from drowsy.router import ModelResourceRouter
    from chinook_api.models import *
    from chinook_api.schemas import *
    from chinook_api.resources import *


    app = Flask(__name__)


    # Set up SQLAlchemy session factory
    # You'll want to do this more robustly in a real app.
    db_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "chinook.sqlite")
    connect_string = "sqlite+pysqlite:///" + db_path
    db_engine = create_engine(connect_string)
    db_session_cls = sessionmaker(bind=db_engine)


    @app.route("/api/<path:path>",
               methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
    def api_router(path):
        """Generic API router.

        You'll probably want to be more specific with your routing.

        We're using the ModelResourceRouter, which automatically routes
        based on the class name of each Resource, and handles nested
        routing, querying, and updating automatically.

        """
        # get your SQLAlchemy db session however you normally would
        db_session = db_session_cls()
        # query params are used to parse fields to include, embeds,
        # sorts, and filters.
        router = ModelResourceRouter(session=db_session)
        query_params = request.values.to_dict()
        errors = None
        message = None
        code = None
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
                result = json.dumps(result)
            return Response(
                result,
                mimetype="application/json",
                status=status)
        except UnprocessableEntityError as exc:
            status = 433
            errors = exc.errors
            message = exc.message
            code = exc.code
        except MethodNotAllowedError as exc:
            status = 405
            message = exc.message
            code = exc.code
        except BadRequestError as exc:
            status = 400
            message = exc.message
            code = exc.code
        except ResourceNotFoundError as exc:
            status = 404
            message = exc.message
            code = exc.code
            print(code)
        if code is not None or message:
            result = {"message": message, "code": code}
            if errors:
                result["errors"] = errors
            return Response(
                json.dumps(result),
                mimetype="application/json",
                status=status)

    if __name__ == '__main__':
        # Never run with debug in production!
        app.run(debug=True)

You can now run this the same way you would any other Flask app and have an
incredibly flexible API up and running in front of your database.

Keep in mind that this is a very, very simplistic implementation. Routing is
done here using resource class name, such that the resource used for the path
``/albums`` is determined by transforming ``albums`` to upper camel case
(``Albums``), using the ``inflection`` library to remove pluralization
(``Album``), and adding ``Resource`` to the end (``AlbumResource``). If this
feels too much like magic for your tastes, and I don't blame you if so, you can
pass the resource you want to use in explicitly to the router's constructor and
have separate routing definitions for each top level resource. You're also more
than welcome to handle routing on your own if the included
:class:`~drowsy.router.ModelResourceRouter` doesn't handle your use cases.


Next Steps
----------

Now that you've got an actual API up and running, you can head over to the
:ref:`querying`, :ref:`creating_updating`, and :ref:`deleting` sections to
get an overview of how to interact with your new API.

You'll also want to be sure to check out the :ref:`permissions` section to
gain an understanding of how to properly secure a Drowsy based API.
