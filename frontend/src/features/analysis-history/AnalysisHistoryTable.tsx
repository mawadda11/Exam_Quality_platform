import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { deleteAnalysis } from '../../api/analyses'
import { Button } from '../../components/ui/Button'
import { Icon } from '../../components/ui/Icon'
import { ProcessingStateBadge } from '../../components/ui/ProcessingStateBadge'
import { useI18n } from '../../i18n/I18nProvider'
import { localizeInterfaceError } from '../../i18n/localizeError'
import { routeForAnalysis } from '../../router/analysisRouting'
import type { AnalysisResponse } from '../../types/api'

interface AnalysisHistoryTableProps {
  analyses: AnalysisResponse[]
  caption: string
  onDeleted?: (analysisId: string) => void
}

const DELETABLE_STATES = new Set(['queued', 'review_ready', 'completed', 'failed'])

export function AnalysisHistoryTable({
  analyses,
  caption,
  onDeleted,
}: AnalysisHistoryTableProps) {
  const { locale, t, formatDateTime } = useI18n()
  const [selected, setSelected] = useState<AnalysisResponse | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [deleteNotice, setDeleteNotice] = useState<string | null>(null)
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

  async function confirmDelete(): Promise<void> {
    if (!selected || isDeleting) return
    setIsDeleting(true)
    setDeleteError(null)
    try {
      await deleteAnalysis(selected.id)
      onDeleted?.(selected.id)
      setDeleteNotice(t('Analysis deleted'))
      setSelected(null)
    } catch (error) {
      setDeleteError(
        localizeInterfaceError(error, locale, t, 'Could not delete analysis'),
      )
    } finally {
      setIsDeleting(false)
    }
  }

  function deleteAction(analysis: AnalysisResponse) {
    const allowed = DELETABLE_STATES.has(analysis.state)
    return (
      <Button
        variant="ghost"
        className="analysis-delete-action"
        disabled={!allowed}
        title={allowed ? t('Delete analysis') : t('Deletion is unavailable while processing')}
        onClick={() => {
          setDeleteError(null)
          setSelected(analysis)
        }}
      >
        <Icon name="trash" />
      </Button>
    )
  }

  const dialog = selected ? (
    <div className="analysis-delete-backdrop" role="presentation">
      <section
        className="analysis-delete-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="analysis-delete-title"
      >
        <h2 id="analysis-delete-title">{t('Permanently delete analysis?')}</h2>
        <dl>
          <div><dt>{t('Course code')}</dt><dd><bdi>{selected.course.code}</bdi></dd></div>
          <div><dt>{t('Course name')}</dt><dd dir="auto">{selected.course.name}</dd></div>
          <div><dt>{t('Exam type')}</dt><dd>{t(selected.exam_type)}</dd></div>
          <div><dt>{t('Term')}</dt><dd dir="auto">{selected.term}</dd></div>
        </dl>
        <p>{t('Uploaded files, extracted evidence, findings, and generated reports will be permanently removed.')}</p>
        <strong>{t('This action cannot be undone.')}</strong>
        {deleteError && <p className="analysis-delete-error" role="alert">{deleteError}</p>}
        <div className="analysis-delete-dialog__actions">
          <Button variant="secondary" disabled={isDeleting} onClick={() => setSelected(null)}>
            {t('Cancel')}
          </Button>
          <Button
            variant="danger"
            isLoading={isDeleting}
            loadingLabel={t('Deleting analysis…')}
            onClick={() => void confirmDelete()}
          >
            {t('Delete permanently')}
          </Button>
        </div>
      </section>
    </div>
  ) : null

  if (!useCards) {
    return (
      <>
      {deleteNotice && <p className="analysis-delete-notice" role="status">{deleteNotice}</p>}
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
                <div className="analysis-history-actions">
                  <Link
                    className="analysis-action-icon analysis-open-action"
                    to={routeForAnalysis(analysis)}
                    aria-label={t('Open analysis')}
                    title={t('Open analysis')}
                  >
                    <Icon name="eye" />
                  </Link>
                  {deleteAction(analysis)}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
        </table>
      </div>
      {dialog}
      </>
    )
  }

  return (
    <>
    {deleteNotice && <p className="analysis-delete-notice" role="status">{deleteNotice}</p>}
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
              <div className="analysis-history-actions">
                <Link
                  className="analysis-action-icon analysis-open-action"
                  to={routeForAnalysis(analysis)}
                  aria-label={t('Open analysis')}
                  title={t('Open analysis')}
                >
                  <Icon name="eye" />
                </Link>
                {deleteAction(analysis)}
              </div>
            </li>
          ))}
        </ul>
      </section>
      {dialog}
    </>
  )
}
