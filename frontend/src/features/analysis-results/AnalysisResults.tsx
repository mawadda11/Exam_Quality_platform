import { useMemo, useState, type ReactNode } from 'react'
import { Tabs } from '../../components/ui/Tabs'
import { PageState } from '../../components/ui/PageState'
import { Button } from '../../components/ui/Button'
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
import { StructuredEvidenceSection } from './StructuredEvidenceSection'
import { ReportSection } from './ReportSection'
import { ResultResourceState } from './ResultResourceState'
import { ResultsHeader } from './ResultsHeader'
import { RESULTS_SECTIONS, type ResultsSectionId } from './resultSections'
import { useAnalysisResultsData } from './useAnalysisResultsData'
import { useI18n } from '../../i18n/I18nProvider'


function QuestionEvidenceGate({
  resource,
  onRetry,
  children,
}: {
  resource: ReturnType<typeof useAnalysisResultsData>['resources']['questions']
  onRetry: () => void
  children: ReactNode
}) {
  const { t } = useI18n()
  if (resource.status === 'loading') {
    return (
      <PageState
        state="loading"
        title={t('Checking confirmed question evidence')}
        message={t('Academic results are shown only after confirmed questions are available.')}
      />
    )
  }
  if (resource.status === 'error') {
    return (
      <PageState
        state="error"
        title={t('Analysis incomplete')}
        message={t('Confirmed question evidence could not be loaded, so academic results and the score are hidden.')}
        action={<Button variant="secondary" onClick={onRetry}>{t('Try again')}</Button>}
      />
    )
  }
  if (resource.data.length === 0) {
    return (
      <PageState
        state="empty"
        title={t('Insufficient Evidence')}
        message={t('No confirmed questions are available. Return to extraction review before relying on academic results.')}
      />
    )
  }
  return <>{children}</>
}

interface AnalysisResultsProps {
  analysis: AnalysisResponse
  section?: ResultsSectionId
  onSectionChange?: (section: ResultsSectionId) => void
}

export function AnalysisResults({
  analysis,
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
        questions={resources.questions}
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
          <QuestionEvidenceGate
            resource={resources.questions}
            onRetry={() => retryResource('questions')}
          >
            <ResultResourceState
              resource={resources.score}
              loadingMessage={t('Loading score summary…')}
              errorTitle={t('Could not load score summary')}
              onRetry={() => retryResource('score')}
            >
              {(score) => (
                <OverviewSection
                  score={score}
                  ruleCoverage={resources.ruleCoverage}
                  onRetryRuleCoverage={() => retryResource('ruleCoverage')}
                />
              )}
            </ResultResourceState>
          </QuestionEvidenceGate>
        )}

        {section === 'questions' && (
          <ResultResourceState
            resource={resources.questions}
            loadingMessage={t('Loading extracted questions…')}
            errorTitle={t('Could not load questions')}
            onRetry={() => retryResource('questions')}
          >
            {(questions) => (
              <QuestionsSection
                questions={questions}
                findings={resources.findings}
              />
            )}
          </ResultResourceState>
        )}

        {section === 'alignment-coverage' && (
          <QuestionEvidenceGate resource={resources.questions} onRetry={() => retryResource('questions')}>
            <AlignmentCoverageSection
              findings={resources.findings}
              questions={resources.questions}
              clos={resources.clos}
              topics={resources.topics}
              onRetry={retryResource}
            />
          </QuestionEvidenceGate>
        )}

        {section === 'marks-structure' && (
          <QuestionEvidenceGate resource={resources.questions} onRetry={() => retryResource('questions')}>
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
          </QuestionEvidenceGate>
        )}

        {section === 'supporting-evidence' && (
          <QuestionEvidenceGate resource={resources.questions} onRetry={() => retryResource('questions')}>
            <StructuredEvidenceSection analysisId={analysis.id} />
          </QuestionEvidenceGate>
        )}

        {section === 'findings-recommendations' && (
          <QuestionEvidenceGate resource={resources.questions} onRetry={() => retryResource('questions')}>
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
                  onRetryRecommendations={() => retryResource('recommendations')}
                />
              )}
            </ResultResourceState>
          </QuestionEvidenceGate>
        )}

        {section === 'report' && (
          <QuestionEvidenceGate resource={resources.questions} onRetry={() => retryResource('questions')}>
            <ReportSection
              analysisId={analysis.id}
              reports={resources.reports}
              onRetryReports={() => retryResource('reports')}
              onRefreshReports={() => refreshResource('reports')}
            />
          </QuestionEvidenceGate>
        )}
      </div>
    </div>
  )
}
