.. _why:

Why?
====

Motivations
-----------

This project started from a desire to be able to query and modify
nested resources. Since its beginning, GraphQL has hit the mainstream
and become a popular way to accomplish those same goals, but I don't
believe the break from REST is a necessary one, and this library aims to
help provide similar features through a REST API.


What makes Drowsy different?
----------------------------

While there are plenty of toolkits and libraries out there to help make
building REST APIs easier, Drowsy attempts to distinguish itself in the
depth of access to nested resources it provides.

It does this by making some very opinionated choices in ORM (SQLAlchemy),
serialization and deserialization library (Marshmallow), and language
(Python). Beyond those choices, Drowsy allows a great deal of flexibility
and freedom in how to build your API through its modularity.
