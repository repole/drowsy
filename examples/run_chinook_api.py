"""
    examples.run_chinook_api
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Launches the example Chinook API project using debug server.

"""
# :copyright: (c) 2020 by Nicholas Repole and contributors.
#             See AUTHORS for more details.
# :license: MIT - See LICENSE for more details.
from chinook_api.api import app

if __name__ == '__main__':
    # Never run with debug in production!
    app.run(debug=True)
