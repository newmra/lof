"""
xnodes: Exchange nodes framework
        Simplistic event framework which enables unrelated nodes to exchange information, alter each other states and
        provides the possibility to undo made changes.

Author: Ralph Neumann (@newmra)

This framework is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
License as published by the Free Software Foundation, see <https://www.gnu.org/licenses/>.
"""

from typing import Callable

X_EVENT_HANDLER_FLAG = "XEVENT_HANDLER"


def x_event_handler(event_identifier: str) -> Callable:
    """
    Decorator which registers an event handler of a node.
    :param event_identifier: String of the event which this decorator handles.
    :return: Decorated function.
    """

    def decorate(function: Callable) -> Callable:
        setattr(function, X_EVENT_HANDLER_FLAG, event_identifier)
        return function

    return decorate
