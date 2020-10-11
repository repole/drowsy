=======
Changes
=======

Release 0.1.3
=============

Features Added
--------------
* Data is now attached to ``ResourceSchema`` as ``loaded_data`` while
  being loaded. Allows for option of child schemas to see what data the
  parent is currently loading.
* Nested objects will no longer trigger an ``"update"`` action when the
  object has no data provided other than identifying keys.

Bug Fixes
---------
* Avoid updating primary key's unnecessarily on loads of existing objects.


Release 0.1.2
=============

Features Added
--------------
* ``ModelResourceRouter`` can now be passed a ``convert_types_func`` to
  handle converting identifiers in the url slug to the corresponding
  database type. Useful for handling non primitive identifiers.

Bug Fixes
---------
* Handle composite Primary Keys that also act as Foreign Keys gracefully.
* Fix issues with embedding relationships that have a different ``data_key``
  than their default field name.
* Fix handling of required fields on nested entities when their values are
  implied by their relation to their parent.


Release 0.1.1
=============

Bug Fixes
---------
* Fix ``ModelResourceConverter`` to include a Foreign Key when it's also a
  Primary Key, even if ``include_fk`` is set to ``False``.
* Fix ``convert_key_name`` bug causing it to fail with
  ``CamelModelResourceConverter``.


Release 0.1.0
=============

Features added
--------------
* Permission handling for resource CRUD operations.
* Permission handling for relationship operations.
* Ability to properly handle nested required filters.
