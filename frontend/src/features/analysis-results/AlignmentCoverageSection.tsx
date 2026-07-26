import { Card } from '../../components/ui/Card'
import { ResponsiveTable } from '../../components/ui/ResponsiveTable'
import type {
  AssessmentRecordResponse,
  CloResponse,
  FindingResponse,
  TopicResponse,
} from '../../types/api'
import { ALIGNMENT_COVERAGE_DIMENSIONS } from './dimensions'
import type { EvidenceLookupKind } from './EvidenceDrillDown'
import { FindingCard } from './FindingCard'
import type { EvidenceLookups } from './lookups'
import { ResultResourceState } from './ResultResourceState'
import type {
  ResultResource,
  ResultsResourceKey,
} from './useAnalysisResultsData'

interface AlignmentCoverageSectionProps {
  findings: ResultResource<FindingResponse[]>
  clos: ResultResource<CloResponse[]>
  topics: ResultResource<TopicResponse[]>
  assessmentRecords: ResultResource<AssessmentRecordResponse[]>
  lookups: EvidenceLookups
  unavailableLookups: ReadonlySet<EvidenceLookupKind>
  onRetry: (resource: ResultsResourceKey) => void
}

export function AlignmentCoverageSection({
  findings,
  clos,
  topics,
  assessmentRecords,
  lookups,
  unavailableLookups,
  onRetry,
}: AlignmentCoverageSectionProps) {
  return (
    <div className="alignment-coverage-section results-section-stack">
      <div className="results-section-heading">
        <div>
          <h2>Alignment &amp; Coverage</h2>
          <p>
            Existing governed findings and source-faithful entities extracted from the TP-153.
          </p>
        </div>
      </div>

      <Card as="section" className="results-content-card">
        <h3>Alignment and coverage findings</h3>
        <ResultResourceState
          resource={findings}
          loadingMessage="Loading alignment and coverage findings…"
          errorTitle="Could not load alignment and coverage findings"
          onRetry={() => onRetry('findings')}
        >
          {(loadedFindings) => {
            const relevant = loadedFindings.filter((finding) =>
              ALIGNMENT_COVERAGE_DIMENSIONS.has(finding.dimension),
            )
            return relevant.length === 0 ? (
              <p className="results-empty-state">
                No alignment or coverage findings are available.
              </p>
            ) : (
              <ul className="finding-list">
                {relevant.map((finding) => (
                  <FindingCard
                    key={finding.id}
                    finding={finding}
                    lookups={lookups}
                    unavailableLookups={unavailableLookups}
                  />
                ))}
              </ul>
            )
          }}
        </ResultResourceState>
      </Card>

      <div className="alignment-source-grid">
        <Card as="section" className="results-content-card">
          <h3>Extracted CLOs</h3>
          <ResultResourceState
            resource={clos}
            loadingMessage="Loading extracted CLOs…"
            errorTitle="Could not load extracted CLOs"
            onRetry={() => onRetry('clos')}
          >
            {(loadedClos) =>
              loadedClos.length === 0 ? (
                <p className="results-empty-state">
                  No CLOs were extracted from the TP-153.
                </p>
              ) : (
                <ul className="source-evidence-list">
                  {loadedClos.map((clo) => (
                    <li key={clo.id}>
                      <strong>
                        <bdi>{clo.code}</bdi>
                      </strong>
                      <span dir="auto">{clo.text}</span>
                      <span>TP-153 page {clo.page_number}</span>
                    </li>
                  ))}
                </ul>
              )
            }
          </ResultResourceState>
        </Card>

        <Card as="section" className="results-content-card">
          <h3>Extracted topics</h3>
          <ResultResourceState
            resource={topics}
            loadingMessage="Loading extracted topics…"
            errorTitle="Could not load extracted topics"
            onRetry={() => onRetry('topics')}
          >
            {(loadedTopics) =>
              loadedTopics.length === 0 ? (
                <p className="results-empty-state">
                  No topics were extracted from the TP-153.
                </p>
              ) : (
                <ul className="source-evidence-list">
                  {loadedTopics.map((topic) => (
                    <li key={topic.id}>
                      <strong>
                        <bdi>{topic.code ?? 'No code'}</bdi>
                      </strong>
                      <span dir="auto">{topic.text}</span>
                      <span>TP-153 page {topic.page_number}</span>
                    </li>
                  ))}
                </ul>
              )
            }
          </ResultResourceState>
        </Card>
      </div>

      <Card as="section" className="results-content-card">
        <h3>Extracted assessment records</h3>
        <p>
          These records are displayed as source evidence only. No mapping or consistency
          conclusion is inferred here.
        </p>
        <ResultResourceState
          resource={assessmentRecords}
          loadingMessage="Loading extracted assessment records…"
          errorTitle="Could not load extracted assessment records"
          onRetry={() => onRetry('assessmentRecords')}
        >
          {(records) =>
            records.length === 0 ? (
              <p className="results-empty-state">
                No assessment records were extracted from the TP-153.
              </p>
            ) : (
              <ResponsiveTable caption="Extracted assessment records">
                <thead>
                  <tr>
                    <th>Method</th>
                    <th>Activity</th>
                    <th>Percentage</th>
                    <th>Page</th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((record) => (
                    <tr key={record.id}>
                      <td>
                        <span dir="auto">{record.method}</span>
                      </td>
                      <td>
                        <span dir="auto">{record.activity ?? '—'}</span>
                      </td>
                      <td>{record.percentage === null ? '—' : `${record.percentage}%`}</td>
                      <td>{record.page_number}</td>
                    </tr>
                  ))}
                </tbody>
              </ResponsiveTable>
            )
          }
        </ResultResourceState>
      </Card>
    </div>
  )
}
