"""
xnodes: Exchange nodes framework
        Simplistic event framework which enables unrelated nodes to exchange information, alter each other states and
        provides the possibility to undo made changes.

Author: Ralph Neumann (@newmra)

This framework is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
License as published by the Free Software Foundation, see <https://www.gnu.org/licenses>.
"""

import logging
import re
from unittest.mock import MagicMock, ANY

import pytest

from xnodes import x_core, x_event_handler, X_CORE_START, X_CORE_NODE_IDENTIFIER
from xnodes.x_core import XEvent, XEventDescription, EventPublishingContext
from xnodes.x_core_configuration import XCoreConfiguration
from xnodes.x_node_exception import XNodeException

NODE_IDENTIFIER_1 = "NODE_IDENTIFIER_1"
NODE_IDENTIFIER_2 = "NODE_IDENTIFIER_2"

EVENT_IDENTIFIER_1 = "EVENT_IDENTIFIER_1"
EVENT_IDENTIFIER_2 = "EVENT_IDENTIFIER_2"
EVENT_DESCRIPTION = "EVENT_DESCRIPTION"

EVENT_PARAMETER_NAME_1 = "parameter_1"
EVENT_PARAMETER_NAME_2 = "parameter_2"


# noinspection PyProtectedMember
def _reset_x_core() -> None:
    """
    Reset the x_core variables and bring it into its initial state.
    :return: None
    """
    x_core._UNDO_STACK.clear()
    x_core._REDO_STACK.clear()

    x_core._NODE_IDENTIFIERS.clear()
    x_core._NODE_IDENTIFIERS.add(x_core.X_CORE_NODE_IDENTIFIER)

    x_core._EVENT_SUBSCRIPTIONS.clear()
    x_core._EVENT_SUBSCRIPTIONS[x_core.X_UNDO_EVENT].add(x_core.X_CORE_NODE_IDENTIFIER)
    x_core._EVENT_SUBSCRIPTIONS[x_core.X_REDO_EVENT].add(x_core.X_CORE_NODE_IDENTIFIER)
    x_core._EVENT_SUBSCRIPTIONS[x_core.X_CLEAR_UNDO_REDO_EVENTS].add(x_core.X_CORE_NODE_IDENTIFIER)

    x_core._EVENT_HANDLERS.clear()
    x_core._EVENT_HANDLERS.update({
        (x_core.X_UNDO_EVENT, x_core.X_CORE_NODE_IDENTIFIER): lambda: x_core._undo_events(),
        (x_core.X_REDO_EVENT, x_core.X_CORE_NODE_IDENTIFIER): lambda: x_core._redo_events(),
        (x_core.X_CLEAR_UNDO_REDO_EVENTS, x_core.X_CORE_NODE_IDENTIFIER): lambda: x_core._clear_undo_redo_stacks()
    })

    x_core._EVENT_DESCRIPTIONS.clear()
    x_core._EVENT_DESCRIPTIONS.update({
        x_core.X_CORE_START: x_core.XEventDescription(
            set(), x_core.logging.INFO
        ),
        x_core.X_UNDO_EVENT: x_core.XEventDescription(
            set(), x_core.logging.INFO
        ),
        x_core.X_REDO_EVENT: x_core.XEventDescription(
            set(), x_core.logging.INFO
        ),

        # (Args: Undo counter, redo counter)
        x_core.X_MAP_UNDO_REDO_COUNTERS: x_core.XEventDescription(
            {
                ("undo_counter", int),
                ("redo_counter", int)
            }, x_core.logging.INFO
        ),
        x_core.X_CLEAR_UNDO_REDO_EVENTS: x_core.XEventDescription(
            set(), x_core.logging.INFO
        )
    })

    x_core._EVENT_LENGTH = 24
    x_core._IS_EVENT_IN_PROGRESS = False
    x_core._CONFIGURATION = XCoreConfiguration()


def test_register_event_raise_event_registered_twice() -> None:
    """
    Register an event and check that an exception is raised if the same event is registered twice.
    :return: None
    """
    _reset_x_core()

    x_core.register_event(EVENT_IDENTIFIER_1, {EVENT_PARAMETER_NAME_1})

    with pytest.raises(XNodeException, match=re.escape(f"Attempted to register event '{EVENT_IDENTIFIER_1}' twice.")):
        x_core.register_event(EVENT_IDENTIFIER_1, {EVENT_PARAMETER_NAME_1})


def test_register_event_raise_invalid_log_level() -> None:
    """
    Register an event and check that an exception is raised if the log level has an invalid type.
    :return: None
    """
    _reset_x_core()

    with pytest.raises(XNodeException, match=re.escape(
            f"Attempted to register event '{EVENT_IDENTIFIER_1}', but the log_level is not of type 'int'.")):
        # noinspection PyTypeChecker
        x_core.register_event(EVENT_IDENTIFIER_1, [EVENT_PARAMETER_NAME_1], log_level="DEBUG")


def test_register_event_raise_parameters_not_iterable() -> None:
    """
    Register an event and check that an exception is raised if the parameters are not iterable.
    :return: None
    """
    _reset_x_core()

    with pytest.raises(TypeError, match=re.escape(f"'int' object is not iterable")):
        # noinspection PyTypeChecker
        x_core.register_event(EVENT_IDENTIFIER_1, 42)


@pytest.mark.parametrize("parameter", [
    42,
    tuple(),
    (1, 2, 3, 4),
    (42,),
    ("", 42),
    ("", 42, ""),
    ("", int, 42)
], ids=[
    "Not string or tuple",
    "Tuple has less than one element",
    "Tuple has more than 3 elements",
    "First element of tuple is not a string",
    "Second element of tuple is not a string or a type",
    "Tuple with three elements, but second element is not a type",
    "Tuple with three elements, but third element is not a string"
])
def test_register_event_raise_invalid_parameter(parameter) -> None:
    """
    Register an event and check that invalid parameters are correctly recognized.
    :param parameter: Parameter to test.
    :return: None
    """
    _reset_x_core()

    with pytest.raises(XNodeException, match=re.escape(
            f"Attempted to register event '{EVENT_IDENTIFIER_1}', but parameter 0 has an invalid type, has to be "
            f"of type {str(x_core.EVENT_PARAMETER_TYPE)}.")):
        x_core.register_event(EVENT_IDENTIFIER_1, {parameter})


@pytest.mark.parametrize("parameter", [
    EVENT_IDENTIFIER_1,
    (EVENT_IDENTIFIER_1, EVENT_DESCRIPTION),
    (EVENT_IDENTIFIER_1, int),
    (EVENT_IDENTIFIER_1, int, EVENT_DESCRIPTION)
], ids=[
    "Only parameter name",
    "Parameter name with description",
    "Parameter name with type",
    "Parameter name with type and description"
])
def test_register_event_valid_parameter(parameter) -> None:
    """
    Register an event and check that valid parameters can be set without a raised exception.
    :param parameter: Parameter to test.
    :return: None
    """
    _reset_x_core()

    x_core.register_event(EVENT_IDENTIFIER_1, {parameter})


def test_register_event_raise_duplicated_parameter() -> None:
    """
    Register an event and check that an exception is raised if a parameter is added twice.
    :return: None
    """
    _reset_x_core()

    with pytest.raises(XNodeException, match=re.escape(
            f"Attempted to register event '{EVENT_IDENTIFIER_1}', but parameter {EVENT_PARAMETER_NAME_1} is configured "
            f"twice.")):
        x_core.register_event(EVENT_IDENTIFIER_1, {EVENT_PARAMETER_NAME_1, (EVENT_PARAMETER_NAME_1, str)})


def test_register_node_raise_node_registered_twice() -> None:
    _reset_x_core()

    class EmptyNode:
        def empty_method(self) -> None:
            pass

    node = EmptyNode()
    x_core.register_node(NODE_IDENTIFIER_1, node)

    with pytest.raises(XNodeException, match=re.escape(
            f"Attempted to register node '{NODE_IDENTIFIER_1}', but a node with that identifier is already registered.")):
        x_core.register_node(NODE_IDENTIFIER_1, node)


def test_register_node_raise_invalid_event() -> None:
    _reset_x_core()

    class Node:
        @x_event_handler(EVENT_IDENTIFIER_1)
        def handler_invalid(self) -> None:
            pass

    with pytest.raises(XNodeException, match=re.escape(
            f"Node '{NODE_IDENTIFIER_1}' handles event '{EVENT_IDENTIFIER_1}', but the event is not registered.")):
        x_core.register_node(NODE_IDENTIFIER_1, Node())


def test_register_node_raise_invalid_event_parameters() -> None:
    _reset_x_core()

    x_core.register_event(EVENT_IDENTIFIER_1, {EVENT_PARAMETER_NAME_1})

    class Node:
        @x_event_handler(EVENT_IDENTIFIER_1)
        def handler_invalid(self, parameter_2) -> None:
            pass

    with pytest.raises(XNodeException, match=re.escape(
            f"Node '{NODE_IDENTIFIER_1}' handles event '{EVENT_IDENTIFIER_1}', but the parameters do not match. "
            f"Event requires: ['{EVENT_PARAMETER_NAME_1}'], handler provides: ['parameter_2'].")):
        x_core.register_node(NODE_IDENTIFIER_1, Node())


def test_register_node_no_exception() -> None:
    _reset_x_core()

    x_core.register_event(EVENT_IDENTIFIER_1, {EVENT_PARAMETER_NAME_1, EVENT_PARAMETER_NAME_2})

    class Node:
        @x_event_handler(EVENT_IDENTIFIER_1)
        def handler_invalid(self, parameter_1, parameter_2) -> None:
            pass

    x_core.register_node(NODE_IDENTIFIER_1, Node())


def test_unregister_node_raise_invalid_node() -> None:
    _reset_x_core()

    with pytest.raises(XNodeException, match=re.escape(
            f"Attempted to unregister node '{NODE_IDENTIFIER_1}', but no node with that identifier is registered.")):
        x_core.unregister_node(NODE_IDENTIFIER_1)


def test_unregister_node() -> None:
    _reset_x_core()

    x_core.register_event(EVENT_IDENTIFIER_1, set())
    x_core.register_event(EVENT_IDENTIFIER_2, set())

    class Node:
        @x_event_handler(EVENT_IDENTIFIER_2)
        def handler(self) -> None:
            pass

    x_core.register_node(NODE_IDENTIFIER_1, Node())
    x_core.unregister_node(NODE_IDENTIFIER_1)


def test_start_raise_invalid_maximum_logging_length() -> None:
    _reset_x_core()

    configuration = XCoreConfiguration(logging.INFO, True, False, 0, 1000)

    with pytest.raises(XNodeException, match=re.escape(
            f"Invalid configuration: 'identifier_maximum_logging_length' has to be greater or equal to 10.")):
        x_core.start(configuration)


def test_start(monkeypatch) -> None:
    _reset_x_core()

    broadcast_mock = MagicMock()
    monkeypatch.setattr(x_core, "broadcast", broadcast_mock)

    x_core.start()
    broadcast_mock.assert_called_once_with(X_CORE_START, X_CORE_NODE_IDENTIFIER, {})


def test_publish_raise_event_not_registered() -> None:
    _reset_x_core()

    with pytest.raises(XNodeException, match=re.escape(
            f"Node '{NODE_IDENTIFIER_1}' attempted to publish event '{EVENT_IDENTIFIER_1}' to node "
            f"'{NODE_IDENTIFIER_2}', but the event is not registered.")):
        x_core.publish(EVENT_IDENTIFIER_1, NODE_IDENTIFIER_1, NODE_IDENTIFIER_2, {})


def test_publish_raise_sender_not_registered() -> None:
    _reset_x_core()

    x_core.register_event(EVENT_IDENTIFIER_1, set())

    with pytest.raises(XNodeException, match=re.escape(
            f"Node '{NODE_IDENTIFIER_1}' attempted to publish event '{EVENT_IDENTIFIER_1}' to node "
            f"'{NODE_IDENTIFIER_2}', but the sender node is not registered.")):
        x_core.publish(EVENT_IDENTIFIER_1, NODE_IDENTIFIER_1, NODE_IDENTIFIER_2, {})


def test_publish_raise_receiver_not_registered() -> None:
    _reset_x_core()

    class Node:
        pass

    x_core.register_event(EVENT_IDENTIFIER_1, set())
    x_core.register_node(NODE_IDENTIFIER_1, Node())

    with pytest.raises(XNodeException, match=re.escape(
            f"Node '{NODE_IDENTIFIER_1}' attempted to publish event '{EVENT_IDENTIFIER_1}' to node "
            f"'{NODE_IDENTIFIER_2}', but the receiver node is not registered.")):
        x_core.publish(EVENT_IDENTIFIER_1, NODE_IDENTIFIER_1, NODE_IDENTIFIER_2, {})


def test_publish_raise_receiver_not_handles_event() -> None:
    _reset_x_core()

    class Node:
        pass

    x_core.register_event(EVENT_IDENTIFIER_1, set())
    x_core.register_node(NODE_IDENTIFIER_1, Node())
    x_core.register_node(NODE_IDENTIFIER_2, Node())

    with pytest.raises(XNodeException, match=re.escape(
            f"Node '{NODE_IDENTIFIER_1}' attempted to publish event '{EVENT_IDENTIFIER_1}' to node "
            f"'{NODE_IDENTIFIER_2}', but receiver '{NODE_IDENTIFIER_2}' is not subscribed to event "
            f"'{EVENT_IDENTIFIER_1}'.")):
        x_core.publish(EVENT_IDENTIFIER_1, NODE_IDENTIFIER_1, NODE_IDENTIFIER_2, {})


def test_publish(monkeypatch) -> None:
    _reset_x_core()

    class Node:
        @x_event_handler(EVENT_IDENTIFIER_1)
        def handler(self) -> None:
            pass

    x_core.register_event(EVENT_IDENTIFIER_1, set())
    x_core.register_node(NODE_IDENTIFIER_1, Node())
    x_core.register_node(NODE_IDENTIFIER_2, Node())

    publish_events_mock = MagicMock()
    monkeypatch.setattr(x_core, "_publish_events", publish_events_mock)

    built_event = "BUILT_EVENT"
    build_event_mock = MagicMock()
    build_event_mock.return_value = built_event
    monkeypatch.setattr(x_core, "_build_event", build_event_mock)

    x_core.publish(EVENT_IDENTIFIER_1, NODE_IDENTIFIER_1, NODE_IDENTIFIER_2, {})
    build_event_mock.assert_called_once_with(EVENT_IDENTIFIER_1, NODE_IDENTIFIER_1, NODE_IDENTIFIER_2, {})
    publish_events_mock.assert_called_once_with([built_event], is_undo=False)


def test_broadcast_raise_event_not_registered() -> None:
    _reset_x_core()

    with pytest.raises(XNodeException, match=re.escape(
            f"Node '{NODE_IDENTIFIER_1}' attempted to broadcast event '{EVENT_IDENTIFIER_1}', but the event is not "
            f"registered.")):
        x_core.broadcast(EVENT_IDENTIFIER_1, NODE_IDENTIFIER_1, {})


def test_broadcast_raise_sender_not_registered() -> None:
    _reset_x_core()

    x_core.register_event(EVENT_IDENTIFIER_1, set())

    with pytest.raises(XNodeException, match=re.escape(
            f"Node '{NODE_IDENTIFIER_1}' attempted to broadcast event '{EVENT_IDENTIFIER_1}', but the sender node is not "
            f"registered.")):
        x_core.broadcast(EVENT_IDENTIFIER_1, NODE_IDENTIFIER_1, {})


def test_broadcast(monkeypatch) -> None:
    _reset_x_core()

    class Node:
        @x_event_handler(EVENT_IDENTIFIER_1)
        def handler(self) -> None:
            pass

    x_core.register_event(EVENT_IDENTIFIER_1, set())
    x_core.register_node(NODE_IDENTIFIER_1, MagicMock())
    x_core.register_node(NODE_IDENTIFIER_2, Node())

    publish_events_mock = MagicMock()
    monkeypatch.setattr(x_core, "_publish_events", publish_events_mock)

    built_event = "BUILT_EVENT"
    build_event_mock = MagicMock()
    build_event_mock.return_value = built_event
    monkeypatch.setattr(x_core, "_build_event", build_event_mock)

    x_core.broadcast(EVENT_IDENTIFIER_1, NODE_IDENTIFIER_1, {})
    build_event_mock.assert_called_once_with(EVENT_IDENTIFIER_1, NODE_IDENTIFIER_1, NODE_IDENTIFIER_2, {})
    publish_events_mock.assert_called_once_with([built_event], is_undo=False)


def test_broadcast_no_receiver(monkeypatch) -> None:
    _reset_x_core()

    x_core.register_event(EVENT_IDENTIFIER_1, set())
    x_core.register_node(NODE_IDENTIFIER_1, MagicMock())

    publish_events_mock = MagicMock()
    monkeypatch.setattr(x_core, "_publish_events", publish_events_mock)

    build_event_mock = MagicMock()
    monkeypatch.setattr(x_core, "_build_event", build_event_mock)

    logger_warning_mock = MagicMock()
    monkeypatch.setattr(x_core.LOGGER, "warning", logger_warning_mock)

    x_core.broadcast(EVENT_IDENTIFIER_1, NODE_IDENTIFIER_1, {})
    build_event_mock.assert_not_called()
    publish_events_mock.assert_not_called()
    logger_warning_mock.assert_called_once_with(f"*** Node '{NODE_IDENTIFIER_1}' attempted to broadcast event "
                                                f"'{EVENT_IDENTIFIER_1}', but it echoed in the void... ***")


def test_add_undo_events(monkeypatch) -> None:
    _reset_x_core()

    x_core._REDO_STACK.append([XEvent("TEST", XEventDescription(set()), "", "", {})])

    append_undo_events_mock = MagicMock()
    monkeypatch.setattr(x_core, "_append_undo_events", append_undo_events_mock)

    publish_undo_redo_counters_mock = MagicMock()
    monkeypatch.setattr(x_core, "_publish_undo_redo_counters", publish_undo_redo_counters_mock)

    x_core.add_undo_events([])
    assert len(x_core._REDO_STACK) == 0
    append_undo_events_mock.assert_called_once_with([])
    publish_undo_redo_counters_mock.assert_called_once()


def test_undo_events(monkeypatch) -> None:
    _reset_x_core()

    x_core._UNDO_STACK.append([XEvent("TEST", XEventDescription(set()), "", "", {})])

    publish_events_mock = MagicMock()
    monkeypatch.setattr(x_core, "_publish_events", publish_events_mock)

    x_core._undo_events()
    publish_events_mock.assert_called_once_with(ANY, is_undo=True)


def test_undo_events_no_undo_events(monkeypatch) -> None:
    _reset_x_core()

    publish_events_mock = MagicMock()
    monkeypatch.setattr(x_core, "_publish_events", publish_events_mock)

    x_core._undo_events()
    publish_events_mock.assert_not_called()


def test_redo_events(monkeypatch) -> None:
    _reset_x_core()

    x_core._REDO_STACK.append([XEvent("TEST", XEventDescription(set()), "", "", {})])

    publish_events_mock = MagicMock()
    monkeypatch.setattr(x_core, "_publish_events", publish_events_mock)

    x_core._redo_events()
    publish_events_mock.assert_called_once_with(ANY, is_undo=False)


def test_redo_events_no_redo_events(monkeypatch) -> None:
    _reset_x_core()

    publish_events_mock = MagicMock()
    monkeypatch.setattr(x_core, "_publish_events", publish_events_mock)

    x_core._redo_events()
    publish_events_mock.assert_not_called()


def test_append_undo_events() -> None:
    _reset_x_core()

    event = XEvent("TEST", XEventDescription(set()), "", "", {})

    x_core._REDO_STACK.append([event])
    x_core._REDO_STACK.append([event])
    x_core._REDO_STACK.append([event])

    x_core._append_undo_events([event])
    assert len(x_core._REDO_STACK) == 3
    assert len(x_core._UNDO_STACK) == 1


def test_append_undo_remove_oldest_redo_event() -> None:
    _reset_x_core()

    first_event = XEvent("TEST", XEventDescription(set()), "", "", {})
    other_event = XEvent("TEST", XEventDescription(set()), "", "", {})

    x_core._UNDO_STACK.append([first_event])
    for i in range(998):
        x_core._UNDO_STACK.append([other_event])

    assert len(x_core._UNDO_STACK) == 999
    x_core._append_undo_events([first_event])
    assert len(x_core._UNDO_STACK) == 1000
    x_core._append_undo_events([other_event])
    assert len(x_core._UNDO_STACK) == 1000
    assert x_core._UNDO_STACK[0][0] is not first_event


def test_append_undo_keep_all_undo_events() -> None:
    _reset_x_core()

    x_core._CONFIGURATION = XCoreConfiguration(maximum_undo_events=-1)

    event = XEvent("TEST", XEventDescription(set()), "", "", {})

    events_to_add = 100000
    for i in range(events_to_add):
        assert len(x_core._UNDO_STACK) == i
        x_core._append_undo_events([event])
        assert len(x_core._UNDO_STACK) == i + 1


def test_clear_undo_redo_stack(monkeypatch) -> None:
    _reset_x_core()

    publish_undo_redo_counters_mock = MagicMock()
    monkeypatch.setattr(x_core, "_publish_undo_redo_counters", publish_undo_redo_counters_mock)

    event = XEvent("TEST", XEventDescription(set()), "", "", {})

    x_core._UNDO_STACK.append([event])
    x_core._REDO_STACK.append([event])

    x_core._clear_undo_redo_stacks()
    assert len(x_core._UNDO_STACK) == 0
    assert len(x_core._REDO_STACK) == 0
    publish_undo_redo_counters_mock.assert_called_once()


def test_publish_undo_redo_counters(monkeypatch) -> None:
    _reset_x_core()

    broadcast_mock = MagicMock()
    monkeypatch.setattr(x_core, "broadcast", broadcast_mock)

    event = XEvent(EVENT_IDENTIFIER_1, XEventDescription(set()), "", "", {})

    undo_count = 21
    redo_count = 21

    for i in range(undo_count):
        x_core._UNDO_STACK.append([event])

    for i in range(redo_count):
        x_core._REDO_STACK.append([event])

    x_core._publish_undo_redo_counters()
    broadcast_mock.assert_called_once_with(x_core.X_MAP_UNDO_REDO_COUNTERS, x_core.X_CORE_NODE_IDENTIFIER, {
        "undo_counter": undo_count,
        "redo_counter": redo_count
    })


def test_build_event_raise_event_not_registered() -> None:
    _reset_x_core()

    with pytest.raises(XNodeException,
                       match=re.escape(f"Attempted to create an unknown event '{EVENT_IDENTIFIER_1}'.")):
        x_core._build_event(EVENT_IDENTIFIER_1, NODE_IDENTIFIER_1, NODE_IDENTIFIER_2, {})


def test_build_event_raise_event_parameter_not_matching() -> None:
    _reset_x_core()

    registered_parameter_1 = "parameter_1"
    registered_parameter_2 = "parameter_2"
    provided_parameter_1 = "parameter_3"
    provided_parameter_2 = "parameter_4"

    x_core.register_event(EVENT_IDENTIFIER_1, {registered_parameter_1, (registered_parameter_2, bool)})

    with pytest.raises(XNodeException,
                       match="Event 'event' cannot be constructed, event requires: \\['parameter_1|2', "
                             "'parameter_1|2'\\], provided are: \\['parameter_3|4', 'parameter_3|4'\\]\\."):
        x_core._build_event(EVENT_IDENTIFIER_1, NODE_IDENTIFIER_1, NODE_IDENTIFIER_2,
                            {provided_parameter_1: 42, provided_parameter_2: "test"})


def test_build_event() -> None:
    _reset_x_core()

    x_core.register_event(EVENT_IDENTIFIER_1, {EVENT_PARAMETER_NAME_1, (EVENT_PARAMETER_NAME_2, bool)})

    event = x_core._build_event(EVENT_IDENTIFIER_1, NODE_IDENTIFIER_1, NODE_IDENTIFIER_2,
                                {EVENT_PARAMETER_NAME_1: 42, EVENT_PARAMETER_NAME_2: "test"})

    assert event.identifier == EVENT_IDENTIFIER_1
    assert event.sender_identifier == NODE_IDENTIFIER_1
    assert event.receiver_identifier == NODE_IDENTIFIER_2


def test_log(monkeypatch) -> None:
    _reset_x_core()

    base_logging_string = "BASE"
    parameters_logging_string = "PARAMETERS"

    create_base_logging_string_mock = MagicMock()
    create_base_logging_string_mock.return_value = base_logging_string
    monkeypatch.setattr(x_core, "_create_base_logging_string", create_base_logging_string_mock)

    create_parameters_logging_string_mock = MagicMock()
    create_parameters_logging_string_mock.return_value = parameters_logging_string + "        "
    monkeypatch.setattr(x_core, "_create_parameters_logging_string", create_parameters_logging_string_mock)

    log_mock = MagicMock()
    monkeypatch.setattr(x_core.LOGGER, "log", log_mock)

    event_mock = MagicMock()
    event_mock.event_description.log_level = logging.INFO

    x_core._log(event_mock)
    log_mock.assert_called_once_with(logging.INFO, f"{base_logging_string}{parameters_logging_string}")


def test_create_base_logging_string(monkeypatch) -> None:
    _reset_x_core()

    identifier_maximum_logging_length = 20

    configuration_mock = MagicMock()
    configuration_mock.identifier_maximum_logging_length = identifier_maximum_logging_length
    configuration_mock.log_event_parameters = False
    monkeypatch.setattr(x_core, "_CONFIGURATION", configuration_mock)

    event_mock = MagicMock()
    event_mock.sender_identifier = NODE_IDENTIFIER_1
    event_mock.receiver_identifier = NODE_IDENTIFIER_2
    event_mock.identifier = EVENT_IDENTIFIER_1
    event_mock.event_description.log_level = logging.INFO

    base_logging_string = x_core._create_base_logging_string(event_mock)
    assert base_logging_string == f"   {NODE_IDENTIFIER_1} ----- {EVENT_IDENTIFIER_1} ----> {NODE_IDENTIFIER_2}   "


def test_create_parameters_logging_string(monkeypatch) -> None:
    _reset_x_core()

    configuration_mock = MagicMock()
    configuration_mock.identifier_maximum_logging_length = 10
    configuration_mock.event_parameter_maximum_logging_length = 30
    configuration_mock.log_event_parameters = True
    monkeypatch.setattr(x_core, "_CONFIGURATION", configuration_mock)

    event_mock = MagicMock()
    event_mock.event_description.log_level = logging.INFO
    event_mock.event_description.parameters = {(EVENT_PARAMETER_NAME_1, int)}
    event_mock.parameters = {EVENT_PARAMETER_NAME_1: "21"}

    assert x_core._create_parameters_logging_string(event_mock) == f" | {EVENT_PARAMETER_NAME_1} (int / str): '21'"


def test_log_with_parameters_empty_if_disabled(monkeypatch) -> None:
    _reset_x_core()

    configuration_mock = MagicMock()
    configuration_mock.log_event_parameters = False
    monkeypatch.setattr(x_core, "_CONFIGURATION", configuration_mock)

    event_mock = MagicMock()
    assert x_core._create_parameters_logging_string(event_mock) == ""


def test_log_with_parameters_empty_if_no_parameters_are_available(monkeypatch) -> None:
    _reset_x_core()

    configuration_mock = MagicMock()
    configuration_mock.log_event_parameters = True
    monkeypatch.setattr(x_core, "_CONFIGURATION", configuration_mock)

    event_mock = MagicMock()
    event_mock.event_description.parameters = set()
    assert x_core._create_parameters_logging_string(event_mock) == ""


def test_publish_events_no_undo_events_but_is_undo(monkeypatch) -> None:
    _reset_x_core()

    event_mock = MagicMock()
    event_mock.receiver_identifier = NODE_IDENTIFIER_1

    monkeypatch.setattr(x_core, "EventPublishingContext", MagicMock())
    monkeypatch.setattr(x_core, "_log", MagicMock())
    monkeypatch.setattr(x_core, "_execute_event", MagicMock())
    monkeypatch.setattr(x_core, "_extract_undo_events", MagicMock())

    publish_undo_redo_counters_mock = MagicMock()
    monkeypatch.setattr(x_core, "_publish_undo_redo_counters", publish_undo_redo_counters_mock)

    assert len(x_core._REDO_STACK) == 0
    x_core._publish_events([event_mock], is_undo=True)
    assert len(x_core._REDO_STACK) == 0
    publish_undo_redo_counters_mock.assert_called_once()


def test_publish_events_no_undo_events_is_not_undo(monkeypatch) -> None:
    _reset_x_core()

    event_mock = MagicMock()
    event_mock.receiver_identifier = NODE_IDENTIFIER_1

    monkeypatch.setattr(x_core, "_log", MagicMock())
    monkeypatch.setattr(x_core, "_execute_event", MagicMock())
    monkeypatch.setattr(x_core, "_extract_undo_events", MagicMock())

    event_publishing_context_mock = MagicMock()
    monkeypatch.setattr(x_core, "EventPublishingContext", event_publishing_context_mock)

    publish_undo_redo_counters_mock = MagicMock()
    monkeypatch.setattr(x_core, "_publish_undo_redo_counters", publish_undo_redo_counters_mock)

    x_core._publish_events([event_mock], is_undo=False)
    publish_undo_redo_counters_mock.assert_not_called()


def test_publish_events_undo_events_is_undo(monkeypatch) -> None:
    _reset_x_core()

    event_mock = MagicMock()
    event_mock.receiver_identifier = NODE_IDENTIFIER_1

    monkeypatch.setattr(x_core, "EventPublishingContext", MagicMock())
    monkeypatch.setattr(x_core, "_log", MagicMock())
    monkeypatch.setattr(x_core, "_execute_event", MagicMock())

    extract_undo_events_mock = MagicMock()
    extract_undo_events_mock.return_value = [event_mock]
    monkeypatch.setattr(x_core, "_extract_undo_events", extract_undo_events_mock)

    publish_undo_redo_counters_mock = MagicMock()
    monkeypatch.setattr(x_core, "_publish_undo_redo_counters", publish_undo_redo_counters_mock)

    assert len(x_core._REDO_STACK) == 0
    x_core._publish_events([event_mock], is_undo=True)
    assert len(x_core._REDO_STACK) == 1
    publish_undo_redo_counters_mock.assert_called_once()


def test_publish_events_undo_events_is_not_undo(monkeypatch) -> None:
    _reset_x_core()

    event_mock = MagicMock()
    event_mock.receiver_identifier = NODE_IDENTIFIER_1

    monkeypatch.setattr(x_core, "EventPublishingContext", MagicMock())
    monkeypatch.setattr(x_core, "_log", MagicMock())
    monkeypatch.setattr(x_core, "_execute_event", MagicMock())

    extract_undo_events_mock = MagicMock()
    extract_undo_events_mock.return_value = [event_mock]
    monkeypatch.setattr(x_core, "_extract_undo_events", extract_undo_events_mock)

    publish_undo_redo_counters_mock = MagicMock()
    monkeypatch.setattr(x_core, "_publish_undo_redo_counters", publish_undo_redo_counters_mock)

    append_undo_events_mock = MagicMock()
    monkeypatch.setattr(x_core, "_append_undo_events", append_undo_events_mock)

    assert len(x_core._REDO_STACK) == 0
    x_core._publish_events([event_mock], is_undo=False)
    assert len(x_core._REDO_STACK) == 0
    append_undo_events_mock.assert_called_once()
    publish_undo_redo_counters_mock.assert_called_once()


def test_execute_event_raise_event_not_subscribed() -> None:
    _reset_x_core()

    event_mock = MagicMock()
    event_mock.identifier = EVENT_IDENTIFIER_1
    event_mock.receiver_identifier = NODE_IDENTIFIER_1

    with pytest.raises(XNodeException, match=re.escape(
            f"Attempted to send event with identifier '{EVENT_IDENTIFIER_1}' to node '{NODE_IDENTIFIER_1}', but the "
            f"node is not subscribed to that event.")):
        x_core._execute_event(event_mock)


def test_execute_event() -> None:
    _reset_x_core()

    parameter_1_value = 21
    parameter_2_value = 42

    parameter_description = {(EVENT_PARAMETER_NAME_2, int), (EVENT_PARAMETER_NAME_1, int)}

    class Node:

        def __init__(self):
            self.is_called = False

        @x_event_handler(EVENT_IDENTIFIER_1)
        def handler(self, parameter_1: int, parameter_2: int):
            self.is_called = True

            assert parameter_1 == parameter_1_value
            assert parameter_2 == parameter_2_value

    node = Node()
    x_core.register_event(EVENT_IDENTIFIER_1, parameter_description)
    x_core.register_node(NODE_IDENTIFIER_1, node)

    event_mock = MagicMock()
    event_mock.identifier = EVENT_IDENTIFIER_1
    event_mock.receiver_identifier = NODE_IDENTIFIER_1
    event_mock.event_description = XEventDescription(parameter_description)
    event_mock.parameters = {EVENT_PARAMETER_NAME_1: parameter_1_value, EVENT_PARAMETER_NAME_2: parameter_2_value}

    x_core._execute_event(event_mock)
    assert node.is_called


def test_extract_undo_events_not_a_generator() -> None:
    _reset_x_core()

    assert len(x_core._extract_undo_events(None, "")) == 0


@pytest.mark.parametrize("undo_event",
                         [None, (None,), (None, None, None)],
                         ids=["Not a tuple", "Too few elements", "Too many elements"])
def test_extract_undo_events_invalid_undo_event_type(undo_event) -> None:
    _reset_x_core()

    with pytest.raises(XNodeException,
                       match=re.escape("Undo event has to be a tuple consisting of the event and the parameters.")):
        x_core._extract_undo_events(iter([undo_event]), "")


def test_extract_undo_events_invalid_parameters_type() -> None:
    _reset_x_core()

    with pytest.raises(XNodeException,
                       match=re.escape("Undo event parameters has an invalid type, should be dict, is: 'int'.")):
        x_core._extract_undo_events(iter([("test", 42)]), "")


def test_extract_undo_events(monkeypatch) -> None:
    _reset_x_core()

    parameters = {"test": 42}

    build_event_mock = MagicMock()
    build_event_mock.return_value = MagicMock()
    monkeypatch.setattr(x_core, "_build_event", build_event_mock)

    assert len(x_core._extract_undo_events(iter([(EVENT_IDENTIFIER_1, parameters)]), NODE_IDENTIFIER_1)) == 1
    build_event_mock.assert_called_once_with(EVENT_IDENTIFIER_1, NODE_IDENTIFIER_1, NODE_IDENTIFIER_1, parameters)


def test_event_publishing_context_no_log_if_logging_level_too_high(monkeypatch) -> None:
    _reset_x_core()

    event_mock = MagicMock()
    event_mock.event_description.log_level = logging.DEBUG

    log_mock = MagicMock()
    monkeypatch.setattr(x_core.LOGGER, "log", log_mock)

    configuration_mock = MagicMock()
    configuration_mock.log_level = logging.INFO
    monkeypatch.setattr(x_core, "_CONFIGURATION", configuration_mock)

    with EventPublishingContext([event_mock]):
        pass

    log_mock.assert_not_called()


def test_event_publishing_context(monkeypatch) -> None:
    _reset_x_core()

    event_mock = MagicMock()
    event_mock.event_description.log_level = logging.DEBUG

    log_mock = MagicMock()
    monkeypatch.setattr(x_core.LOGGER, "log", log_mock)

    configuration_mock = MagicMock()
    configuration_mock.log_level = logging.DEBUG
    monkeypatch.setattr(x_core, "_CONFIGURATION", configuration_mock)

    with EventPublishingContext([event_mock]):
        # Second context within the first context should not log an empty line again.
        with EventPublishingContext([event_mock]):
            pass

    log_mock.assert_called_once()
