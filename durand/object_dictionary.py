from dataclasses import dataclass, field
from collections import defaultdict
from typing import Any, Dict, List, Tuple, Callable, Union
from inspect import ismethod, getmembers

from .datatypes import DatatypeEnum


@dataclass(frozen=True)
class Object:
    index: int
    type: int
    name: str
    object_type: int


@dataclass
class Array(Object):
    type: int = 8
    fields: list[Variable] = field(default_factory=list)

    def __getitem__(self, subindex):
        return self.fields[subindex]


@dataclass(frozen=True)
class Variable:
    index: int
    subindex: int
    datatype: DatatypeEnum
    access: str
    default: Any = 0
    factor: float = 1
    minimum: float = None
    maximum: float = None

    def __post_init__(self):
        if not 0 <= self.index <= 0xFFFF:
            raise ValueError('Index has to UINT16')
        if not 0 <= self.subindex <= 255:
            raise ValueError('Subindex has to be UINT8')
        if self.datatype not in DatatypeEnum:
            raise ValueError('Unsupported datatype')
        if self.access not in ('rw', 'ro', 'wo', 'const'):
            raise ValueError('Invalid access type')

    @property
    def multiplexor(self):
        return (self.index, self.subindex)

    @property
    def is_writeable(self):
        return self.access in ('wo', 'rw')

    @property
    def is_readable(self):
        return self.access in ('ro', 'rw', 'const')


class ObjectDictionary:
    def __init__(self):
        self._variables: Dict[Tuple[int, int], Variable] = dict()
        self._data: Dict[Variable, Any] = dict()

        self._validate_callbacks: Dict[Variable, List[Callable]] = \
            defaultdict(list)
        self._update_callbacks: Dict[Variable, List[Callable]] = \
            defaultdict(list)
        self._read_callbacks: Dict[Variable, Callable] = dict()

    def add_object(self, variable: Variable):
        self._variables[variable.multiplexor] = variable

        if variable.subindex == 0:
            return

        if (variable.index, 0) in self._variables:
            largest_subindex = self._variables[(variable.index, 0)]
        else:
            largest_subindex = Variable(
                index=variable.index, subindex=0,
                datatype=DatatypeEnum.UNSIGNED8, access='const')

            self._variables[(variable.index, 0)] = largest_subindex

        value = max(self._data.get(largest_subindex, 0),  variable.subindex)
        self._data[largest_subindex] = value

    def lookup(self, index: int, subindex: int = 0) -> Variable:
        return self._variables[(index, subindex)]

    def write(self, variable: Variable, value: Any):
        self._data[variable] = value

        if variable not in self._update_callbacks:
            return

        for callback in self._update_callbacks[variable]:
            callback(value)

    def add_validate_callback(self, variable: Variable, callback):
        self._validate_callbacks[variable].append(callback)

    def remove_validate_callback(self, variable: Variable, callback):
        self._validate_callbacks[variable].remove(callback)

    def add_update_callback(self, variable: Variable, callback):
        self._update_callbacks[variable].append(callback)

    def remove_update_callback(self, variable: Variable, callback):
        self._update_callbacks[variable].remove(callback)

    def read(self, variable: Variable):
        if variable in self._read_callbacks:
            return self._read_callbacks[variable]()

        return self._data[variable]

    def set_read_callback(self, variable: Variable, callback) -> None:
        self._read_callbacks[variable] = callback