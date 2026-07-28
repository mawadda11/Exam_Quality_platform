import { useMemo, useState } from 'react'
import { Tabs } from '../../components/ui/Tabs'
import type {
  AnalysisResponse,
  RecommendationResponse,
} from '../../types/api'
import { AlignmentCoverageSection } from './AlignmentCoverageSection'
import { FindingsRecommendationsSection } from './FindingsRecommendationsSection'
import { buildLookups } from './lookups'
import { MarksStructureSection } from './MarksStructureSection'
import { OverviewSection } from './OverviewSection'
import { QuestionsSection } from './QuestionsSection'
import { ReportSection } from './ReportSection'
import { ResultResourceState } from './ResultResourceState'
import { ResultsHeader } from './ResultsHeader'
import { RESULTS_SECTIONS, type ResultsSectionId } from './resultSections'
import { useAnalysisResultsData } from './useAnalysisResultsData'
import { useI18n } from '../../i18n/I18nProvider'

interface AnalysisResultsProps {
  analysis: AnalysisResponse
  onReanalysisCreated?: (reanalysis: AnalysisResponse) => void
  section?: ResultsSectionId
  onSectionChange?: (section: ResultsSectionId) => void
}

export function AnalysisResults({
  analysis,
  onReanalysisCreated,
  section: controlledSection,
  onSectionChange,
}: AnalysisResultsProps) {
  const { t } = useI18n()
  const [localSection, setLocalSection] = useState<ResultsSectionId>('overview')
  const section = controlledSection ?? localSection
  const { resources, retryResource, refreshResource } = useAnalysisResultsData(
    analysis.id,
  )

  function handleSectionChange(nextSection: ResultsSectionId): void {
    if (onSectionChange) {
      onSectionChange(nextSection)
    } else {
      setLocalSection(nextSection)
    }
  }

  const lookups = useMemo(
    () =>
      buildLookups(
        resources.clos.status === 'ready' ? resources.clos.data : [],
        resources.topics.status === 'ready' ? resources.topics.data : [],
        resources.questions.status === 'ready' ? resources.questions.data : [],
      ),
    [resources.clos, resources.questions, resources.topics],
  )

  const unavailableLookups = useMemo(() => {
    const unavailable = new Set<'clo' | 'topic' | 'question'>()
    if (resources.clos.status === 'error') unavailable.add('clo')
    if (resources.topics.status === 'error') unavailable.add('topic')
    if (resources.questions.status === 'error') unavailable.add('question')
    return unavailable
  }, [resources.clos.status, resources.questions.status, resources.topics.status])

  const recommendationsByFinding = useMemo(() => {
    const map = new Map<string, RecommendationResponse[]>()
    if (resources.recommendations.status !== 'ready') return map
    for (const recommendation of resources.recommendations.data) {
      const existing = map.get(recommendation.finding_id) ?? []
      existing.push(recommendation)
      map.set(recommendation.finding_id, existing)
    }
    return map
  }, [resources.recommendations])

  const hasAiAssistedFindings =
    resources.findings.status === 'ready' &&
    resources.findings.data.some((finding) => finding.evaluator_type === 'semantic_ai')

  return (
    <div className="analysis-results">
      <ResultsHeader
        analysis={analysis}
        score={resources.score}
        onRetryScore={() => retryResource('score')}
      />

      {hasAiAssistedFindings && (
        <div className="notice ai-advisory-notice">
          {t('This evaluation is advisory and intended to support faculty review. Final academic responsibility remains with the instructor.')}
        </div>
      )}

      <Tabs
        items={RESULTS_SECTIONS.map((item) => ({ ...item, label: t(item.label) }))}
        value={section}
        onValueChange={handleSectionChange}
        ariaLabel={t('Results sections')}
      />

      <div
        className="results-panel"
        role="tabpanel"
        id={`tabpanel-${section}`}
        aria-labelledby={`tab-${section}`}
      >
        {section === 'overview' && (
          <ResultResourceState
            resource={resources.score}
            loadingMessage={t('Loading score summary…')}
            errorTitle={t('Could not load score summary')}
            onRetry={() => retryResource('score')}
          >
            {(score) => (
              <OverviewSection
                analysis={analysis}
                score={score}
                ruleCoverage={resources.ruleCoverage}
                onRetryRuleCoverage={() => retryResource('ruleCoverage')}
                onReanalysisCreated={onReanalysisCreated}
              />
            )}
          </ResultResourceState>
        )}

        {section === 'questions' && (
          <ResultResourceState
            resource={resources.questions}
            loadingMessage={t('Loading extracted questions…')}
            errorTitle={t('Could not load questions')}
            onRetry={() => retryResource('questions')}
          >
            {(questions) => <QuestionsSection questions={questions} />}
          </ResultResourceState>
        )}

        {section === 'alignment-coverage' && (
          <AlignmentCoverageSection
            findings={resources.findings}
            clos={resources.clos}
            topics={resources.topics}
            assessmentRecords={resources.assessmentRecords}
            lookups={lookups}
            unavailableLookups={unavailableLookups}
            onRetry={retryResource}
          />
        )}

        {section === 'marks-structure' && (
          <ResultResourceState
            resource={resources.findings}
            loadingMessage={t('Loading marks and structure findings…')}
            errorTitle={t('Could not load marks and structure findings')}
            onRetry={() => retryResource('findings')}
          >
            {(findings) => (
              <MarksStructureSection
                findings={findings}
                lookups={lookups}
                unavailableLookups={unavailableLookups}
              />
            )}
          </ResultResourceState>
        )}

        {section === 'findings-recommendations' && (
          <ResultResourceState
            resource={resources.findings}
            loadingMessage={t('Loading findings…')}
            errorTitle={t('Could not load findings')}
            onRetry={() => retryResource('findings')}
          >
            {(findings) => (
              <FindingsRecommendationsSection
                findings={findings}
                recommendations={resources.recommendations}
                recommendationsByFinding={recommendationsByFinding}
                lookups={lookups}
                unavailableLookups={unavailableLookups}
                onRetryRecommendations={() => retryResource('recommendations')}
              />
            )}
          </ResultResourceState>
        )}

        {section === 'report' && (
          <ReportSection
            analysisId={analysis.id}
            reports={resources.reports}
            onRetryReports={() => retryResource('reports')}
            onRefreshReports={() => refreshResource('reports')}
          />
        )}
      </div>
    </div>
  )
}
