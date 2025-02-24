# XNodes (Exchanging nodes)

## About

XNodes is an application framework which provides an event mechanism for unrelated nodes by utilizing a global event
bus. The framework's initial purpose was to establish a lightweight mechanism for exchanging information between UI
widgets and a data model, all without necessitating their mutual awareness. Upon receiving an event which alters the
state of a node, the receiving node can provide an event in return which undoes the made changes. This way an easy to
use but powerful undo/redo mechanism is realized.

## Foreword

This framework is open source and every one is welcome to introduce changes via Pull Requests or to report bugs and
request features by adding a new issue.

In case this framework has been useful to you, and you want to support its development or just want to buy me a coffee,
you can donate via PayPal:

[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/donate/?hosted_button_id=3LUSLWJP6Z7P8)

## Showcase

Practical examples are sometimes the best way to understand a topic. Follow
[this link ](https://github.com/newmra/xnodes-showcase) to see what this framework is capable of and how it may be used
in an application.

## How to use

### Event registration

Before a node is constructed, all events which the node is subscribed to have to be registered beforehand. In order to
register an event, the ID of the event and a description of the parameters of the event have to be provided.
Optionally, a log level can be provided as well, which will be used for logging when the event is published. If no log
level is provided, the default log level is _INFO_.

Parameter descriptions are passed as a set of objects of the dataclass `XEventParameter`. This dataclass has three
attributes, which are:

- The name of the parameter as a string,
- The type of the parameter as a type object and
- A description of the parameter as a string.

The type and the description of a parameter are both optional. Here are some examples:

```
import logging
from xnodes import xcore, XEventParameter

# Registering an event called 'MY_EVENT_1' with one parameter called 'parameter_name' and log level 'INFO'.
xcore.register_event("MY_EVENT_1", {XEventParameter("parameter_name")}, logging.INFO)

# Registering an event called 'MY_EVENT_2' with two parameters called 'parameter_name' of type int and 'parameter_name_2' without any other information.
xcore.register_event("MY_EVENT_2", {XEventParameter("parameter_name_1", int), XEventParameter("parameter_name_2")})

# Registering an event called 'MY_EVENT_3' with one parameter called 'parameter_name' of type int and a description of the parameter.
x_core.register_event("MY_EVENT_3", {XEventParameter("parameter_name", int, "Description of the parameter")})

# Registering an event called 'MY_EVENT_4' with one parameter called 'parameter_name' and a description of the parameter.
x_core.register_event("MY_EVENT_4", {XEventParameter("parameter_name", description="Description of the parameter")})
```

The order in which the parameters are registered is not important, further you can only register a parameter of an event
once.

### Node initialization

To create a node, a class has to inherit from the _XNode_ class. Every node has a node type and when a class inherits
from _XNode_, the type has to be provided to the _XNode_ super class. Purpose of this type is easier identification of
nodes.

```
from xnodes import XNode

MY_NODE_TYPE = "MY_NODE"

class MyNode(XNode):
    
    def __init__():
        XNode.__init__(self, MY_NODE_TYPE)

instance_1 = MyNode()
instance_2 = MyNode()
```

The created instances of MyNode both have unique IDs within the node type MY_NODE. It is also possible to assign a
static ID to a node, but then it is only possible to create one instance of the node. This is done by calling
the `__init__` method of `XNode` with the parameter `is_static` set to `True`:

```
from xnodes import XNode

MY_NODE_TYPE = "MY_NODE"

class MyNode(XNode):
    
    def __init__():
        XNode.__init__(self, MY_NODE_TYPE, is_static=True)

# ID is 'MY_NODE'.
instance_1 = MyNode()

# Would raise an error.
instance_2 = MyNode()
```

Nodes with static IDs are central components in an application and can be contacted by any node by the predefined ID.
If your class inherits from `XNode` and another class, you can only call `super().__init__()` first with the node type,
then optionally with the static flag and then with the init parameters of the other super class.

```
from xnodes import XNode

MY_NODE_TYPE = "MY_NODE"

class OtherSuperClass:

    def __init__(self, parameter_1: int, parameter_2: str):
        ...

class MyNode(XNode):
    
    def __init__():
        XNode.__init__(self, MY_NODE_TYPE, is_static=True, 42, "parameter_2")
```

### Receiving events

In order to receive an event, a node has to implement an event listener function and decorate it with the
_x_event_listener_ decorator function:

```

from xnodes import XNode, x_event_listener

MY_NODE_TYPE = "MY_NODE"
EVENT_A = "EVENT_A"
EVENT_B = "EVENT_B"

class MyNode(XNode):

    def __init__():
        XNode.__init__(self, MY_NODE_TYPE)
    
    @x_event_listener(EVENT_A)
    def handle_event_a(self, parameter_1: int, parameter_2: str):
        pass  # Do something with the event.
    
    @x_event_listener(EVENT_B)
    def handle_event_b(self, parameter_1: bool, parameter_2: list):
        pass  # Do something with the event.

```

The decorator _x_event_listener_ takes as argument the ID of the event which the decorated function is supposed
to handle.

### Publishing events

XNode provides two functions to publish events. The first is the _publish_ function, which delivers one single event to
one single node which is specified by its ID. The second is the _broadcast_ function which delivers an event to every
node which subscribed to the published event.

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

### Main thread necessity

All events published in the xnodes framework are supposed to be published from the main thread. This is due to the
undo/redo mechanism which relies on a sequential order of published events. If an event is published from a different
thread, the undo stack can get corrupted and the undo/redo mechanism will not work as intended. If your application only
runs on the main thread there is no need to worry about this. However, if your application runs on multiple threads, and
you want to publish events from a different thread, you have to add a main thread delegator to the xcore at the start of
your application. A main thread delegator is a class which has to inherit from the _XMainThreadDelegator_ class and
implement the _delegate_events_ method. This method receives a list of events and a flag if the events are undo events.
It then has to make sure that they are

1. delegated to the main thread and
2. that the main thread then calls the __delegate_events_to_main_thread_ of the _xcore_ with the given events.

The main thread delegator has to be passed in the _start_ function of the _xcore_.

### Start of the application

At the start of the application, the _start_ function of the _xcore_ has to be called. This function initializes the
global event bus and accepts a configuration of the framework and the main thread delegator mentioned in the last
chapter. Upon calling the start function, a special event called 'X_CORE_START' is published which nodes can subscribe
to in order to perform initialization tasks.

The configuration of the framework is an object of the dataclass 'XCoreConfiguration', which includes:

1. _log_level_: The log level of the framework. Default is _INFO_. You can register events with an optional log level,
   but those events will only be logged if the log level of the framework is equal or higher than the log level of the
   event. For example if an event has a DEBUG log level, but the framework has an INFO log level, the event will not be
   logged.
2. _log_event_parameters_: Flag if the parameters of an event should be logged. Default is _True_.
3. _log_parameter_type_info_: Flag if the type of the parameters of an event should be logged. Default is _False_.
4. _id_maximum_logging_length_: Maximum length of the ID of an event which is logged. Default is _40_.
   This parameter has to be larger than 10. If an event ID is longer than this value, it will be shortened to
   this value.
5. _maximum_undo_events_: Maximum number of events which are stored in the undo stack. Default is _1000_. If this
   value is negative, there is no limit to the number of events stored in the undo stack.

The configuration has to be set at the beginning of the application and cannot be changed afterward.

### Undo / Redo mechanism

Xnodes provides a simple event based undo / redo mechanism. If a node receives an event which alters its state, it can
provide an event in return which undoes the made changes. If this is consequently done for every event, every change to
the internal data model can be reversed and redone. A node can provide an undo event 
