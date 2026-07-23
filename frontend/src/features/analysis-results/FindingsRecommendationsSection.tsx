import type { FindingResponse, RecommendationResponse } from '../../types/api'
import { FindingCard } from './FindingCard'
import type { EvidenceLookups } from './lookups'

interface FindingsRecommendationsSectionProps {
  findings: FindingResponse[]
  recommendationsByFinding: Map<string, RecommendationResponse[]>
  lookups: EvidenceLookups
}

export function FindingsRecommendationsSection({
  findings,
  recommendationsByFinding,
  lookups,
}: FindingsRecommendationsSectionProps) {
  // SCORING_POLICY.md: "Not Verified results must remain visible even
  // though excluded from the denominator" - called out separately here as
  // the PRD's "Missing Evidence" sub-section, using each Finding's own
  // explanation (never a fabricated summary) to say what's missing.
  const missingEvidence = findings.filter((finding) => finding.status === 'Not Verified')

  return (
    <div className="findings-recommendations-section">
      <h3>Findings & Recommendations</h3>

      {missingEvidence.length > 0 && (
        <div className="missing-evidence-panel">
          <h4>Missing Evidence ({missingEvidence.length})</h4>
          <p>
            These are excluded from the score because required evidence was missing, unreadable,
            or insufficient - not because the exam failed the requirement.
          </p>
          <ul>
            {missingEvidence.map((finding) => (
              <li key={finding.id}>
                <strong>{finding.requirement_name}</strong>: {finding.explanation}
              </li>
            ))}
          </ul>
        </div>
      )}

      {findings.length === 0 ? (
        <p className="notice">Findings are not available yet.</p>
      ) : (
        <ul className="finding-list">
          {findings.map((finding) => (
            <FindingCard
              key={finding.id}
              finding={finding}
              lookups={lookups}
              recommendations={recommendationsByFinding.get(finding.id)}
            />
          ))}
        </ul>
      )}
    </div>
  )
}
