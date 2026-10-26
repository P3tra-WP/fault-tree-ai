import { useState } from "react";

import { AttachPointPicker } from "./components/AttachPointPicker";
import { ControlsPanel } from "./components/ControlsPanel";
import { CutSetsList } from "./components/CutSetsList";
import { ExportButtons } from "./components/ExportButtons";
import { FaultTreeDiagram } from "./components/FaultTreeDiagram";
import { GenerateStep } from "./components/GenerateStep";
import { ImportPanel } from "./components/ImportPanel";
import { RiskQuantificationPanel } from "./components/RiskQuantificationPanel";
import { TopEventProbability } from "./components/TopEventProbability";
import { RawJsonEditor } from "./components/TreeEditor/RawJsonEditor";
import { TreeView } from "./components/TreeEditor/TreeView";
import {
  createAnalysis,
  createAnalysisFromImport,
  importIntoAnalysis,
  updateAnalysis,
} from "./lib/api";
import { MODELS } from "./components/ProviderConfig";
import type { AnalysisResult, Control, FaultTree, LossMagnitude, Provider } from "./types";

type Step = "setup" | "editing";
type View = "tree" | "json";

function deepEqual(a: unknown, b: unknown): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

export default function App() {
  const [step, setStep] = useState<Step>("setup");

  // Setup form state.
  const [threatModelMarkdown, setThreatModelMarkdown] = useState("");
  const [topEvent, setTopEvent] = useState("");
  const [provider, setProvider] = useState<Provider>("anthropic");
  const [model, setModel] = useState(MODELS.anthropic[0]);
  const [apiKey, setApiKey] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);

  // Editing state: `analysis` is the last result computed by the backend; the draft
  // fields are the working copy the user is editing client-side until "Recompute".
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [draftTree, setDraftTree] = useState<FaultTree | null>(null);
  const [draftControls, setDraftControls] = useState<Control[]>([]);
  const [draftLossMagnitude, setDraftLossMagnitude] = useState<LossMagnitude | null>(null);
  const [isRecomputing, setIsRecomputing] = useState(false);
  const [recomputeError, setRecomputeError] = useState<string | null>(null);

  const [view, setView] = useState<View>("tree");
  const [attachMode, setAttachMode] = useState(false);
  const [pendingImportTree, setPendingImportTree] = useState<FaultTree | null>(null);

  function syncDraftFrom(result: AnalysisResult) {
    setAnalysis(result);
    setDraftTree(result.fault_tree);
    setDraftControls(result.controls);
    setDraftLossMagnitude(result.risk_quantification?.loss_magnitude ?? null);
  }

  function handleProviderChange(p: Provider) {
    setProvider(p);
    setModel(MODELS[p][0]);
  }

  async function handleGenerate() {
    setIsGenerating(true);
    setGenerateError(null);
    try {
      const result = await createAnalysis({
        provider,
        api_key: apiKey,
        model,
        top_event: topEvent,
        threat_model_markdown: threatModelMarkdown,
      });
      syncDraftFrom(result);
      setStep("editing");
    } catch (e) {
      setGenerateError(e instanceof Error ? e.message : "Failed to generate fault tree");
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleCreateFromImport(tree: FaultTree) {
    setGenerateError(null);
    try {
      const result = await createAnalysisFromImport(tree);
      syncDraftFrom(result);
      setStep("editing");
    } catch (e) {
      setGenerateError(e instanceof Error ? e.message : "Failed to import fault tree");
    }
  }

  async function handleRecompute() {
    if (!analysis || !draftTree) return;
    setIsRecomputing(true);
    setRecomputeError(null);
    try {
      const result = await updateAnalysis(analysis.analysis_id, {
        fault_tree: draftTree,
        controls: draftControls,
        loss_magnitude: draftLossMagnitude,
      });
      syncDraftFrom(result);
    } catch (e) {
      setRecomputeError(e instanceof Error ? e.message : "Failed to recompute");
    } finally {
      setIsRecomputing(false);
    }
  }

  async function handleReplaceImport(tree: FaultTree) {
    if (!analysis) return;
    setRecomputeError(null);
    try {
      const result = await importIntoAnalysis(analysis.analysis_id, { fault_tree: tree, mode: "replace" });
      syncDraftFrom(result);
    } catch (e) {
      setRecomputeError(e instanceof Error ? e.message : "Failed to replace tree");
    }
  }

  function handleStartMerge(tree: FaultTree) {
    setPendingImportTree(tree);
    setAttachMode(true);
  }

  async function handlePickAttachPoint(gateId: string) {
    if (!analysis || !pendingImportTree) return;
    setRecomputeError(null);
    try {
      const result = await importIntoAnalysis(analysis.analysis_id, {
        fault_tree: pendingImportTree,
        mode: "merge",
        attach_gate_id: gateId,
      });
      syncDraftFrom(result);
    } catch (e) {
      setRecomputeError(e instanceof Error ? e.message : "Failed to merge imported tree");
    } finally {
      setAttachMode(false);
      setPendingImportTree(null);
    }
  }

  function handleReset() {
    setStep("setup");
    setAnalysis(null);
    setDraftTree(null);
    setDraftControls([]);
    setDraftLossMagnitude(null);
    setApiKey("");
    setAttachMode(false);
    setPendingImportTree(null);
    setGenerateError(null);
    setRecomputeError(null);
  }

  if (step === "setup" || !analysis || !draftTree) {
    return (
      <GenerateStep
        threatModelMarkdown={threatModelMarkdown}
        onThreatModelChange={setThreatModelMarkdown}
        topEvent={topEvent}
        onTopEventChange={setTopEvent}
        provider={provider}
        onProviderChange={handleProviderChange}
        model={model}
        onModelChange={setModel}
        apiKey={apiKey}
        onApiKeyChange={setApiKey}
        isGenerating={isGenerating}
        errorMessage={generateError}
        onGenerate={handleGenerate}
        onImport={handleCreateFromImport}
      />
    );
  }

  const hasUnsavedChanges =
    !deepEqual(draftTree, analysis.fault_tree) ||
    !deepEqual(draftControls, analysis.controls) ||
    !deepEqual(draftLossMagnitude, analysis.risk_quantification?.loss_magnitude ?? null);
  const showResidual = draftControls.some((c) => c.active);

  return (
    <div className="app-editing">
      <header className="app-header">
        <h1>{analysis.top_event.description}</h1>
        <button type="button" onClick={handleReset}>
          Start over
        </button>
      </header>

      {analysis.warnings.length > 0 && (
        <div className="warnings-box">
          {analysis.warnings.map((w, i) => (
            <p key={i} className="warning-text">
              {w}
            </p>
          ))}
        </div>
      )}

      <section className="tree-section">
        <div className="tree-section-header">
          <div className="view-toggle">
            <button type="button" disabled={view === "tree"} onClick={() => setView("tree")}>
              Tree editor
            </button>
            <button type="button" disabled={view === "json"} onClick={() => setView("json")}>
              Raw JSON
            </button>
          </div>
          <button type="button" onClick={handleRecompute} disabled={isRecomputing || !hasUnsavedChanges}>
            {isRecomputing ? "Recomputing…" : hasUnsavedChanges ? "Recompute" : "Up to date"}
          </button>
        </div>

        {recomputeError && <p className="error-text">{recomputeError}</p>}

        {attachMode && <AttachPointPicker onCancel={() => { setAttachMode(false); setPendingImportTree(null); }} />}

        {view === "tree" ? (
          <TreeView
            root={draftTree.root}
            onChange={(root) => setDraftTree({ ...draftTree, root })}
            attachMode={attachMode}
            onPickAttachPoint={handlePickAttachPoint}
          />
        ) : (
          <RawJsonEditor key={analysis.updated_at} faultTree={draftTree} onApply={setDraftTree} />
        )}

        <FaultTreeDiagram faultTree={draftTree} />
      </section>

      <section className="controls-section">
        <ControlsPanel root={draftTree.root} controls={draftControls} onChange={setDraftControls} />
      </section>

      <section className="results-section">
        <TopEventProbability
          baseline={analysis.baseline_probability}
          residual={analysis.residual_probability}
          showResidual={showResidual}
        />
        <CutSetsList cutSets={analysis.minimal_cut_sets} showResidual={showResidual} />
        <RiskQuantificationPanel
          lossMagnitude={draftLossMagnitude}
          riskQuantification={analysis.risk_quantification}
          onChange={setDraftLossMagnitude}
        />
      </section>

      <section className="import-section">
        <ImportPanel
          hasExistingAnalysis
          onReplace={handleReplaceImport}
          onStartMerge={handleStartMerge}
        />
      </section>

      <ExportButtons analysisId={analysis.analysis_id} />
    </div>
  );
}
