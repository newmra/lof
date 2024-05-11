"""
xnodes: Exchange nodes framework
        Simplistic event framework which enables unrelated nodes to exchange information, alter each other states and
        provides the possibility to undo made changes.

Author: Ralph Neumann (@newmra)

This framework is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
License as published by the Free Software Foundation, see <https://www.gnu.org/licenses>.
"""

import inspect
import logging
from collections import defaultdict
from dataclasses import dataclass
from types import GeneratorType
from typing import Callable, Optional, Dict, List, Set, Tuple, Union, Any, Iterable

from xnodes.x_core_configuration import XCoreConfiguration
from xnodes.x_event_handler import X_EVENT_HANDLER_FLAG
from xnodes.x_node_exception import XNodeException

LOGGER = logging.getLogger(__name__)

MINIMUM_IDENTIFIER_MAXIMUM_LOGGING_LENGTH = 10

# pylint: disable = global-statement
# Globals are only used for private members.

# pylint: disable = invalid-name
# Global constants are not used as classes.

# First possible type: Just the name of the parameter.
EVENT_PARAMETER_TYPE_1 = str

# Second possible type: Name of the parameter and the type of the parameter.
EVENT_PARAMETER_TYPE_2 = Tuple[str, type]

# Third possible type: Name of the parameter, type of the parameter and description of the parameter.
EVENT_PARAMETER_TYPE_3 = Tuple[str, type, str]

# Fourth possible type: Name of the parameter and description of the parameter.
EVENT_PARAMETER_TYPE_4 = Tuple[str, str]

EVENT_PARAMETER_TYPE = Union[EVENT_PARAMETER_TYPE_1, EVENT_PARAMETER_TYPE_2, EVENT_PARAMETER_TYPE_3,
                             EVENT_PARAMETER_TYPE_4]

# pylint: enable = invalid-name


@dataclass
class XEventDescription:
    """
    Description of an event which contains the parameters and the log level.
    """
    parameters: Set[Union[Tuple[str], EVENT_PARAMETER_TYPE_2, EVENT_PARAMETER_TYPE_3, EVENT_PARAMETER_TYPE_4]]
    log_level: int = logging.INFO


@dataclass
class XEvent:
    """
    Complete event which is sent from one node to another node.
    """
    identifier: str
    event_description: XEventDescription
    sender_identifier: str
    receiver_identifier: str
    parameters: Dict[str, object]


X_CORE_NODE_IDENTIFIER = "X_CORE"

X_CORE_START = "X_CORE_START"
X_UNDO_EVENT = "X_UNDO_EVENT"
X_REDO_EVENT = "X_REDO_EVENT"
X_MAP_UNDO_REDO_COUNTERS = "X_MAP_UNDO_REDO_COUNTERS"
X_CLEAR_UNDO_REDO_EVENTS = "X_CLEAR_UNDO_REDO_EVENTS"

_UNDO_STACK: List[List[XEvent]] = []
_REDO_STACK: List[List[XEvent]] = []

_NODE_IDENTIFIERS = {X_CORE_NODE_IDENTIFIER}

_EVENT_SUBSCRIPTIONS: Dict[str, Set[str]] = defaultdict(set)
_EVENT_SUBSCRIPTIONS[X_UNDO_EVENT].add(X_CORE_NODE_IDENTIFIER)
_EVENT_SUBSCRIPTIONS[X_REDO_EVENT].add(X_CORE_NODE_IDENTIFIER)
_EVENT_SUBSCRIPTIONS[X_CLEAR_UNDO_REDO_EVENTS].add(X_CORE_NODE_IDENTIFIER)

# pylint: disable = unnecessary-lambda
# Functions are declared later, so lambda is necessary.
_EVENT_HANDLERS: Dict[Tuple[str, str], Callable] = {
    (X_UNDO_EVENT, X_CORE_NODE_IDENTIFIER): lambda: _undo_events(),
    (X_REDO_EVENT, X_CORE_NODE_IDENTIFIER): lambda: _redo_events(),
    (X_CLEAR_UNDO_REDO_EVENTS, X_CORE_NODE_IDENTIFIER): lambda: _clear_undo_redo_stacks()
}
# pylint: enable = unnecessary-lambda

_EVENT_DESCRIPTIONS: Dict[str, XEventDescription] = {
    X_CORE_START: XEventDescription(set(), logging.INFO),
    X_UNDO_EVENT: XEventDescription(set(), logging.INFO),
    X_REDO_EVENT: XEventDescription(set(), logging.INFO),

    # (Args: Undo counter, redo counter)
    X_MAP_UNDO_REDO_COUNTERS: XEventDescription({("undo_counter", int), ("redo_counter", int)}, logging.INFO),
    X_CLEAR_UNDO_REDO_EVENTS: XEventDescription(set(), logging.INFO)
}

# Event length is the length of the biggest event identifier name.
_EVENT_LENGTH = 24
_IS_EVENT_IN_PROGRESS = False
_CONFIGURATION = XCoreConfiguration()


def _get_parameter_names(event_description: XEventDescription) -> Set[str]:
    """
    Get all parameter names of the given event description.
    :param event_description: Event description to get the parameter names of.
    :return: All event parameter names of the given event description.
    """
    event_parameters = set()
    for parameter in event_description.parameters:
        event_parameters.add(parameter[0])
    return event_parameters


def _build_event(event_identifier: str, sender_identifier: str, receiver_identifier: str,
                 parameters: Dict[str, object]) -> XEvent:
    """
    Build an event with the given information.
    :param event_identifier: Identifier of the event.
    :param sender_identifier: Identifier of the sender node.
    :param receiver_identifier: Identifier of the receiver node.
    :param parameters: Parameters of the event.
    :return: Constructed event.
    """
    if event_identifier not in _EVENT_DESCRIPTIONS:
        raise XNodeException(f"Attempted to create an unknown event '{event_identifier}'.")

    event_description = _EVENT_DESCRIPTIONS[event_identifier]

    event_parameters = _get_parameter_names(event_description)
    if event_parameters != set(parameters):
        event_parameters_string = ", ".join([f"'{parameter}'" for parameter in event_parameters])
        provided_parameters_string = ", ".join([f"'{parameter}'" for parameter in parameters])

        raise XNodeException(
            f"Event '{event_identifier}' cannot be constructed, event requires: [{event_parameters_string}], "
            f"provided are: [{provided_parameters_string}].")

    return XEvent(event_identifier, event_description, sender_identifier, receiver_identifier, parameters)


def register_event(event_identifier: str, parameters: Set[EVENT_PARAMETER_TYPE], log_level: int = logging.INFO) -> None:
    """
    Register a new event in the core, event identifier cannot be registered yet. Once an event is registered it cannot
    be removed.
    :param event_identifier: Identifier of the event.
    :param parameters: Parameters of the event.
    :param log_level: Log level of the event.
    :return: None
    """
    global _EVENT_LENGTH

    if event_identifier in _EVENT_DESCRIPTIONS:
        raise XNodeException(f"Attempted to register event '{event_identifier}' twice.")

    if not isinstance(log_level, int):
        raise XNodeException(
            f"Attempted to register event '{event_identifier}', but the log_level is not of type 'int'.")

    parameter_names = set()

    def check_parameter(parameter_name: str):
        if parameter_name in parameter_names:
            raise XNodeException(
                f"Attempted to register event '{event_identifier}', but parameter {parameter_name} is configured twice."
            )
        parameter_names.add(parameter_name)

    corrected_parameters = set()
    for i, parameter in enumerate(parameters):
        invalid_parameter_exception = XNodeException(
            f"Attempted to register event '{event_identifier}', but parameter {i} has an invalid type, has to be "
            f"of type {str(EVENT_PARAMETER_TYPE)}.")

        if isinstance(parameter, str):
            current_parameter = (parameter, )
        elif isinstance(parameter, Iterable):
            current_parameter = tuple(parameter)
        else:
            raise invalid_parameter_exception

        corrected_parameters.add(current_parameter)

        if not 1 <= len(current_parameter) <= 3:
            raise invalid_parameter_exception

        if not isinstance(current_parameter[0], str):
            raise invalid_parameter_exception

        check_parameter(current_parameter[0])

        if len(current_parameter) == 2 and not isinstance(current_parameter[1], (str, type)):
            raise invalid_parameter_exception

        if len(current_parameter) == 3 and not (isinstance(current_parameter[1], type)
                                                and isinstance(current_parameter[2], str)):
            raise invalid_parameter_exception

    _EVENT_DESCRIPTIONS[event_identifier] = XEventDescription(corrected_parameters, log_level)
    _EVENT_LENGTH = max(len(event_identifier) for event_identifier in _EVENT_DESCRIPTIONS)


def register_node(node_identifier: str, node: object) -> None:
    """
    Register a new node, node identifier cannot be registered yet.
    :param node_identifier: Identifier of the node.
    :param node: Node to register.
    :return: None
    """
    if node_identifier in _NODE_IDENTIFIERS:
        raise XNodeException(
            f"Attempted to register node '{node_identifier}', but a node with that identifier is already registered.")

    for _, node_method in inspect.getmembers(node, predicate=inspect.ismethod):
        if not hasattr(node_method, X_EVENT_HANDLER_FLAG):
            continue

        event_identifier = getattr(node_method, X_EVENT_HANDLER_FLAG)
        if (event_description := _EVENT_DESCRIPTIONS.get(event_identifier)) is None:
            raise XNodeException(
                f"Node '{node_identifier}' handles event '{event_identifier}', but the event is not registered.")

        node_method_arguments = inspect.getfullargspec(node_method).args

        # Remove the 'self' reference.
        if "self" in node_method_arguments:
            node_method_arguments.remove("self")

        event_parameters = _get_parameter_names(event_description)
        if event_parameters != set(node_method_arguments):
            event_parameters_string = ", ".join([f"'{parameter}'" for parameter in event_parameters])
            handler_parameters_string = ", ".join([f"'{parameter}'" for parameter in node_method_arguments])

            raise XNodeException(
                f"Node '{node_identifier}' handles event '{event_identifier}', but the parameters do not match. "
                f"Event requires: [{event_parameters_string}], handler provides: [{handler_parameters_string}].")

        _EVENT_SUBSCRIPTIONS[event_identifier].add(node_identifier)
        _EVENT_HANDLERS[(event_identifier, node_identifier)] = node_method

    _NODE_IDENTIFIERS.add(node_identifier)


def unregister_node(node_identifier: str) -> None:
    """
    Unregister the node with the given identifier. The node will no longer receive events or is allowed to publish
    and broadcast events.
    :param node_identifier: Identifier of the node to unregister.
    :return: None
    """
    if node_identifier not in _NODE_IDENTIFIERS:
        raise XNodeException(
            f"Attempted to unregister node '{node_identifier}', but no node with that identifier is registered.")

    for event_identifier, subscribers in _EVENT_SUBSCRIPTIONS.items():
        if node_identifier not in subscribers:
            continue

        subscribers.remove(node_identifier)
        _EVENT_HANDLERS.pop((event_identifier, node_identifier))

    _NODE_IDENTIFIERS.remove(node_identifier)


def start(x_core_configuration: Optional[XCoreConfiguration] = None) -> None:
    """
    Start the core and send the X_CORE_START event to all nodes which subscribed to it.
    :param x_core_configuration: Core configuration.
    :return: None
    """
    global _CONFIGURATION

    if isinstance(x_core_configuration, XCoreConfiguration):
        _CONFIGURATION = x_core_configuration

    if _CONFIGURATION.identifier_maximum_logging_length < MINIMUM_IDENTIFIER_MAXIMUM_LOGGING_LENGTH:
        raise XNodeException(f"Invalid configuration: 'identifier_maximum_logging_length' has to be "
                             f"greater or equal to {MINIMUM_IDENTIFIER_MAXIMUM_LOGGING_LENGTH}.")

    LOGGER.setLevel(_CONFIGURATION.log_level)

    broadcast(X_CORE_START, X_CORE_NODE_IDENTIFIER, {})


def publish(event_identifier: str, sender_identifier: str, receiver_identifier: str, parameters: Dict[str,
                                                                                                      object]) -> None:
    """
    Publish a directed event to another node. The event has to be registered and the receiver node identifier has to be
    registered. Additionally, the parameters have to match the parameters of the registered event.
    :param event_identifier: Identifier of the event to publish.
    :param sender_identifier: Identifier of the node which sent the event.
    :param receiver_identifier: Identifier of the node which shall receive the event.
    :param parameters: Parameters of the event. Have to match exactly the parameters of the event.
    :return: None
    """
    base_error_message = (f"Node '{sender_identifier}' attempted to publish event '{event_identifier}' to node "
                          f"'{receiver_identifier}'")

    if event_identifier not in _EVENT_DESCRIPTIONS:
        raise XNodeException(f"{base_error_message}, but the event is not registered.")

    if sender_identifier not in _NODE_IDENTIFIERS:
        raise XNodeException(f"{base_error_message}, but the sender node is not registered.")

    if receiver_identifier not in _NODE_IDENTIFIERS:
        raise XNodeException(f"{base_error_message}, but the receiver node is not registered.")

    if (event_identifier, receiver_identifier) not in _EVENT_HANDLERS:
        raise XNodeException(f"{base_error_message}, but receiver '{receiver_identifier}' is not subscribed to event "
                             f"'{event_identifier}'.")

    _publish_events([_build_event(event_identifier, sender_identifier, receiver_identifier, parameters)], is_undo=False)


def broadcast(event_identifier: str, sender_identifier: str, parameters: Dict[str, object]) -> None:
    """
    Broadcast an event to all nodes which are subscribed to the event. The event has to be registered and the
    receiver node identifier has to be registered. Additionally, the parameters have to match the parameters of the
    registered event.
    :param event_identifier: Identifier of the event to broadcast.
    :param sender_identifier: Identifier of the node which sent the event.
    :param parameters: Parameters of the event. Have to match exactly the parameters of the event.
    :return: None
    """
    base_error_message = f"Node '{sender_identifier}' attempted to broadcast event '{event_identifier}'"

    if event_identifier not in _EVENT_DESCRIPTIONS:
        raise XNodeException(f"{base_error_message}, but the event is not registered.")

    if sender_identifier not in _NODE_IDENTIFIERS:
        raise XNodeException(f"{base_error_message}, but the sender node is not registered.")

    events = [
        _build_event(event_identifier, sender_identifier, handler_id, parameters)
        for handler_id in _EVENT_SUBSCRIPTIONS[event_identifier]
    ]

    if events:
        _publish_events(events, is_undo=False)
    else:
        LOGGER.warning(f"*** {base_error_message}, but it echoed in the void... ***")


def add_undo_events(undo_events: List[XEvent]) -> None:
    """
    Add new undo events to the stack and clear the redo stack. This function can be used to add undo events
    to changed which were not induced by events. Has to be used with care, because it can alter the event flow.
    :param undo_events: Undo events to add.
    :return: None
    """
    _REDO_STACK.clear()
    _append_undo_events(undo_events)

    _publish_undo_redo_counters()


def _log(event: XEvent) -> None:
    """
    Log an event to the console.
    :param event: Event to log.
    :return: None
    """
    base_string = _create_base_logging_string(event)
    parameters_logging_string = _create_parameters_logging_string(event)

    LOGGER.log(event.event_description.log_level, f"{base_string}{parameters_logging_string}".rstrip())


def _create_base_logging_string(event: XEvent) -> str:
    """
    Create the base logging string for the given event.
    :param event: Event to create the base logging string for.
    :return: Base logging string of the passed event.
    """
    from_str = (" " * (_CONFIGURATION.identifier_maximum_logging_length - len(event.sender_identifier)) +
                event.sender_identifier)
    to_str = event.receiver_identifier + " " * (_CONFIGURATION.identifier_maximum_logging_length -
                                                len(event.receiver_identifier))

    remaining_dashes = _EVENT_LENGTH - len(event.identifier)

    event_str = "--"
    event_str += "-" * (remaining_dashes // 2)
    event_str += f" {event.identifier} "
    event_str += "-" * (remaining_dashes - remaining_dashes // 2)
    event_str += "->"

    return f"{from_str} {event_str} {to_str}"


def _create_parameters_logging_string(event: XEvent) -> str:
    """
    Create the parameters logging string for the given event.
    :param event: Event to create the parameters logging string for.
    :return: Parameters logging string of the passed event.
    """
    if not _CONFIGURATION.log_event_parameters or not event.event_description.parameters:
        return ""

    part_strings = []

    for parameter in event.event_description.parameters:
        type_info = ""
        if _CONFIGURATION.log_parameter_type_info and len(parameter) >= 2 and isinstance(parameter[1], type):
            type_info = f" ({parameter[1].__name__} / {type(event.parameters[parameter[0]]).__name__})"

        part_strings.append(f"{parameter[0]}{type_info}: '{event.parameters[parameter[0]]}'")

    return " | " + " | ".join(part_strings)


class EventPublishingContext:
    """
    Context for publishing events.
    """

    def __init__(self, events: List[XEvent]):
        """
        Init of EventPublishingContext.
        :param events: Events which are published.
        """
        global _IS_EVENT_IN_PROGRESS

        self._is_first_event_in_batch = not _IS_EVENT_IN_PROGRESS
        _IS_EVENT_IN_PROGRESS = True

        self._events = events

    def __enter__(self):
        """
        Enter the context. If no event is currently published, an empty line is logged to separate the event stack from
        the remaining log.
        :return: Self.
        """
        if not self._is_first_event_in_batch:
            return self

        for event in self._events:
            if event.event_description.log_level >= _CONFIGURATION.log_level:
                LOGGER.log(event.event_description.log_level, "")
                break

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the context.
        :param exc_type: Exception type.
        :param exc_val: Exception value.
        :param exc_tb: Exception traceback.
        :return: None
        """
        global _IS_EVENT_IN_PROGRESS
        if self._is_first_event_in_batch:
            _IS_EVENT_IN_PROGRESS = False


def _publish_events(events: List[XEvent], is_undo: bool) -> None:
    """
    Publish a list of events and return the undo events.
    :param events: Events to publish.
    :param is_undo: Flag if the events are undo events.
    :return: Undo events.
    """
    with EventPublishingContext(events):
        undo_events = []

        for event in events:
            _log(event)

            undo_event_generator = _execute_event(event)
            undo_events.extend(_extract_undo_events(undo_event_generator, event.receiver_identifier))

        if undo_events:
            if is_undo:
                _REDO_STACK.append(list(reversed(undo_events)))
            else:
                _append_undo_events(list(reversed(undo_events)))

        if undo_events or is_undo:
            _publish_undo_redo_counters()


def _execute_event(event: XEvent) -> GeneratorType:
    """
    Execute the given event and call the receiver nodes event handler.
    :param event: Event to execute.
    :return: An undo event generator which is provided by the event handler of the receiver node.
    """
    if (event.identifier, event.receiver_identifier) not in _EVENT_HANDLERS:
        raise XNodeException(f"Attempted to send event with identifier '{event.identifier}' to node "
                             f"'{event.receiver_identifier}', but the node is not subscribed to that event.")

    parameter_description = event.event_description.parameters
    return _EVENT_HANDLERS[(event.identifier,
                            event.receiver_identifier)](**{
                                parameter_key[0]: event.parameters[parameter_key[0]]
                                for parameter_key in parameter_description
                            })


def _extract_undo_events(undo_event_iterable: Any, receiver_identifier: str) -> List[XEvent]:
    """
    Extract the undo events from the given undo event iterable.
    :param undo_event_iterable: Undo event iterable to extract the undo events from.
    :param receiver_identifier: Identifier of the receiver node.
    :return: Extracted undo events.
    """
    if not isinstance(undo_event_iterable, Iterable):
        return []

    undo_events = []
    for undo_event in undo_event_iterable:
        if not isinstance(undo_event, tuple) or len(undo_event) != 2:
            raise XNodeException("Undo event has to be a tuple consisting of the event and the parameters.")

        undo_event_identifier, undo_event_parameters = undo_event

        if not isinstance(undo_event_parameters, dict):
            raise XNodeException(f"Undo event parameters has an invalid type, should be dict, is: "
                                 f"'{type(undo_event_parameters).__name__}'.")

        undo_events.append(
            _build_event(undo_event_identifier, receiver_identifier, receiver_identifier, undo_event_parameters))

    return undo_events


def _undo_events() -> None:
    """
    Publish the last undo events and save the redo events to the redo stack.
    :return: None
    """
    if not _UNDO_STACK:
        return

    _publish_events(_UNDO_STACK.pop(-1), is_undo=True)


def _redo_events() -> None:
    """
    Perform the last redo events and save the undo events to the undo stack.
    :return: None
    """
    if not _REDO_STACK:
        return

    _publish_events(_REDO_STACK.pop(-1), is_undo=False)


def _append_undo_events(undo_events: List[XEvent]) -> None:
    """
    Append new undo events.
    :param undo_events: Undo events to append.
    :return: None
    """
    _UNDO_STACK.append(undo_events)
    if _CONFIGURATION.maximum_undo_events < 0:
        return

    if len(_UNDO_STACK) > _CONFIGURATION.maximum_undo_events:
        _UNDO_STACK.pop(0)


def _clear_undo_redo_stacks() -> None:
    """
    Clear the undo and redo stacks.
    :return: None
    """
    _UNDO_STACK.clear()
    _REDO_STACK.clear()

    _publish_undo_redo_counters()


def _publish_undo_redo_counters() -> None:
    """
    Publish the undo and redo counters.
    :return: None
    """
    broadcast(X_MAP_UNDO_REDO_COUNTERS, X_CORE_NODE_IDENTIFIER, {
        "undo_counter": len(_UNDO_STACK),
        "redo_counter": len(_REDO_STACK)
    })
