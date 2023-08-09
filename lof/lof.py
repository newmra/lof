#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
lof: Live Object Framework
     Simplistic event framework which enables unrelated objects to share information, alter each other states and
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


class Event:
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
    Event handle dictionary for live objects.
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


def handle_event(event_identifier: str):
    """
    Decorator which registers an event or action handler in a live object.
    :param event_identifier: String of the event or action which this decorator handles.
    :return: The decorated function.
    """

    def decorate(function):
        setattr(function, EVENT_HANDLER, event_identifier)
        return function

    return decorate


class LiveObject(object, metaclass=EventHandleMeta):
    """
    Main class for live objects.
    """

    def __init__(self, category: str):
        """
        Init of live object.
        :param category: Category of the live object.
        """
        self._category = category
        self._id = LOF.register(self)
        self._undo_event = None

    def delete(self):
        """
        Delete the live object and unregister it from the application lof.
        :return: None
        """
        LOF.unregister(self)

    @property
    def category(self) -> str:
        return self._category

    @property
    def subscribed_events(self) -> list[str]:
        return getattr(self, EVENT_HANDLERS)

    @property
    def id(self) -> str:
        """
        Get the id property.
        :return: The id property.
        """
        return self._id

    @id.setter
    def id(self, new_id: str):
        """
        Set a new ID to the live object.
        :param new_id: New ID to set.
        :return: None
        """
        LOF.unregister(self)
        self._id = LOF.register(self, new_id)

    def publish(self, event_identifier: str, target: str, *parameters):
        """
        Publish a new event.
        :param event_identifier: The type of event to publish.
        :param target: The target this event is meant for.
        :param parameters: The parameters of the event.
        """
        LOF.publish(event_identifier, self.id, target, *parameters)

    def broadcast(self, event_identifier: str, *parameters):
        """
        Publish a new event.
        :param event_identifier: The type of event to publish.
        :param parameters: The parameters of the event.
        """
        LOF.broadcast(event_identifier, self.id, *parameters)

    def push_undo(self, event_identifier: str, *parameters):
        """
        Push an undo action to the application lof.
        :param event_identifier: The action tag of the undo action.
        :param parameters: The parameters of the undo action.
        :return: None
        """
        if self._undo_event is not None:
            raise ValueError(f"Undo event already set.")

        self._undo_event = Event(event_identifier, self.id, self.id, *parameters)

    def handle_event(self, event: Event) -> Event or None:
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


def make_live(super_class: type, category: str) -> type:
    """
    Converts the passed super class to a live object. Necessary for classes which have a custom metaclass.
    :param super_class: Super class to convert to a live object.
    :param category: Category of the live object.
    :return: The combined super class.
    """
    metaclass = type("CombinedMetaClass", (type(super_class), type(LiveObject)), {})

    class MergedSuperclass(LiveObject, super_class, metaclass=metaclass):
        """
        Merged super class.
        """

        def __init__(self, *super_class_args):
            super_class.__init__(self, *super_class_args)
            LiveObject.__init__(self, category)

    return MergedSuperclass


class LOF:
    """
    Core of the application. Handles action delegations, event management and value requests.
    """
    _undo_stack: list[list[Event]] = []
    _redo_stack: list[list[Event]] = []
    _live_objects: dict[str, LiveObject] = {}
    _event_descriptions: dict[str, EventDescription] = {}
    _subscriptions: dict[str, list[str]] = defaultdict(list)
    _is_running = False
    _indices: dict[str, int] = defaultdict(int)
    _undo_redo_change_handler: Callable or None = None

    @staticmethod
    def start():
        LOF._is_running = True

        for live_object_id, live_object in LOF._live_objects.items():
            for event in live_object.subscribed_events:
                assert event in LOF._event_descriptions, f"Unknown event {event}"

                LOF._subscriptions[event].append(live_object_id)

    @staticmethod
    def set_undo_redo_change_handler(undo_redo_change_handler: Callable):
        LOF._undo_redo_change_handler = undo_redo_change_handler

    @staticmethod
    def add_event(identifier: str, parameter_types, log_level: int = logging.INFO):
        assert identifier not in LOF._event_descriptions, "Event already added."
        assert not LOF._is_running, "Events cannot be added once LOF has started."

        LOF._event_descriptions[identifier] = EventDescription(parameter_types, log_level)

    @staticmethod
    def register(live_object: LiveObject, predefined_id: str or None = None) -> str:
        """
        Register a new live object.
        :param live_object: The live object to register.
        :param predefined_id: Optional predefined ID.
        :return: None
        """
        if predefined_id is not None:
            new_id = predefined_id
            assert predefined_id not in LOF._live_objects

        elif live_object.category not in LOF._indices:
            new_id = live_object.category

        else:
            new_id = f"{live_object.category}_{LOF._indices[live_object.category]}"
            while new_id in LOF._live_objects:
                LOF._indices[live_object.category] += 1
                new_id = f"{live_object.category}_{LOF._indices[live_object.category]}"

        LOF._indices[live_object.category] += 1
        LOF._live_objects[new_id] = live_object

        return new_id

    @staticmethod
    def unregister(live_object: LiveObject):
        """
        Unregister the passed ActionHandler.
        :param live_object: The ActionHandler to unregister.
        :return: None
        """
        if live_object.id not in LOF._live_objects:
            return

        for subscriber_list in LOF._subscriptions.values():
            if live_object.id in subscriber_list:
                subscriber_list.remove(live_object.id)

        del LOF._live_objects[live_object.id]

    @staticmethod
    def _log(event: Event):
        """
        Log a new event or action to the console.
        :return: None
        """
        maximum_event_identifier_length = max([len(event) for event in LOF._event_descriptions.keys()])

        from_str = " " * (MAXIMUM_ID_LENGTH - len(event.sender)) + event.sender
        to_str = event.target + " " * (MAXIMUM_ID_LENGTH - len(event.target))
        event_or_action_str = event.identifier + " " * (maximum_event_identifier_length - len(event.identifier))

        base_string = f"LOF: {from_str} => {to_str}  {event_or_action_str.upper()}"

        additional = " | " + LOF.format_parameters(*event.parameters)
        if len(additional) > ADDITIONAL_LOGGING_LENGTH:
            additional = additional[:ADDITIONAL_LOGGING_LENGTH] + "..."

        logging.log(LOF._event_descriptions[event.identifier].log_level, f"{base_string} {additional}".rstrip())

    @staticmethod
    def publish(event_identifier: str, sender: str, target: str, *parameters):
        parameter_types = LOF._event_descriptions[event_identifier].parameter_types
        LOF._publish_new_events([Event(event_identifier, sender, target, parameters, parameter_types)])

    @staticmethod
    def broadcast(event_identifier: str, sender: str, *parameters):
        parameter_types = LOF._event_descriptions[event_identifier].parameter_types
        LOF._publish_new_events([Event(
            event_identifier, sender, handler_id, parameters, parameter_types
        ) for handler_id in LOF._subscriptions[event_identifier]])

    @staticmethod
    def _publish_new_events(events: list[Event]):
        assert LOF._is_running, "LOF not yet started"

        if undo_events := LOF._publish_events(events):
            LOF._redo_stack.clear()
            LOF._append_undo_event(undo_events)

    @staticmethod
    def _publish_events(events: list[Event]) -> list[Event]:
        undo_events = [LOF._publish_event(event) for event in events]
        return [undo_event for undo_event in undo_events if undo_event]

    @staticmethod
    def _publish_event(event: Event) -> Event or None:
        assert event.target in LOF._live_objects, f"Unknown element {event.target}"

        LOF._log(event)

        return LOF._live_objects[event.target].handle_event(event)

    @staticmethod
    def undo_event():
        """
        Perform the last undo action and save the redo action to the redo stack.
        :return: None
        """
        assert LOF._is_running, "LOF not started yet"

        if not LOF._undo_stack:
            return

        if redo_events := LOF._publish_events(LOF._undo_stack.pop(-1)):
            LOF._redo_stack.append(redo_events)

        if LOF._undo_redo_change_handler is not None:
            LOF._undo_redo_change_handler()

    @staticmethod
    def redo_event():
        """
        Perform the last redo action and save the undo action to the undo stack.
        :return: None
        """
        assert LOF._is_running, "LOF not started yet"

        if not LOF._redo_stack:
            return

        if undo_events := LOF._publish_events(LOF._redo_stack.pop(-1)):
            LOF._append_undo_event(undo_events)

        if LOF._undo_redo_change_handler is not None:
            LOF._undo_redo_change_handler()

    @staticmethod
    def _append_undo_event(undo_event: list[Event]):
        """
        Append a new undo event.
        :param undo_event: Undo event to append.
        :return: None
        """
        LOF._undo_stack.append(undo_event)
        if len(LOF._undo_stack) == 1000:
            LOF._undo_stack.pop(0)

        if LOF._undo_redo_change_handler is not None:
            LOF._undo_redo_change_handler()

    @staticmethod
    def clear_undo_redo_stacks():
        """
        Clear the undo and redo stacks.
        :return: None
        """
        LOF._undo_stack.clear()
        LOF._redo_stack.clear()

        if LOF._undo_redo_change_handler is not None:
            LOF._undo_redo_change_handler()

    @staticmethod
    def get_undo_count():
        """
        Get the amount of undo events.
        :return: The amount of undo events.
        """
        return len(LOF._undo_stack)

    @staticmethod
    def get_redo_count():
        """
        Get the amount of redo events.
        :return: The amount of redo events.
        """
        return len(LOF._redo_stack)

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
