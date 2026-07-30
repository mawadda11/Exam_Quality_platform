import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ProcessingStateBadge } from '../../components/ui/ProcessingStateBadge'
import { useI18n } from '../../i18n/I18nProvider'
import { routeForAnalysis } from '../../router/analysisRouting'
import type { AnalysisResponse } from '../../types/api'

interface AnalysisHistoryTableProps {
  analyses: AnalysisResponse[]
  caption: string
}

export function AnalysisHistoryTable({
  analyses,
  caption,
}: AnalysisHistoryTableProps) {
  const { t, formatDateTime } = useI18n()
  const [useCards, setUseCards] = useState(
    () => typeof window.matchMedia === 'function' && window.matchMedia('(max-width: 48rem)').matches,
  )

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return undefined
    const media = window.matchMedia('(max-width: 48rem)')
    const update = () => setUseCards(media.matches)
    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])

  if (!useCards) {
    return (
      <div className="ui-responsive-table analysis-history-table-wrap">
        <table>
        <caption>{caption}</caption>

        <thead>
          <tr>
            <th scope="col">{t('Course')}</th>
            <th scope="col">{t('Course name')}</th>
            <th scope="col">{t('Exam type')}</th>
            <th scope="col">{t('Term')}</th>
            <th scope="col">{t('Created')}</th>
            <th scope="col">{t('Processing state')}</th>
            <th scope="col">{t('Action')}</th>
          </tr>
        </thead>

        <tbody>
          {analyses.map((analysis) => (
            <tr key={analysis.id}>
              <th scope="row">
                <bdi>{analysis.course.code}</bdi>
              </th>

              <td dir="auto">{analysis.course.name}</td>
              <td>{t(analysis.exam_type)}</td>
              <td dir="auto">{analysis.term}</td>

              <td>
                <time dateTime={analysis.created_at}>
                  {formatDateTime(analysis.created_at)}
                </time>
              </td>

              <td>
                <ProcessingStateBadge state={analysis.state} />
              </td>

              <td>
                <Link to={routeForAnalysis(analysis)}>
                  {t('Open analysis')}
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
        </table>
      </div>
    )
  }

  return (
      <section className="analysis-history-cards" aria-label={caption}>
        <h2 className="visually-hidden">{caption}</h2>
        <ul>
          {analyses.map((analysis) => (
            <li key={analysis.id} className="analysis-history-card">
              <div className="analysis-history-card__heading">
                <div>
                  <strong><bdi>{analysis.course.code}</bdi></strong>
                  <span dir="auto">{analysis.course.name}</span>
                </div>
                <ProcessingStateBadge state={analysis.state} />
              </div>
              <dl>
                <div><dt>{t('Exam type')}</dt><dd>{t(analysis.exam_type)}</dd></div>
                <div><dt>{t('Term')}</dt><dd dir="auto">{analysis.term}</dd></div>
                <div>
                  <dt>{t('Created')}</dt>
                  <dd><time dateTime={analysis.created_at}>{formatDateTime(analysis.created_at)}</time></dd>
                </div>
              </dl>
              <Link className="ui-button ui-button--secondary" to={routeForAnalysis(analysis)}>
                {t('Open analysis')}
              </Link>
            </li>
          ))}
        </ul>
      </section>
  )
}
