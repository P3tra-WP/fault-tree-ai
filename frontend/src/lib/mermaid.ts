import type { FaultTree, FaultTreeNode } from "../types";

function sanitizeLabel(text: string): string {
  return text.replace(/"/g, "'").slice(0, 80);
}

function renderNode(node: FaultTreeNode, lines: string[]): void {
  if (node.node_type === "BASIC") {
    const prob = node.probability !== null ? ` (p=${node.probability.toFixed(3)})` : "";
    lines.push(`  ${node.id}["${sanitizeLabel(node.description)}${prob}"]`);
    return;
  }

  const label = sanitizeLabel(`${node.gate_type}: ${node.description}`);
  const shape = node.gate_type === "AND" ? `{{"${label}"}}` : `(("${label}"))`;
  lines.push(`  ${node.id}${shape}`);
  for (const child of node.children) {
    lines.push(`  ${node.id} --> ${child.id}`);
    renderNode(child, lines);
  }
}

export function faultTreeToMermaid(tree: FaultTree): string {
  const lines: string[] = ["flowchart TD"];
  renderNode(tree.root, lines);
  return lines.join("\n");
}
