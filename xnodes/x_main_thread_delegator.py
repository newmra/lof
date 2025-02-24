"""
xnodes: Exchange nodes framework
        Simplistic event framework which enables unrelated nodes to exchange information, alter each other states and
        provides the possibility to undo made changes.

Author: Ralph Neumann (@newmra)
"""

from typing import List

from xnodes import XEvent
from xnodes.x_core import publish_events_in_main_thread, IMainThreadDelegator


class XMainThreadDelegator(IMainThreadDelegator):
    """
    Interface of classes which can delegate events to the main thread.
    """

    def _delegate_events_to_main_thread(self, events: List[XEvent], is_undo: bool) -> None:
        """
        Delegate a list of events to the main thread.
        :param events: Events to delegate.
        :param is_undo: Flag if the events are undo events.
        :return:
        """
        publish_events_in_main_thread(events, is_undo)
