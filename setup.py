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

from setuptools import setup

LONG_DESCRIPTION = """# XNodes (Exchanging nodes)

### WORK IN PROGRESS, CURRENTLY NOT FUNCTIONAL

## About

XNodes is an application framework which provides an event mechanism for unrelated nodes by utilizing a global event bus. The framework's initial purpose was to establish a lightweigth mechanism for exchanging information between UI widgets and a data model, all without necessitating their mutual awareness. Upon receiving an event which alters the state of a node, the receiving node can provide an event in return which undos the made changes. This way an easy to use but powerful undo/redo mechanism is realized.

## How to use

### Application start
Before any node is constructed, all events with their parameters which are used within the system have to be registers in the event bus called _XNodeBus_. _XNodeBus_ consists of staticmethods only, so instantiating it is not necessary. When adding an event to the bus, one can provide an optional log level for that event which will be used during logging when that event is published, default log level is _INFO_.

```
import logging

from xnodes import XNodeBus

EVENT_A = "EVENT_A"
EVENT_B = "EVENT_B"

XNodeBus.add_event(EVENT_A, (int, str))
XNodeBus.add_event(EVENT_B, (bool, list), logging.DEBUG)
```

If a node wants to publish an event, the types of the parameters have to match the types provided during registration. If the parameter types do not match, a _ValueError_ is raised during publication.

### Node initialization

To create a node, a class has to inherit from the _XNode_ class. Every node has a type and when a class inherits from _XNode_, the type has to be provided to _XNode_. Purpose of this type is easier identification of nodes and the possibility of other nodes to publish events to all nodes of a certain type.

```
from xnodes import XNode

MY_NODE_TYPE = "MY_NODE"

class MyNode(XNode):
    
    def __init__():
        XNode.__init__(self, MY_NODE_TYPE)

instance1 = MyNode()  # ID: MY_NODE
instance2 = MyNode()  # ID: MY_NODE_1
instance3 = MyNode()  # ID: MY_NODE_2
```

The created instances of MyNode both have unique IDs within the node type MY_NODE. Note that the first instance will receive an ID equal to the node type, but the second ID has a suffix. Background for this is that if only one node instance of a type exists in the application, it can be directly referred to by its type. This makes it easier to address services in the application.

### Receiving events

In order to receive an event, a node has to implement an event handler function and decorate it with the _xevent_ decorator function.

```
from xnodes import XNode, xevent

MY_NODE_TYPE = "MY_NODE"
EVENT_A = "EVENT_A"
EVENT_B = "EVENT_B"

class MyNode(XNode):
    
    def __init__():
        XNode.__init__(self, MY_NODE_TYPE)
    
    @xevent(EVENT_A)
    def handle_event(self, parameter_1: int, parameter_2: str):
        pass  # Do something with the event.
    
    @xevent(EVENT_B)
    def handle_event(self, parameter_1: bool, parameter_2: list):
        pass  # Do something with the event.
```

The decorator _xevent_ takes as argument the identifier of the event which the decorated function is supposed to handle. Note that the names of both of the event handler functions above are the same, which is not possible in standard Python. This is achieved by a custom metaclass of _XNode_, which stores all functions which are decorated with _xevent_ in a separate dictionary and identifies the function by the event identifier and not by its name. In fact, the name of an event handler function is completely irrelevant and one is free to name them all the same or give them different names.

### Publishing events

XNode provides two functions to publish events. The first is the _publish_ function, which delivers one single event to one single node which is specified by its ID. The second is the _broadcast_ function which delivers an event to every node which subscribed to the published event.

```
from xnodes import XNode

MY_NODE_TYPE = "MY_NODE"
EVENT_A = "EVENT_A"
EVENT_B = "EVENT_B"

class MyNode(XNode):
    
    def __init__():
        XNode.__init__(self, MY_NODE_TYPE)
    
    def publish_event_a(self, target_node_id: str, parameter_1: int, parameter_2: str):
        self.publish(EVENT_A, target_node_id, parameter_1, parameter_2)
    
    def broadcast_event_b(self, parameter_1: bool, parameter_2: list):
        self.broadcast(EVENT_B, parameter_1, parameter_2)
```

### Conflicting metaclasses

If you want to convert a class to an XNode, but also need the class to derive from another class which also has a custom metaclass, one has to combine the metaclasses of both into a common metaclass. In order to do this, xnodes provdides a function for this called _create_xnode_:

```
import ConflictingMetaclassType

from xnodes import create_xnode

MY_NODE_TYPE = "MY_NODE"

class MyNode(create_xnode(ConflictingMetaclassType, MY_NODE_TYPE)):
    
    def __init__():
        super().__init__(parameters_of_conflicting_metaclass_type)
```

Instead of deriving from ConflictingMetaclassType and XNode in the super class list, one can call _create_xnode_ inside the super class list and pass the conflicting class together with the xnode type to combine the metaclasses. In the init of the new class, one now only has to provide the super class init arguments of the conflicting metaclass type.
One example of a conflicting metaclass type are any widgets of the Python Qt bindings. If the goal is to implement a custom QLineEdit and send an XEvent whenever the text changes for example, one has to use the create_xnode function to combine QLineEdit with XNode to resolve this issue.
"""


setup(
    name="xnodes",
    url="https://github.com/newmra/xnodes",
    author="Ralph Neumann",
    maintainer="Ralph Neumann",
    description="Event exchanging nodes framework",
    long_description_content_type="text/markdown",
    long_description=LONG_DESCRIPTION,
    version="v0.0.13-beta",
    packages=["xnodes"],
    license="GNU GENERAL PUBLIC LICENSE 3"
)
