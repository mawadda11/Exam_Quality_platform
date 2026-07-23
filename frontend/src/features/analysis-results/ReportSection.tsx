/** Honest deferral, not a placeholder that pretends to work: report
 * generation, PDF rendering, and score/recommendation persistence are
 * Milestone 10 scope (docs/IMPLEMENTATION_ROADMAP.md item 10 - "Report
 * generation and revised-exam history"). No report endpoint exists yet
 * (see docs/API_SPECIFICATION.md), so this section says so plainly instead
 * of showing a button that fails or does nothing. */
export function ReportSection() {
  return (
    <div className="report-section">
      <h3>Report</h3>
      <p className="notice">
        Downloadable report generation is not available in this milestone. The Overview,
        Questions, Alignment &amp; Coverage, Marks &amp; Structure, and Findings &amp;
        Recommendations sections above reflect the same evidence and findings a future report
        will use.
      </p>
    </div>
  )
}
