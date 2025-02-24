"""
xnodes: Exchange nodes framework
        Simplistic event framework which enables unrelated nodes to exchange information, alter each other states and
        provides the possibility to undo made changes.

Author: Ralph Neumann (@newmra)
"""

from typing import Callable

X_EVENT_LISTENER_FLAG = "X_EVENT_LISTENER"
APPEND_SENDER_ID_FLAG = "APPEND_SENDER_ID"


def x_event_listener(event_id: str, append_sender_id: bool = False) -> Callable:
    """
    Decorator which registers an event listener of a node.
    :param event_id: ID of the event which this decorator handles.
    :param append_sender_id: Flag if the sender ID shall be appended to the parameters.
    :return: Decorated function.
    """

    def decorate(function: Callable) -> Callable:
        setattr(function, X_EVENT_LISTENER_FLAG, event_id)
        if append_sender_id:
            setattr(function, APPEND_SENDER_ID_FLAG, True)
        return function

    return decorate
