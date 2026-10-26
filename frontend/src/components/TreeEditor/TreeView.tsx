import { createContext, useContext, useMemo } from "react";
import { Tree } from "react-arborist";
import type { NodeRendererProps } from "react-arborist";

import * as ops from "../../lib/treeOps";
import type { FaultTreeNode, Gate } from "../../types";

interface Callbacks {
  rootId: string;
  attachMode: boolean;
  onPickAttachPoint?: (gateId: string) => void;
  updateDescription: (id: string, description: string) => void;
  updateProbability: (id: string, probability: number | null) => void;
  toggleGateType: (id: string) => void;
  addChild: (parentId: string, kind: "GATE" | "BASIC") => void;
  deleteSubtree: (id: string) => void;
}

const CallbacksContext = createContext<Callbacks | null>(null);

function newBasicEvent(): FaultTreeNode {
  return {
    node_type: "BASIC",
    id: ops.generateId("basic"),
    description: "New basic event",
    probability: null,
    rationale: null,
  };
}

function Node({ node, style, dragHandle }: NodeRendererProps<FaultTreeNode>) {
  const cb = useContext(CallbacksContext);
  if (!cb) return null;

  const item = node.data;
  const isGate = item.node_type === "GATE";

  return (
    <div style={style} ref={dragHandle} className={`tree-row ${isGate ? "tree-row-gate" : "tree-row-basic"}`}>
      {isGate ? (
        <button type="button" className="tree-toggle" onClick={() => node.toggle()}>
          {node.isOpen ? "▾" : "▸"}
        </button>
      ) : (
        <span className="tree-toggle-spacer" />
      )}

      <span className={`badge badge-${isGate ? item.gate_type.toLowerCase() : "basic"}`}>
        {isGate ? item.gate_type : "EVENT"}
      </span>

      <input
        className="tree-description"
        value={item.description}
        onChange={(e) => cb.updateDescription(item.id, e.target.value)}
      />

      {isGate && (
        <button type="button" className="tree-action" onClick={() => cb.toggleGateType(item.id)}>
          switch to {item.gate_type === "AND" ? "OR" : "AND"}
        </button>
      )}

      {!isGate && (
        <input
          className="tree-probability"
          type="number"
          min={0}
          max={1}
          step={0.01}
          placeholder="p unknown"
          value={item.probability ?? ""}
          onChange={(e) =>
            cb.updateProbability(item.id, e.target.value === "" ? null : Number(e.target.value))
          }
        />
      )}

      {isGate && (
        <>
          <button type="button" className="tree-action" onClick={() => cb.addChild(item.id, "GATE")}>
            + gate
          </button>
          <button type="button" className="tree-action" onClick={() => cb.addChild(item.id, "BASIC")}>
            + event
          </button>
        </>
      )}

      {cb.attachMode && isGate && (
        <button
          type="button"
          className="tree-action tree-action-attach"
          onClick={() => cb.onPickAttachPoint?.(item.id)}
        >
          attach here
        </button>
      )}

      {item.id !== cb.rootId && (
        <button type="button" className="tree-action tree-action-delete" onClick={() => cb.deleteSubtree(item.id)}>
          delete
        </button>
      )}
    </div>
  );
}

interface TreeViewProps {
  root: Gate;
  onChange: (newRoot: Gate) => void;
  attachMode: boolean;
  onPickAttachPoint?: (gateId: string) => void;
}

export function TreeView({ root, onChange, attachMode, onPickAttachPoint }: TreeViewProps) {
  const data = useMemo<FaultTreeNode[]>(() => [root], [root]);

  const callbacks = useMemo<Callbacks>(
    () => ({
      rootId: root.id,
      attachMode,
      onPickAttachPoint,
      updateDescription: (id, description) => onChange(ops.updateNode(root, id, (n) => ({ ...n, description }))),
      updateProbability: (id, probability) =>
        onChange(ops.updateNode(root, id, (n) => (n.node_type === "BASIC" ? { ...n, probability } : n))),
      toggleGateType: (id) =>
        onChange(
          ops.updateNode(root, id, (n) =>
            n.node_type === "GATE" ? { ...n, gate_type: n.gate_type === "AND" ? "OR" : "AND" } : n
          )
        ),
      addChild: (parentId, kind) => {
        const node: FaultTreeNode =
          kind === "GATE"
            ? { node_type: "GATE", id: ops.generateId("gate"), gate_type: "OR", description: "New gate", children: [newBasicEvent()] }
            : newBasicEvent();
        onChange(ops.addChild(root, parentId, node));
      },
      deleteSubtree: (id) => {
        if (id !== root.id) onChange(ops.deleteSubtree(root, id));
      },
    }),
    [root, attachMode, onPickAttachPoint, onChange]
  );

  function handleMove({ dragIds, parentId, index }: { dragIds: string[]; parentId: string | null; index: number }) {
    if (!parentId || dragIds.length !== 1 || dragIds[0] === root.id) return;
    onChange(ops.moveNode(root, dragIds[0], parentId, index));
  }

  return (
    <CallbacksContext.Provider value={callbacks}>
      <Tree<FaultTreeNode>
        data={data}
        idAccessor="id"
        childrenAccessor={(d) => (d.node_type === "GATE" ? d.children : null)}
        openByDefault
        width="100%"
        height={480}
        indent={20}
        rowHeight={40}
        disableEdit
        disableMultiSelection
        onMove={handleMove}
        disableDrag={(d) => d.id === root.id}
        disableDrop={({ parentNode, dragNodes }) => {
          if (parentNode.data?.node_type !== "GATE") return true;
          return dragNodes.some((dn) => dn.id === parentNode.id || dn.isAncestorOf(parentNode));
        }}
      >
        {Node}
      </Tree>
    </CallbacksContext.Provider>
  );
}
