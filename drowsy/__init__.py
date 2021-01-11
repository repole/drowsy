"""
    drowsy.__init__
    ~~~~~~~~~~~~~~~

    Root of the Drowsy module.

"""
# :copyright: (c) 2016-2020 by Nicholas Repole and contributors.
#             See AUTHORS for more details.
# :license: MIT - See LICENSE for more details.
import logging
from logging import NullHandler

logging.getLogger(__name__).addHandler(NullHandler())


__version__ = "0.1.5"
