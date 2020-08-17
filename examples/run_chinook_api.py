"""
    examples.run_chinook_api
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Launches the example Chinook API project using debug server.

"""
# :copyright: (c) 2020 by Nicholas Repole and contributors.
#             See AUTHORS for more details.
# :license: MIT - See LICENSE for more details.
import os
import sys
root_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..')
print(root_path)
sys.path.insert(0, root_path)
from chinook_api.api import app


if __name__ == '__main__':
    # Never run with debug in production!
    app.run(debug=True)
