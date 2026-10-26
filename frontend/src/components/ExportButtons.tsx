import { exportUrl } from "../lib/api";

interface ExportButtonsProps {
  analysisId: string;
}

export function ExportButtons({ analysisId }: ExportButtonsProps) {
  return (
    <div className="export-buttons">
      <a href={exportUrl(analysisId, "json")} download>
        Export JSON
      </a>
      <a href={exportUrl(analysisId, "markdown")} download>
        Export Markdown
      </a>
    </div>
  );
}
