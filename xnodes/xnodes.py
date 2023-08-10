#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
xnodes: Exchange nodes framework
        Simplistic event framework which enables unrelated nodes to exchange information, alter each other states and
        provides the possibility to undo made changes.

Author: Ralph Neumann

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, see <https://www.gnu.org/licenses/>.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

MAXIMUM_ID_LENGTH = 25
ADDITIONAL_LOGGING_LENGTH = 128

EVENT_HANDLER = "EVENT_HANDLER"
EVENT_HANDLERS = "EVENT_HANDLERS"


@dataclass
class EventDescription:
    parameter_types: tuple
    log_level: int


class XEvent:
    """
    This is a descriptor class for events. It holds information about the event kind, the target, the sender and
    the event parameters.
    """

    def __init__(self, identifier: str, sender: str, target: str, parameters: tuple, parameter_types: tuple):
        self._identifier = identifier
        self._sender = sender
        self._parameters = parameters
        self._target = target

        if len(parameters) != len(parameter_types):
            raise ValueError(f"Event {identifier} has an invalid parameter count.")

        for i, (parameter, parameter_type) in enumerate(zip(parameters, parameter_types)):
            if not isinstance(parameter, parameter_type):
                raise ValueError(f"Parameter {i} of event {identifier} has an invalid type: Is {type(parameter)}, "
                                 f"should be {parameter_type}")

    @property
    def identifier(self) -> str:
        """
        Get the event property.
        :return: The event property.
        """
        return self._identifier

    @property
    def sender(self) -> str:
        """
        Get the sender property.
        :return: The sender property.
        """
        return self._sender

    @property
    def parameters(self) -> tuple:
        """
        Get the parameters property.
        :return: The parameters property.
        """
        return self._parameters

    @property
    def target(self) -> str:
        """
        Get the receiver property.
        :return: The receiver property.
        """
        return self._target


class EventHandleDictionary(dict):
    """
    Event handle dictionary for nodes.
    """

    def __setitem__(self, key, value):
        """
        Set an item to the dictionary.
        :param key: The key to set.
        :param value: The value to set.
        :return: None
        """
        if not hasattr(value, EVENT_HANDLER):
            super().__setitem__(key, value)
            return

        event = getattr(value, EVENT_HANDLER)
        assert event not in self[EVENT_HANDLERS], f"Duplicated event handler: {event}"
        self[EVENT_HANDLERS][event] = value


class EventHandleMeta(type):
    """
    Metaclass to have multiple methods with the same name but different signatures.
    """

    # pylint: disable = bad-mcs-classmethod-argument
    def __new__(mcs, cls_name, bases, cls_dict):
        """
        Create a new class instance.
        :param cls_name: Class name.
        :param bases: Base classes.
        :param cls_dict: Attributes.
        :return: The created class.
        """
        return type.__new__(mcs, cls_name, bases, dict(cls_dict))

    @classmethod
    def __prepare__(cls, _, bases):
        """
        Prepare the metaclass.
        :return: A MultiDict.
        """
        multi_dict = EventHandleDictionary()
        multi_dict[EVENT_HANDLERS] = {}

        for base in bases:
            if hasattr(base, EVENT_HANDLERS):
                multi_dict[EVENT_HANDLERS] |= getattr(base, EVENT_HANDLERS)

        return multi_dict


def xevent(event_identifier: str):
    """
    Decorator which registers an event or action handler in a node.
    :param event_identifier: String of the event or action which this decorator handles.
    :return: The decorated function.
    """

    def decorate(function):
        setattr(function, EVENT_HANDLER, event_identifier)
        return function

    return decorate


class XNode(object, metaclass=EventHandleMeta):
    """
    Main class for nodes.
    """

    def __init__(self, node_type: str):
        """
        Init of node.
        :param node_type: Category of the node.
        """
        self._type = node_type
        self._identifier = XNodeBus._register(self)
        self._undo_event = None

    @property
    def id(self) -> str:
        """
        Get the id property.
        :return: The id property.
        """
        return self._identifier

    @id.setter
    def id(self, new_id: str):
        """
        Set a new ID to the node.
        :param new_id: New ID to set.
        :return: None
        """
        XNodeBus.unregister(self)
        self._identifier = XNodeBus._register(self, new_id)

    def delete(self):
        """
        Delete the node and unregister it from the bus.
        :return: None
        """
        XNodeBus.unregister(self)

    @property
    def type(self) -> str:
        return self._type

    @property
    def subscribed_events(self) -> list[str]:
        return getattr(self, EVENT_HANDLERS)

    def publish(self, event_identifier: str, target: str, *parameters):
        """
        Publish a new event.
        :param event_identifier: The type of event to publish.
        :param target: The target this event is meant for.
        :param parameters: The parameters of the event.
        """
        XNodeBus.publish(event_identifier, self.id, target, *parameters)

    def broadcast(self, event_identifier: str, *parameters):
        """
        Publish a new event.
        :param event_identifier: The type of event to publish.
        :param parameters: The parameters of the event.
        """
        XNodeBus.broadcast(event_identifier, self.id, *parameters)

    def set_undo_event(self, event_identifier: str, *parameters):
        """
        Push an undo action to the application xnodes.
        :param event_identifier: The action tag of the undo action.
        :param parameters: The parameters of the undo action.
        :return: None
        """
        if self._undo_event is not None:
            raise ValueError(f"Undo event already set.")

        self._undo_event = XEvent(event_identifier, self.id, self.id, *parameters)

    def handle_event(self, event: XEvent) -> XEvent or None:
        """
        Handle the passed event.
        :return: None
        """
        event_handlers = getattr(self, EVENT_HANDLERS)
        self._undo_event = None

        if event.identifier not in event_handlers:
            raise ValueError(f"Event {event.identifier} not registered.")

        event_handlers[event.identifier](self, *event.parameters)
        return self._undo_event


def create_xnode(super_class: type, node_type: str) -> type:
    """
    Converts the passed super class to a node. Necessary for classes which have a custom metaclass.
    :param super_class: Super class to convert to a node.
    :return: The combined super class.
    """
    metaclass = type("CombinedMetaClass", (type(super_class), type(XNode)), {})

    class MergedSuperclass(XNode, super_class, metaclass=metaclass):
        """
        Merged super class.
        """

        def __init__(self, *super_class_args):
            super_class.__init__(self, *super_class_args)
            XNode.__init__(self, node_type)

    return MergedSuperclass


class XNodeBus:
    """
    Core of the application. Handles action delegations, event management and value requests.
    """

    _undo_stack: list[list[XEvent]] = []
    _redo_stack: list[list[XEvent]] = []
    _nodes: dict[str, XNode] = {}
    _event_descriptions: dict[str, EventDescription] = {}
    _subscriptions: dict[str, list[str]] = defaultdict(list)
    _indices: dict[str, int] = defaultdict(int)
    _undo_redo_change_handler: Callable or None = None

    @staticmethod
    def set_undo_redo_change_handler(undo_redo_change_handler: Callable):
        XNodeBus._undo_redo_change_handler = undo_redo_change_handler

    @staticmethod
    def add_event(identifier: str, parameter_types, log_level: int = logging.INFO):
        assert identifier not in XNodeBus._event_descriptions, "Event already added."

        XNodeBus._event_descriptions[identifier] = EventDescription(parameter_types, log_level)

    @staticmethod
    def _register(node: XNode, predefined_id: str or None = None) -> str:
        """
        Register a new node.
        :param node: The node to register.
        :param predefined_id: Optional predefined ID.
        :return: None
        """
        if predefined_id is not None:
            new_id = predefined_id
            assert predefined_id not in XNodeBus._nodes

        elif node.type not in XNodeBus._indices:
            new_id = node.type

        else:
            new_id = f"{node.type}_{XNodeBus._indices[node.type]}"
            while new_id in XNodeBus._nodes:
                XNodeBus._indices[node.type] += 1
                new_id = f"{node.type}_{XNodeBus._indices[node.type]}"

        XNodeBus._indices[node.type] += 1
        XNodeBus._nodes[new_id] = node

        for event in node.subscribed_events:
            assert event in XNodeBus._event_descriptions, f"Unknown event {event}"

            XNodeBus._subscriptions[event].append(new_id)

        return new_id

    @staticmethod
    def unregister(node: XNode):
        """
        Unregister the passed ActionHandler.
        :param node: The ActionHandler to unregister.
        :return: None
        """
        if node.id not in XNodeBus._nodes:
            return

        for subscriber_list in XNodeBus._subscriptions.values():
            if node.id in subscriber_list:
                subscriber_list.remove(node.id)

        del XNodeBus._nodes[node.id]

    @staticmethod
    def _log(event: XEvent):
        """
        Log a new event or action to the console.
        :return: None
        """
        maximum_event_identifier_length = max([len(event) for event in XNodeBus._event_descriptions.keys()])

        from_str = " " * (MAXIMUM_ID_LENGTH - len(event.sender)) + event.sender
        to_str = event.target + " " * (MAXIMUM_ID_LENGTH - len(event.target))
        event_or_action_str = event.identifier + " " * (maximum_event_identifier_length - len(event.identifier))

        base_string = f"LOF: {from_str} => {to_str}  {event_or_action_str.upper()}"

        additional = " | " + XNodeBus.format_parameters(*event.parameters)
        if len(additional) > ADDITIONAL_LOGGING_LENGTH:
            additional = additional[:ADDITIONAL_LOGGING_LENGTH] + "..."

        logging.log(XNodeBus._event_descriptions[event.identifier].log_level, f"{base_string} {additional}".rstrip())

    @staticmethod
    def publish(event_identifier: str, sender: str, target: str, *parameters):
        parameter_types = XNodeBus._event_descriptions[event_identifier].parameter_types
        XNodeBus._publish_new_events([XEvent(event_identifier, sender, target, parameters, parameter_types)])

    @staticmethod
    def broadcast(event_identifier: str, sender: str, *parameters):
        parameter_types = XNodeBus._event_descriptions[event_identifier].parameter_types
        XNodeBus._publish_new_events([XEvent(
            event_identifier, sender, handler_id, parameters, parameter_types
        ) for handler_id in XNodeBus._subscriptions[event_identifier]])

    @staticmethod
    def _publish_new_events(events: list[XEvent]):
        if undo_events := XNodeBus._publish_events(events):
            XNodeBus._redo_stack.clear()
            XNodeBus._append_undo_event(undo_events)

    @staticmethod
    def _publish_events(events: list[XEvent]) -> list[XEvent]:
        undo_events = [XNodeBus._publish_event(event) for event in events]
        return [undo_event for undo_event in undo_events if undo_event]

    @staticmethod
    def _publish_event(event: XEvent) -> XEvent or None:
        assert event.target in XNodeBus._nodes, f"Unknown element {event.target}"

        XNodeBus._log(event)

        return XNodeBus._nodes[event.target].handle_event(event)

    @staticmethod
    def undo_event():
        """
        Perform the last undo action and save the redo action to the redo stack.
        :return: None
        """
        if not XNodeBus._undo_stack:
            return

        if redo_events := XNodeBus._publish_events(XNodeBus._undo_stack.pop(-1)):
            XNodeBus._redo_stack.append(redo_events)

        if XNodeBus._undo_redo_change_handler is not None:
            XNodeBus._undo_redo_change_handler()

    @staticmethod
    def redo_event():
        """
        Perform the last redo action and save the undo action to the undo stack.
        :return: None
        """
        if not XNodeBus._redo_stack:
            return

        if undo_events := XNodeBus._publish_events(XNodeBus._redo_stack.pop(-1)):
            XNodeBus._append_undo_event(undo_events)

        if XNodeBus._undo_redo_change_handler is not None:
            XNodeBus._undo_redo_change_handler()

    @staticmethod
    def _append_undo_event(undo_event: list[XEvent]):
        """
        Append a new undo event.
        :param undo_event: Undo event to append.
        :return: None
        """
        XNodeBus._undo_stack.append(undo_event)
        if len(XNodeBus._undo_stack) == 1000:
            XNodeBus._undo_stack.pop(0)

        if XNodeBus._undo_redo_change_handler is not None:
            XNodeBus._undo_redo_change_handler()

    @staticmethod
    def clear_undo_redo_stacks():
        """
        Clear the undo and redo stacks.
        :return: None
        """
        XNodeBus._undo_stack.clear()
        XNodeBus._redo_stack.clear()

        if XNodeBus._undo_redo_change_handler is not None:
            XNodeBus._undo_redo_change_handler()

    @staticmethod
    def get_undo_count():
        """
        Get the amount of undo events.
        :return: The amount of undo events.
        """
        return len(XNodeBus._undo_stack)

    @staticmethod
    def get_redo_count():
        """
        Get the amount of redo events.
        :return: The amount of redo events.
        """
        return len(XNodeBus._redo_stack)

    @staticmethod
    def format_parameters(*parameters) -> str:
        """
        Format the given parameters.
        :param parameters: The parameters to format.
        :return: The formatted parameters.
        """
        part_strings = []

        for parameter in parameters:
            if isinstance(parameter, list):
                value = f"[{', '.join([str(value) for value in parameter])}]"
            else:
                value = str(parameter)
            part_strings.append(value)
        return " || ".join(part_strings)
