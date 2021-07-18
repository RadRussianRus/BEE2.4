"""Handles generation for items which are placed as a chain between instances.

This includes Unstationary Scaffolds and Vactubes.
"""
from __future__ import annotations
from typing import Container, Optional, Iterator, TypeVar, Generic

import attr

from precomp import connections
from srctools import Entity, VMF, Matrix, Angle
from precomp.connections import Item

__all__ = ['Node', 'chain']
ConfT = TypeVar('ConfT')


@attr.define
class Node(Generic[ConfT]):
    """Represents a single node in the chain."""
    item: Item
    conf: ConfT
    orient = attr.ib(init=False)
    prev: Optional[Node[ConfT]] = attr.ib(default=None, init=False)
    next: Optional[Node[ConfT]] = attr.ib(default=None, init=False)

    @orient.default
    def _set_orient(self) -> None:
        """Set the orient value."""
        self.orient = Matrix.from_angle(Angle.from_str(self.item.inst['angles']))

    @property
    def inst(self) -> Entity:
        return self.item.inst


def chain(
    vmf: VMF,
    inst_files: dict[str, ConfT],
    allow_loop: bool,
) -> Iterator[list[Node[ConfT]]]:
    """Evaluate the chain of items.

    inst_files maps an instance to the configuration to store.
    Lists of nodes are yielded, for each separate track.
    """
    # Name -> node
    nodes: dict[str, Node[ConfT]] = {}

    for inst in vmf.by_class['func_instance']:
        try:
            conf = inst_files[inst['file'].casefold()]
        except KeyError:
            continue
        name = inst['targetname']
        try:
            nodes[name] = Node(connections.ITEMS[name], conf)
        except KeyError:
            raise ValueError('No item for "{}"?'.format(name)) from None

    # Now compute the links, and check for double-links.
    for name, node in nodes.items():
        has_other_io = False
        for conn in list(node.item.outputs):
            try:
                next_node = nodes[conn.to_item.name]
            except KeyError:
                # Not one of our instances - fine, it's just actual IO.
                has_other_io = True
                continue
            conn.remove()
            if node.next is not None:
                raise ValueError('Item "{}" links to multiple output items!')
            if next_node.prev is not None:
                raise ValueError('Item "{}" links to multiple input items!')
            node.next = next_node
            next_node.prev = node

        # If we don't have real IO, we can delete the antlines automatically.
        if not has_other_io:
            node.item.delete_antlines()

    todo = set(nodes.values())
    while todo:
        # Grab a random node, then go backwards until we find the start.
        # If we return back to this node, it's an infinite loop.
        pop_node = todo.pop()

        if pop_node.prev is None:
            start_node = pop_node
        else:
            start_node = pop_node.prev
            while True:
                if start_node.prev is None:
                    break
                # We've looped back.
                elif start_node is pop_node:
                    if not allow_loop:
                        raise ValueError('Loop in linked items!')
                    break
                start_node = start_node.prev

        node_list = []
        node = start_node
        while True:
            node_list.append(node)
            todo.discard(node)
            if node.next is None:
                break
            node = node.next
            if node is start_node:
                break

        yield node_list
