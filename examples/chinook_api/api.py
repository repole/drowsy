"""
    chinook_api.api
    ~~~~~~~~~~~~~~~

    Simple implementation of a Flask API using Drowsy.

"""
# :copyright: (c) 2020 by Nicholas Repole and contributors.
#             See AUTHORS for more details.
# :license: MIT - See LICENSE for more details.
import json
import logging
import os
from flask import Flask, request, Response, url_for, g
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, scoped_session
from drowsy.exc import (
    UnprocessableEntityError, BadRequestError, MethodNotAllowedError,
    ResourceNotFoundError
)
from drowsy.resource import ResourceCollection
from drowsy.router import ModelResourceRouter
from .resources import *

app = Flask(__name__)

LOGGER = logging.getLogger('api')

# Set up SQLAlchemy session factory
# You'll probably want to do this more robustly in a real app.
DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "chinook.sqlite")
DB_ENGINE = create_engine("sqlite+pysqlite:///" + DB_PATH)


@app.before_request
def prepare_db_session():
    """Prepare a database session and attach it to Flask.g"""
    g.db_session = scoped_session(sessionmaker(bind=DB_ENGINE))


@app.teardown_request
def end_db_session(error):
    """Commit any changes or rollback on failure."""
    if hasattr(g, "db_session"):
        db_session = g.db_session
        try:
            if error:
                raise error
            db_session.commit()
        except SQLAlchemyError:
            db_session.rollback()
            LOGGER.exception("Error committing changes, rolling back.")
        finally:
            db_session.remove()


def url_for_other_page(page):
    """Simple helper function for pagination headers."""
    args = dict(
        request.view_args.items() | request.args.to_dict().items())
    args['page'] = page
    return url_for(request.endpoint, **args)


@app.route(
    "/api/<path:path>",
    methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS", "HEAD"])
def api_router(path):
    """Generic API router.

    You'll probably want to be more specific with your routing.

    We're using the ModelResourceRouter, which automatically routes
    based on the class name of each Resource, and handles nested
    routing, querying, and updating automatically.

    """
    # This should be some context related to the current request.
    # Note that context can be used by resources/schemas to help
    # handle things like permissions/access, and would typically
    # contain any user related info for this request.
    context = {}
    router = ModelResourceRouter(session=g.db_session, context=context)
    # query params are used to parse fields to include, embeds,
    # sorts, and filters.
    query_params = request.values.to_dict()
    errors = None
    status = 200
    response_headers = {}
    try:
        if request.method.upper() == "POST":
            status = 201
        result = router.dispatcher(
            request.method,
            path,
            query_params=query_params,
            data=request.json)
        if result is None:
            status = 204
        if request.method.upper() == "OPTIONS":
            response_headers["Allow"] = ",".join(result)
            result = None
        if isinstance(result, ResourceCollection):
            # Handle providing prev, next, first, last page links header
            links = []
            if result.current_page is not None:
                link_template = '<{link}>; rel="{rel}"'
                if result.first_page:
                    links.append(link_template.format(
                        link=url_for_other_page(result.first_page),
                        rel="first"))
                if result.previous_page:
                    links.append(link_template.format(
                        link=url_for_other_page(result.previous_page),
                        rel="prev"))
                if result.next_page:
                    links.append(link_template.format(
                        link=url_for_other_page(result.next_page),
                        rel="next"))
                if result.last_page:
                    links.append(link_template.format(
                        link=url_for_other_page(result.last_page),
                        rel="last"))
            links_str = ",".join(links)
            if links_str:
                response_headers["Link"] = links_str
            # Handle successful HEAD requests
            if request.method.upper() == "HEAD":
                result = None
        if result is not None:
            result = json.dumps(result)
        return Response(
            result,
            headers=response_headers,
            mimetype="application/json",
            status=status
        )
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
    if code is not None or message:
        if request.method.upper() == "HEAD":
            result = None
        else:
            result = {"message": message, "code": code}
            if errors:
                result["errors"] = errors
        return Response(
            json.dumps(result),
            mimetype="application/json",
            status=status)
