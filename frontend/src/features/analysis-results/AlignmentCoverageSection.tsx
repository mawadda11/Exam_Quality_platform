import { Card } from '../../components/ui/Card'
import { ResponsiveTable } from '../../components/ui/ResponsiveTable'
import { useI18n } from '../../i18n/I18nProvider'
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
import type { ResultResource, ResultsResourceKey } from './useAnalysisResultsData'

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
  const { t } = useI18n()
  return (
    <div className="alignment-coverage-section results-section-stack">
      <div className="results-section-heading">
        <div>
          <h2>{t('Alignment & Coverage')}</h2>
          <p>{t('Existing governed findings and source-faithful entities extracted from the TP-153.')}</p>
        </div>
      </div>

      <Card as="section" className="results-content-card">
        <h3>{t('Alignment and coverage findings')}</h3>
        <ResultResourceState
          resource={findings}
          loadingMessage={t('Loading alignment and coverage findings…')}
          errorTitle={t('Could not load alignment and coverage findings')}
          onRetry={() => onRetry('findings')}
        >
          {(loadedFindings) => {
            const relevant = loadedFindings.filter((finding) =>
              ALIGNMENT_COVERAGE_DIMENSIONS.has(finding.dimension),
            )
            return relevant.length === 0 ? (
              <p className="results-empty-state">{t('No alignment or coverage findings are available.')}</p>
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
          <h3>{t('Extracted CLOs')}</h3>
          <ResultResourceState
            resource={clos}
            loadingMessage={t('Loading extracted CLOs…')}
            errorTitle={t('Could not load extracted CLOs')}
            onRetry={() => onRetry('clos')}
          >
            {(loadedClos) =>
              loadedClos.length === 0 ? (
                <p className="results-empty-state">{t('No CLOs were extracted from the TP-153.')}</p>
              ) : (
                <ul className="source-evidence-list">
                  {loadedClos.map((clo) => (
                    <li key={clo.id}>
                      <strong><bdi>{clo.code}</bdi></strong>
                      <span dir="auto">{clo.text}</span>
                      <span>{t('TP-153 page')} {clo.page_number}</span>
                    </li>
                  ))}
                </ul>
              )
            }
          </ResultResourceState>
        </Card>

        <Card as="section" className="results-content-card">
          <h3>{t('Extracted topics')}</h3>
          <ResultResourceState
            resource={topics}
            loadingMessage={t('Loading extracted topics…')}
            errorTitle={t('Could not load extracted topics')}
            onRetry={() => onRetry('topics')}
          >
            {(loadedTopics) =>
              loadedTopics.length === 0 ? (
                <p className="results-empty-state">{t('No topics were extracted from the TP-153.')}</p>
              ) : (
                <ul className="source-evidence-list">
                  {loadedTopics.map((topic) => (
                    <li key={topic.id}>
                      <strong><bdi>{topic.code ?? t('No code')}</bdi></strong>
                      <span dir="auto">{topic.text}</span>
                      <span>{t('TP-153 page')} {topic.page_number}</span>
                    </li>
                  ))}
                </ul>
              )
            }
          </ResultResourceState>
        </Card>
      </div>

      <Card as="section" className="results-content-card">
        <h3>{t('Extracted assessment records')}</h3>
        <p>{t('These records are displayed as source evidence only. No mapping or consistency conclusion is inferred here.')}</p>
        <ResultResourceState
          resource={assessmentRecords}
          loadingMessage={t('Loading extracted assessment records…')}
          errorTitle={t('Could not load extracted assessment records')}
          onRetry={() => onRetry('assessmentRecords')}
        >
          {(records) =>
            records.length === 0 ? (
              <p className="results-empty-state">{t('No assessment records were extracted from the TP-153.')}</p>
            ) : (
              <ResponsiveTable caption={t('Extracted assessment records')}>
                <thead>
                  <tr>
                    <th>{t('Method')}</th>
                    <th>{t('Activity')}</th>
                    <th>{t('Percentage')}</th>
                    <th>{t('Page')}</th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((record) => (
                    <tr key={record.id}>
                      <td><span dir="auto">{record.method}</span></td>
                      <td><span dir="auto">{record.activity ?? '—'}</span></td>
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
