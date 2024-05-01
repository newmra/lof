"""
xnodes: Exchange nodes framework
        Simplistic event framework which enables unrelated nodes to exchange information, alter each other states and
        provides the possibility to undo made changes.

Author: Ralph Neumann (@newmra)

This framework is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
License as published by the Free Software Foundation, see <https://www.gnu.org/licenses>.
"""

from unittest.mock import MagicMock

from xnodes import XNode

NODE_TYPE = "MY_NODE"

EVENT_IDENTIFIER = "EVENT_IDENTIFIER"
PARAMETER_1 = 42
PARAMETER_2 = "TEST"


def test_anonymous_node_creation(monkeypatch) -> None:
    """
    Construct an XNode with a not-static node type and expect an anonymous identifier.
    :param monkeypatch: Monkeypatch.
    :return: None
    """
    register_node_mock = MagicMock()
    monkeypatch.setattr("xnodes.x_node.x_core.register_node", register_node_mock)

    node = XNode(NODE_TYPE)
    register_node_mock.assert_called_once_with(f"{NODE_TYPE}_{id(node)}", node)


def test_static_node_creation(monkeypatch) -> None:
    """
    Construct an XNode with a static node type and expect the identifier to be the node type.
    :param monkeypatch: Monkeypatch.
    :return: None
    """
    register_node_mock = MagicMock()
    monkeypatch.setattr("xnodes.x_node.x_core.register_node", register_node_mock)

    node = XNode(NODE_TYPE, is_static=True)
    register_node_mock.assert_called_once_with(NODE_TYPE, node)


def test_delete_node(monkeypatch) -> None:
    """
    Construct an XNode and delete it again.
    :param monkeypatch: Monkeypatch.
    :return: None
    """
    register_node_mock = MagicMock()
    monkeypatch.setattr("xnodes.x_node.x_core.register_node", register_node_mock)

    unregister_node_mock = MagicMock()
    monkeypatch.setattr("xnodes.x_node.x_core.unregister_node", unregister_node_mock)

    node = XNode(NODE_TYPE, is_static=True)
    register_node_mock.assert_called_once_with(NODE_TYPE, node)

    node.delete()
    unregister_node_mock.assert_called_once_with(node.identifier)


def test_publish_event(monkeypatch) -> None:
    """
    Construct an XNode, publish an event and expect the values to be passed correctly.
    :param monkeypatch: Monkeypatch.
    :return: None
    """
    receiver_node_identifier = "OTHER_NODE"
    expected_event_parameters = {
        "parameter_1": PARAMETER_1,
        "parameter_2": PARAMETER_2
    }

    register_node_mock = MagicMock()
    monkeypatch.setattr("xnodes.x_node.x_core.register_node", register_node_mock)

    publish_mock = MagicMock()
    monkeypatch.setattr("xnodes.x_node.x_core.publish", publish_mock)

    node = XNode(NODE_TYPE, is_static=True)
    register_node_mock.assert_called_once_with(NODE_TYPE, node)

    node.publish(EVENT_IDENTIFIER, receiver_node_identifier, parameter_1=PARAMETER_1, parameter_2=PARAMETER_2)
    publish_mock.assert_called_once_with(
        EVENT_IDENTIFIER, node.identifier, receiver_node_identifier, expected_event_parameters)


def test_broadcast_event(monkeypatch) -> None:
    """
    Construct an XNode, broadcast an event and expect the values to be passed correctly.
    :param monkeypatch: Monkeypatch.
    :return: None
    """
    expected_event_parameters = {
        "parameter_1": PARAMETER_1,
        "parameter_2": PARAMETER_2
    }

    register_node_mock = MagicMock()
    monkeypatch.setattr("xnodes.x_node.x_core.register_node", register_node_mock)

    broadcast_mock = MagicMock()
    monkeypatch.setattr("xnodes.x_node.x_core.broadcast", broadcast_mock)

    node = XNode(NODE_TYPE, is_static=True)
    register_node_mock.assert_called_once_with(NODE_TYPE, node)

    node.broadcast(EVENT_IDENTIFIER, parameter_1=PARAMETER_1, parameter_2=PARAMETER_2)
    broadcast_mock.assert_called_once_with(EVENT_IDENTIFIER, node.identifier, expected_event_parameters)
