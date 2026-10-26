export type GateType = "AND" | "OR";
export type Provider = "openai" | "anthropic" | "gemini";
export type ProbabilityMethod = "exact" | "approximate_rare_event" | "unavailable";

export interface BasicEvent {
  node_type: "BASIC";
  id: string;
  description: string;
  probability: number | null;
  rationale: string | null;
}

export interface Gate {
  node_type: "GATE";
  id: string;
  gate_type: GateType;
  description: string;
  children: FaultTreeNode[];
}

export type FaultTreeNode = Gate | BasicEvent;

export interface TopEvent {
  description: string;
}

export interface FaultTree {
  top_event: TopEvent;
  root: Gate;
}

export interface Control {
  id: string;
  description: string;
  target_basic_event_id: string;
  effectiveness: number;
  active: boolean;
  rationale: string | null;
}

export interface LossMagnitude {
  amount: number;
  currency: string;
  time_base: string;
}

export interface RiskQuantification {
  loss_magnitude: LossMagnitude;
  baseline_ale: number | null;
  residual_ale: number | null;
  savings: number | null;
}

export interface ProbabilityResult {
  top_event_probability: number | null;
  method: ProbabilityMethod;
  warnings: string[];
}

export interface CutSet {
  event_ids: string[];
  event_descriptions: string[];
  baseline_probability: number | null;
  residual_probability: number | null;
}

export interface AnalysisResult {
  analysis_id: string;
  top_event: TopEvent;
  fault_tree: FaultTree;
  controls: Control[];
  minimal_cut_sets: CutSet[];
  baseline_probability: ProbabilityResult;
  residual_probability: ProbabilityResult;
  risk_quantification: RiskQuantification | null;
  provider: Provider | null;
  model: string | null;
  created_at: string;
  updated_at: string;
  warnings: string[];
}
