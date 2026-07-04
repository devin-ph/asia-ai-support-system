import type { Citation } from "../api";

interface CitationPanelProps {
  citations: Citation[];
}

export function CitationPanel({ citations }: CitationPanelProps) {
  if (citations.length === 0) {
    return null;
  }

  return (
    <section className="citation-panel" aria-label="Nguồn chính sách">
      <h4>Nguồn chính sách</h4>
      <ul>
        {citations.map((citation) => (
          <li key={`${citation.source}#${citation.section}`}>
            <strong>{citation.title}</strong>
            <span>{citation.section}</span>
            <code>{citation.source}</code>
          </li>
        ))}
      </ul>
    </section>
  );
}
