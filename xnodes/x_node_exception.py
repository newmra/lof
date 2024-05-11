"""
xnodes: Exchange nodes framework
        Simplistic event framework which enables unrelated nodes to exchange information, alter each other states and
        provides the possibility to undo made changes.

Author: Ralph Neumann (@newmra)

This framework is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
License as published by the Free Software Foundation, see <https://www.gnu.org/licenses/>.
"""


class XNodeException(Exception):
    """
    Specialization of exception for XNode exceptions.
    """
