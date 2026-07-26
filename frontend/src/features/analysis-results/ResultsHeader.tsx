import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { ScoreRing } from '../../components/ui/ScoreRing'
import type { AnalysisResponse, AnalysisScoreResponse, UploadedFileType } from '../../types/api'
import type { ResultResource } from './useAnalysisResultsData'

interface ResultsHeaderProps {
  analysis: AnalysisResponse
  score: ResultResource<AnalysisScoreResponse>
  onRetryScore: () => void
}

function formatDate(timestamp: string): string {
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(timestamp))
}

function filename(analysis: AnalysisResponse, fileType: UploadedFileType): string | null {
  return (
    analysis.uploaded_files.find((file) => file.file_type === fileType)
      ?.original_filename ?? null
  )
}

export function ResultsHeader({ analysis, score, onRetryScore }: ResultsHeaderProps) {
  const examFilename = filename(analysis, 'exam')
  const tp153Filename = filename(analysis, 'tp153')

  return (
    <Card as="section" className="results-header">
      <div className="results-header-main">
        <div className="results-header-copy">
          <Link className="results-back-link" to="/analyses">
            ← Back to Analyses
          </Link>
          <div className="results-header-identifiers">
            <span className="results-course-code">
              <bdi>{analysis.course.code}</bdi>
            </span>
            <span>{analysis.exam_type}</span>
            <span>
              Analysis <bdi>{analysis.id}</bdi>
            </span>
          </div>
          <h1>
            <bdi dir="auto">{analysis.course.name}</bdi>
          </h1>
          <dl className="results-header-metadata">
            <div>
              <dt>Term</dt>
              <dd>
                <bdi dir="auto">{analysis.term}</bdi>
              </dd>
            </div>
            <div>
              <dt>Last updated</dt>
              <dd>
                <time dateTime={analysis.updated_at}>{formatDate(analysis.updated_at)}</time>
              </dd>
            </div>
            <div>
              <dt>Exam file</dt>
              <dd>
                {examFilename ? <bdi dir="auto">{examFilename}</bdi> : 'Not available'}
              </dd>
            </div>
            <div>
              <dt>TP-153 file</dt>
              <dd>
                {tp153Filename ? <bdi dir="auto">{tp153Filename}</bdi> : 'Not available'}
              </dd>
            </div>
          </dl>
          {analysis.predecessor_analysis_id && (
            <p className="results-reanalysis-context">
              Linked reanalysis of{' '}
              <Link
                to={`/analyses/${analysis.predecessor_analysis_id}/results/overview`}
              >
                analysis <bdi>{analysis.predecessor_analysis_id}</bdi>
              </Link>
              .
            </p>
          )}
        </div>

        <div className="results-header-score">
          {score.status === 'loading' && (
            <div className="results-score-state" role="status" aria-busy="true">
              Loading score…
            </div>
          )}
          {score.status === 'error' && (
            <div className="results-score-state" role="alert">
              <p>{score.message}</p>
              <Button variant="secondary" onClick={onRetryScore}>
                Retry score
              </Button>
            </div>
          )}
          {score.status === 'ready' && (
            <ScoreRing
              score={score.data.score}
              denominator={score.data.denominator}
              emptyLabel={score.data.label ?? 'Insufficient Evidence'}
            />
          )}
        </div>
      </div>
    </Card>
  )
}
