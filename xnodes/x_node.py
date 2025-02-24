"""
xnodes: Exchange nodes framework
        Simplistic event framework which enables unrelated nodes to exchange information, alter each other states and
        provides the possibility to undo made changes.

Author: Ralph Neumann (@newmra)
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

        self.__id = node_type if is_static else f"{node_type}_{id(self)}"
        x_core.register_node(self.__id, self)

    def delete(self) -> None:
        """
        Delete the node and unregister it from the core.
        :return: None
        """
        x_core.unregister_node(self.__id)

    @property
    def id(self) -> str:
        """
        Get the ID of the node.
        :return: ID of the node.
        """
        return self.__id

    def publish(self, event_id: str, receiver_id: str, **parameters) -> None:
        """
        Publish a new event and send it to a single node.
        :param event_id: ID of the event to publish.
        :param receiver_id: ID of the node to with the event shall be delivered.
        :param parameters: Parameters of the event.
        :return: None
        """
        x_core.publish(event_id, self.__id, receiver_id, parameters)

    def broadcast(self, event_id: str, **parameters) -> None:
        """
        Publish a new event and send it to all nodes which subscribed to the event.
        :param event_id: ID of the event to publish.
        :param parameters: Parameters of the event.
        :return: None
        """
        x_core.broadcast(event_id, self.__id, parameters)
