"""
    Copyright (c) 2023 - All rights reserved
    Unauthorized copying of this file, via any medium is strictly prohibited

    File:       main.py
    Created on: 10. Aug.. 2023
    Author:     Ralph Neumann
"""

import logging

from xnodes.xnodes import XNodeBus

EVENT_A = "EVENT_A"
EVENT_B = "EVENT_B"

XNodeBus.add_event(EVENT_A, (int, str))
XNodeBus.add_event(EVENT_B, (int, str), logging.DEBUG)
