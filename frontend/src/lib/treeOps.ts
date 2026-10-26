/**
 * Immutable operations on a nested FaultTree, used by the interactive tree editor.
 *
 * Known v0 limitation: a basic-event id that is legitimately repeated across branches
 * (valid FTA -- a shared root cause) is only addressed as its *first* occurrence in
 * document order by update/remove here, since the visual tree editor's row identity
 * is keyed by domain id. Use the raw JSON editor for full control over repeated-id
 * scenarios.
 */

import type { FaultTreeNode, Gate } from "../types";

export function isGate(node: FaultTreeNode): node is Gate {
  return node.node_type === "GATE";
}

export function findNode(root: FaultTreeNode, id: string): FaultTreeNode | null {
  if (root.id === id) return root;
  if (isGate(root)) {
    for (const c of root.children) {
      const found = findNode(c, id);
      if (found) return found;
    }
  }
  return null;
}

export function updateNode(
  root: Gate,
  id: string,
  updater: (node: FaultTreeNode) => FaultTreeNode
): Gate {
  let done = false;

  function recurse(node: FaultTreeNode): FaultTreeNode {
    if (done) return node;
    let next = node;
    if (node.id === id) {
      next = updater(node);
      done = true;
    }
    if (next.node_type === "GATE") {
      return { ...next, children: next.children.map(recurse) };
    }
    return next;
  }

  return recurse(root) as Gate;
}

export function removeNode(root: Gate, id: string): { root: Gate; removed: FaultTreeNode | null } {
  let removed: FaultTreeNode | null = null;

  function recurse(node: FaultTreeNode): FaultTreeNode {
    if (node.node_type !== "GATE" || removed) return node;
    const newChildren: FaultTreeNode[] = [];
    for (const c of node.children) {
      if (!removed && c.id === id) {
        removed = c;
        continue;
      }
      newChildren.push(recurse(c));
    }
    return { ...node, children: newChildren };
  }

  const newRoot = recurse(root) as Gate;
  return { root: newRoot, removed };
}

export function insertChild(root: Gate, parentId: string, node: FaultTreeNode, index: number): Gate {
  function recurse(n: FaultTreeNode): FaultTreeNode {
    if (n.node_type !== "GATE") return n;
    if (n.id === parentId) {
      const children = [...n.children];
      const clampedIndex = Math.max(0, Math.min(index, children.length));
      children.splice(clampedIndex, 0, node);
      return { ...n, children };
    }
    return { ...n, children: n.children.map(recurse) };
  }
  return recurse(root) as Gate;
}

export function addChild(root: Gate, parentId: string, node: FaultTreeNode): Gate {
  return insertChild(root, parentId, node, Number.MAX_SAFE_INTEGER);
}

export function deleteSubtree(root: Gate, id: string): Gate {
  return removeNode(root, id).root;
}

export function moveNode(root: Gate, nodeId: string, newParentId: string, index: number): Gate {
  const { root: withoutNode, removed } = removeNode(root, nodeId);
  if (!removed) return root;
  return insertChild(withoutNode, newParentId, removed, index);
}

let nextIdCounter = 0;
export function generateId(prefix: string): string {
  nextIdCounter += 1;
  return `${prefix}_${Date.now().toString(36)}_${nextIdCounter}`;
}
