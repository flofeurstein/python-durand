from enum import IntEnum
import logging
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from ..node import Node


log = logging.getLogger(__name__)


class StateEnum(IntEnum):
  INITIALISATION = 0
  STOPPED = 4
  OPERATIONAL = 5
  PRE_OPERATIONAL = 127


class NMTService:
    def __init__(self, node: 'Node'):
        self._node = node
        self._state_callbacks = list()
        
        self.state = None

        node.add_subscription(cob_id=0, callback=self.handle_msg)

        self.set_state(StateEnum.INITIALISATION)
        self.set_state(StateEnum.PRE_OPERATIONAL)

    def handle_msg(self, msg: bytes):
        cs, node_id = msg[:2]

        if node_id not in (0, self._node.node_id):  # 0 is used for broadcast
            return

        if cs == 0x01 and self.state in (StateEnum.PRE_OPERATIONAL, StateEnum.STOPPED):
            self._set_state(StateEnum.OPERATIONAL)  # start node
        elif cs == 0x02 and self.state in (StateEnum.PRE_OPERATIONAL, StateEnum.OPERATIONAL):
            self.set_state(StateEnum.STOPPED)  # stop node
        elif cs == 0x80 and self.state in (StateEnum.OPERATIONAL, StateEnum.STOPPED):
            self.set_state(StateEnum.PRE_OPERATIONAL)  # enter pre-operational
        elif cs in (0x81, 0x82):  # Reset Node or Reset Communication
            self.set_state(StateEnum.INITIALISATION)  
            self.set_state(StateEnum.PRE_OPERATIONAL)
        else:
            log.error('Unknown NMT command specifier 0x%02X', cs)

    def set_state(self, state: StateEnum):
        if state == self.state:
            return

        if state == StateEnum.INITIALISATION:
            # send bootup message
            self._node.adapter.send(0x700 + self._node.node_id, b'\x00')
        
        for callback in self._state_callbacks:
            callback(state)

        self.state = state

    def add_state_callback(self, callback):
        self._state_callbacks.append(callback)
