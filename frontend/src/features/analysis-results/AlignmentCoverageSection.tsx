import type { CloResponse, FindingResponse, TopicResponse } from '../../types/api'
import { ALIGNMENT_COVERAGE_DIMENSIONS } from './dimensions'
import { FindingCard } from './FindingCard'
import type { EvidenceLookups } from './lookups'

interface AlignmentCoverageSectionProps {
  findings: FindingResponse[]
  clos: CloResponse[]
  topics: TopicResponse[]
  lookups: EvidenceLookups
}

export function AlignmentCoverageSection({
  findings,
  clos,
  topics,
  lookups,
}: AlignmentCoverageSectionProps) {
  const relevant = findings.filter((finding) => ALIGNMENT_COVERAGE_DIMENSIONS.has(finding.dimension))

  return (
    <div className="alignment-coverage-section">
      <h3>Alignment & Coverage</h3>

      {relevant.length === 0 ? (
        <p className="notice">No alignment or coverage findings are available yet.</p>
      ) : (
        <ul className="finding-list">
          {relevant.map((finding) => (
            <FindingCard key={finding.id} finding={finding} lookups={lookups} />
          ))}
        </ul>
      )}

      <div className="reference-data-columns">
        <div>
          <h4>Course Learning Outcomes ({clos.length})</h4>
          {clos.length === 0 ? (
            <p className="notice">No CLOs were extracted from the TP-153.</p>
          ) : (
            <ul className="code-reference-list">
              {clos.map((clo) => (
                <li key={clo.id}>
                  <strong>{clo.code}</strong> {clo.text}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h4>Course Topics ({topics.length})</h4>
          {topics.length === 0 ? (
            <p className="notice">No topics were extracted from the TP-153.</p>
          ) : (
            <ul className="code-reference-list">
              {topics.map((topic) => (
                <li key={topic.id}>
                  <strong>{topic.code ?? '—'}</strong> {topic.text}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
