"""
xnodes: Exchange nodes framework
        Simplistic event framework which enables unrelated nodes to exchange information, alter each other states and
        provides the possibility to undo made changes.

Author: Ralph Neumann (@newmra)
"""

import logging
from dataclasses import dataclass
from typing import Set, Union, Tuple


@dataclass(frozen=True, eq=True, order=True)
class XEventParameter:
    """
    Data class for an XEvent parameter.
    """
    name: str
    type: type or None = None
    description: str = ""


@dataclass
class XEventDescription:
    """
    Description of an event which contains the parameters and the log level.
    """
    parameters: Set[Union[Tuple[str], XEventParameter]] = frozenset()
    log_level: int = logging.INFO
