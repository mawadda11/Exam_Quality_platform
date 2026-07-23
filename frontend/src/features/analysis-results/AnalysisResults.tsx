import { useEffect, useMemo, useState } from 'react'
import {
  getAnalysisScore,
  listClos,
  listFindings,
  listQuestions,
  listRecommendations,
  listTopics,
} from '../../api/analyses'
import { ApiError } from '../../api/client'
import type {
  AnalysisResponse,
  AnalysisScoreResponse,
  CloResponse,
  FindingResponse,
  QuestionResponse,
  RecommendationResponse,
  TopicResponse,
} from '../../types/api'
import { AlignmentCoverageSection } from './AlignmentCoverageSection'
import { FindingsRecommendationsSection } from './FindingsRecommendationsSection'
import { buildLookups } from './lookups'
import { MarksStructureSection } from './MarksStructureSection'
import { OverviewSection } from './OverviewSection'
import { QuestionsSection } from './QuestionsSection'
import { ReportSection } from './ReportSection'

type SectionId =
  | 'overview'
  | 'questions'
  | 'alignment-coverage'
  | 'marks-structure'
  | 'findings-recommendations'
  | 'report'

const SECTIONS: { id: SectionId; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'questions', label: 'Questions' },
  { id: 'alignment-coverage', label: 'Alignment & Coverage' },
  { id: 'marks-structure', label: 'Marks & Structure' },
  { id: 'findings-recommendations', label: 'Findings & Recommendations' },
  { id: 'report', label: 'Report' },
]

interface ResultsData {
  questions: QuestionResponse[]
  clos: CloResponse[]
  topics: TopicResponse[]
  findings: FindingResponse[]
  score: AnalysisScoreResponse
  recommendations: RecommendationResponse[]
}

// A discriminated union (rather than separate isLoading/error/data booleans
// set from inside the effect) so the effect only ever calls setState from
// its async .then()/.catch() callbacks, never synchronously in the effect
// body itself. If this component is ever reused for a different analysis
// id, the caller should remount it with `key={analysis.id}` rather than
// relying on this effect to reset state.
type ResultsState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: ResultsData }

export function AnalysisResults({ analysis }: { analysis: AnalysisResponse }) {
  const [section, setSection] = useState<SectionId>('overview')
  const [state, setState] = useState<ResultsState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false

    Promise.all([
      listQuestions(analysis.id),
      listClos(analysis.id),
      listTopics(analysis.id),
      listFindings(analysis.id),
      getAnalysisScore(analysis.id),
      listRecommendations(analysis.id),
    ])
      .then(([questions, clos, topics, findings, score, recommendations]) => {
        if (cancelled) return
        setState({
          status: 'ready',
          data: { questions, clos, topics, findings, score, recommendations },
        })
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setState({
          status: 'error',
          message: err instanceof ApiError ? err.detail : 'Could not load analysis results.',
        })
      })

    return () => {
      cancelled = true
    }
  }, [analysis.id])

  const readyData = state.status === 'ready' ? state.data : null

  const lookups = useMemo(
    () => buildLookups(readyData?.clos ?? [], readyData?.topics ?? [], readyData?.questions ?? []),
    [readyData],
  )

  const recommendationsByFinding = useMemo(() => {
    const map = new Map<string, RecommendationResponse[]>()
    for (const recommendation of readyData?.recommendations ?? []) {
      const existing = map.get(recommendation.finding_id) ?? []
      existing.push(recommendation)
      map.set(recommendation.finding_id, existing)
    }
    return map
  }, [readyData])

  if (state.status === 'loading') {
    return (
      <p className="notice" role="status">
        Loading results…
      </p>
    )
  }
  if (state.status === 'error') {
    return (
      <p className="field-error" role="alert">
        {state.message}
      </p>
    )
  }

  const { data } = state

  return (
    <div className="analysis-results">
      <nav className="results-nav" aria-label="Results sections">
        {SECTIONS.map((entry) => (
          <button
            key={entry.id}
            type="button"
            className={entry.id === section ? 'results-nav-button results-nav-active' : 'results-nav-button'}
            aria-current={entry.id === section ? 'page' : undefined}
            onClick={() => setSection(entry.id)}
          >
            {entry.label}
          </button>
        ))}
      </nav>

      <div className="results-panel">
        {section === 'overview' && <OverviewSection analysis={analysis} score={data.score} />}
        {section === 'questions' && <QuestionsSection questions={data.questions} />}
        {section === 'alignment-coverage' && (
          <AlignmentCoverageSection
            findings={data.findings}
            clos={data.clos}
            topics={data.topics}
            lookups={lookups}
          />
        )}
        {section === 'marks-structure' && (
          <MarksStructureSection findings={data.findings} lookups={lookups} />
        )}
        {section === 'findings-recommendations' && (
          <FindingsRecommendationsSection
            findings={data.findings}
            recommendationsByFinding={recommendationsByFinding}
            lookups={lookups}
          />
        )}
        {section === 'report' && <ReportSection />}
      </div>
    </div>
  )
}
