"""
xnodes: Exchange nodes framework
        Simplistic event framework which enables unrelated nodes to exchange information, alter each other states and
        provides the possibility to undo made changes.

Author: Ralph Neumann (@newmra)
"""


class XNodeException(Exception):
    """
    Specialization of exception for XNode exceptions.
    """
