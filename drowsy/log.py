"""
    drowsy.log
    ~~~~~~~~~~

    Tools for class level logging.

"""
# :copyright: (c) 2016-2020 by Nicholas Repole and contributors.
#             See AUTHORS for more details.
# :license: MIT - See LICENSE for more details.
import logging

_logged_classes = set()


class Loggable(object):

    """Embeds a logger object into any class.

    Inherit from this class to be able to call self.logger in any class.

    """
    @property
    def logger(self):
        if not hasattr(self, "_logger"):
            cls = self.__class__
            self._logger = logging.getLogger(
                cls.__module__ + "." + cls.__name__)
            _logged_classes.add(cls)
        return self._logger
