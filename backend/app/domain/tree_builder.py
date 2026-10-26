"""Converts the LLM's flat node list into a validated nested FaultTree.

The flat schema is a graph via id references (children_ids), so before building the
nested tree we check for cycles and for "shared gates" (a gate referenced as a child
by more than one parent, which would make this a DAG rather than a tree -- the
recursive cut-set/probability algorithms assume a tree). Basic events *may* be
referenced/repeated across branches; only gates must be tree-structured.
"""

from __future__ import annotations

from app.domain.models import BasicEvent, FaultTree, Gate, LLMFaultTreeResponse, TopEvent
from app.domain.tree_validation import TreeValidationError


def build_fault_tree(
    response: LLMFaultTreeResponse, top_event_description: str
) -> tuple[FaultTree, list[str]]:
    nodes_by_id = {n.id: n for n in response.nodes}

    gate_parent_count: dict[str, int] = {}
    for n in response.nodes:
        for child_id in n.children_ids:
            child = nodes_by_id[child_id]
            if child.type == "GATE":
                gate_parent_count[child_id] = gate_parent_count.get(child_id, 0) + 1
    shared = sorted(gid for gid, count in gate_parent_count.items() if count > 1)
    if shared:
        raise TreeValidationError(
            "Gate(s) "
            + ", ".join(shared)
            + " are referenced by more than one parent; shared gates are not supported "
            "(a fault tree must be a tree, not a DAG)"
        )

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n.id: WHITE for n in response.nodes}

    def visit(node_id: str, stack: list[str]) -> None:
        node = nodes_by_id[node_id]
        color[node_id] = GRAY
        for child_id in node.children_ids:
            if color[child_id] == GRAY:
                raise TreeValidationError(
                    "Cycle detected in fault tree: " + " -> ".join(stack + [child_id])
                )
            if color[child_id] == WHITE:
                visit(child_id, stack + [child_id])
        color[node_id] = BLACK

    visit(response.top_event_id, [response.top_event_id])

    def to_domain(node_id: str) -> "Gate | BasicEvent":
        n = nodes_by_id[node_id]
        if n.type == "BASIC":
            return BasicEvent(
                id=n.id, description=n.description, probability=n.probability, rationale=n.rationale
            )
        return Gate(
            id=n.id,
            gate_type=n.gate_type,  # validated non-None for GATE nodes by LLMNode
            description=n.description,
            children=[to_domain(c) for c in n.children_ids],
        )

    root_node = nodes_by_id[response.top_event_id]
    if root_node.type != "GATE":
        raise TreeValidationError("Top event node must be a GATE")

    tree = FaultTree(
        top_event=TopEvent(description=top_event_description),
        root=to_domain(response.top_event_id),
    )

    reachable: set[str] = set()
    stack = [response.top_event_id]
    while stack:
        nid = stack.pop()
        if nid in reachable:
            continue
        reachable.add(nid)
        stack.extend(nodes_by_id[nid].children_ids)
    unreachable = sorted(set(nodes_by_id) - reachable)

    warnings: list[str] = []
    if unreachable:
        warnings.append(
            "Node(s) "
            + ", ".join(unreachable)
            + " were returned by the model but are not reachable from the top event "
            "and were dropped"
        )

    return tree, warnings
