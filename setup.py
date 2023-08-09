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

from setuptools import setup, find_packages

setup(
    name='xnodes',
    author="Ralph Neumann",
    maintainer="Ralph Neumann",
    description="Framework for a system wide event communication between nodes with undo/redo functionality for UIs.",
    long_description_content_type="text/markdown",
    long_description="""
    XNodes (Exchanging nodes) provides a global event bus to which individual nodes can connect to and send events to 
    other nodes. Nodes do not know each other, they communicate via the event bus by their individual IDs.
    The framework also provides a possibility for nodes to offer undo-events when receiving events. If an event alters
    the state of a node, the node has then the responsibility to provide an event which undos the changes made by the
    received event. Those undo-events are stored by the event bus and can then be fed again into the system.
    
    For more information and code examples, please visit the Github project.
    """,
    version='v0.0.12-beta',
    packages=find_packages(),
    install_requires=[],
    license="GNU GENERAL PUBLIC LICENSE 3"
)
