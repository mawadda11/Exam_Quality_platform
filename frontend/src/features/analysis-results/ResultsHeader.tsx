import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { ScoreRing } from '../../components/ui/ScoreRing'
import { useI18n } from '../../i18n/I18nProvider'
import type { AnalysisResponse, AnalysisScoreResponse, QuestionResponse, UploadedFileType } from '../../types/api'
import type { ResultResource } from './useAnalysisResultsData'

interface ResultsHeaderProps {
  analysis: AnalysisResponse
  score: ResultResource<AnalysisScoreResponse>
  onRetryScore: () => void
  questions: ResultResource<QuestionResponse[]>
}

function filename(analysis: AnalysisResponse, fileType: UploadedFileType): string | null {
  return (
    analysis.uploaded_files.find((file) => file.file_type === fileType)
      ?.original_filename ?? null
  )
}

export function ResultsHeader({ analysis, score, onRetryScore, questions }: ResultsHeaderProps) {
  const { t, formatDateTime } = useI18n()
  const examFilename = filename(analysis, 'exam')
  const tp153Filename = filename(analysis, 'tp153')

  return (
    <Card as="section" className="results-header">
      <div className="results-header-main">
        <div className="results-header-copy">
          <Link className="results-back-link" to="/analyses">
            ← {t('Return to Analyses')}
          </Link>
          <div className="results-header-identifiers">
            <span className="results-course-code">
              <bdi>{analysis.course.code}</bdi>
            </span>
            <span>{t(analysis.exam_type)}</span>
            <span>
              {t('Analysis')} <bdi>{analysis.id}</bdi>
            </span>
          </div>
          <h1>
            <bdi dir="auto">{analysis.course.name}</bdi>
          </h1>
          <dl className="results-header-metadata">
            <div>
              <dt>{t('Term')}</dt>
              <dd>
                <bdi dir="auto">{analysis.term}</bdi>
              </dd>
            </div>
            <div>
              <dt>{t('Last updated')}</dt>
              <dd>
                <time dateTime={analysis.updated_at}>{formatDateTime(analysis.updated_at)}</time>
              </dd>
            </div>
            <div>
              <dt>{t('Exam file')}</dt>
              <dd>
                {examFilename ? <bdi dir="auto">{examFilename}</bdi> : t('Not available')}
              </dd>
            </div>
            <div>
              <dt>{t('Course Specification file')}</dt>
              <dd>
                {tp153Filename ? <bdi dir="auto">{tp153Filename}</bdi> : t('Not available')}
              </dd>
            </div>
          </dl>
        </div>

        <div className="results-header-score">
          {questions.status !== 'error' &&
            !(questions.status === 'ready' && questions.data.length === 0) &&
            score.status === 'loading' && (
            <div className="results-score-state" role="status" aria-busy="true">
              {t('Loading score…')}
            </div>
          )}
          {questions.status === 'ready' && questions.data.length > 0 && score.status === 'error' && (
            <div className="results-score-state" role="alert">
              <p>{score.message}</p>
              <Button variant="secondary" onClick={onRetryScore}>
                {t('Retry score')}
              </Button>
            </div>
          )}
          {(questions.status === 'error' ||
            (questions.status === 'ready' && questions.data.length === 0)) && (
            <div className="results-score-state results-score-state--incomplete" role="status">
              <strong>{t('Analysis incomplete')}</strong>
              <p>{t('A quality score is hidden until confirmed question evidence is available.')}</p>
            </div>
          )}
          {questions.status === 'ready' && questions.data.length > 0 && score.status === 'ready' && (
            <ScoreRing
              score={score.data.score}
              denominator={score.data.denominator}
              emptyLabel={score.data.label ?? t('Insufficient Evidence')}
              label={
                score.data.score_mode === 'local_preliminary'
                  ? t('Preliminary Local Quality Score')
                  : t('Overall Exam Quality Score')
              }
              denominatorKind={
                score.data.score_mode === 'local_preliminary' ? 'applicable' : 'verified'
              }
            />
          )}
        </div>
      </div>
    </Card>
  )
}
