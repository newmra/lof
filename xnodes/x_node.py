"""
xnodes: Exchange nodes framework
        Simplistic event framework which enables unrelated nodes to exchange information, alter each other states and
        provides the possibility to undo made changes.

Author: Ralph Neumann (@newmra)

This framework is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
License as published by the Free Software Foundation, see <https://www.gnu.org/licenses/>.
"""

from xnodes import x_core


class XNode:
    """
    Node which can exchange events with other nodes.
    """

    def __init__(self, node_type: str, *args, is_static: bool = False, **kwargs):
        """
        Init of XNode.
        :param: Type of the node.
        :param args: Additional arguments for other super classes.
        :param is_static: Flag if the node type should be used as ID and that there is no other node of the same type.
        :param kwargs: Additional keyword arguments for other super classes.
        """
        super().__init__(*args, **kwargs)

        self.__identifier = node_type if is_static else f"{node_type}_{id(self)}"
        x_core.register_node(self.__identifier, self)

    def delete(self) -> None:
        """
        Delete the node and unregister it from the core.
        :return: None
        """
        x_core.unregister_node(self.__identifier)

    @property
    def identifier(self) -> str:
        """
        Get the identifier of the node.
        :return: Identifier of the node.
        """
        return self.__identifier

    def publish(self, event_identifier: str, receiver_identifier: str, **parameters) -> None:
        """
        Publish a new event and send it to a single node.
        :param event_identifier: Identifier of the event to publish.
        :param receiver_identifier: Identifier of the node to with the event shall be delivered.
        :param parameters: Parameters of the event.
        :return: None
        """
        x_core.publish(event_identifier, self.__identifier, receiver_identifier, parameters)

    def broadcast(self, event_identifier: str, **parameters) -> None:
        """
        Publish a new event and send it to all nodes which subscribed to the event.
        :param event_identifier: Identifier of the event to publish.
        :param parameters: Parameters of the event.
        :return: None
        """
        x_core.broadcast(event_identifier, self.__identifier, parameters)
