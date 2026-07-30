import {
  useDeferredValue,
  useEffect,
  useMemo,
  useState,
  type ChangeEvent,
} from 'react'
import { Link } from 'react-router-dom'
import {
  downloadBlob,
  downloadReportFile,
  generateReport,
} from '../../api/analyses'
import { listReportLibrary } from '../../api/reports'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { PageState } from '../../components/ui/PageState'
import { useI18n } from '../../i18n/I18nProvider'
import { localizeInterfaceError } from '../../i18n/localizeError'
import type {
  ExamType,
  ReportLanguage,
  ReportLibraryItemResponse,
  ReportLibraryPageResponse,
  ReportLibraryPersistedStatus,
  ReportLibrarySort,
  ReportLibraryStatus,
} from '../../types/api'

const PAGE_SIZE = 12

type LibraryLoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: ReportLibraryPageResponse }

function reportItemKey(item: ReportLibraryItemResponse): string {
  return item.report?.id ?? `analysis-${item.analysis.id}`
}

function reportLanguageLabel(
  language: ReportLanguage,
  t: (key: string) => string,
): string {
  return language === 'ar' ? t('Arabic Report') : t('English Report')
}

function ReportDocumentIcon() {
  return (
    <svg
      className="reports-card-icon"
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M7 3.75h7l3 3V20.25H7z" />
      <path d="M14 3.75v3h3M9.5 11h5M9.5 14h5M9.5 17h3.5" />
    </svg>
  )
}

interface ReportCardProps {
  item: ReportLibraryItemResponse
  effectiveStatus: ReportLibraryStatus
  generationError: string | null
  actionError: string | null
  selectedLanguage: ReportLanguage
  isGenerating: boolean
  isDownloading: boolean
  onLanguageChange: (language: ReportLanguage) => void
  onGenerate: () => void
  onDownload: () => void
}

function ReportCard({
  item,
  effectiveStatus,
  generationError,
  actionError,
  selectedLanguage,
  isGenerating,
  isDownloading,
  onLanguageChange,
  onGenerate,
  onDownload,
}: ReportCardProps) {
  const { t, formatDateTime } = useI18n()
  const cardKey = reportItemKey(item)
  const headingId = `report-card-heading-${cardKey}`
  const languageSelectId = `report-language-${cardKey}`
  const report = item.report
  const reportIsUsable =
    report !== null &&
    (effectiveStatus === 'available' ||
      effectiveStatus === 'insufficient_evidence')
  const generateLabel =
    effectiveStatus === 'generation_failed'
      ? 'Retry Generation'
      : effectiveStatus === 'outdated'
        ? 'Generate Updated Report'
        : 'Generate Report'

  const scoreDisplay =
    report?.score !== null && report?.score !== undefined
      ? `${report.score}%`
      : t(report?.score_label ?? 'Insufficient Evidence')

  return (
    <Card
      as="article"
      className="reports-library-card"
      aria-labelledby={headingId}
    >
      <div className="reports-card-status-row">
        <ReportDocumentIcon />
        <span
          className="reports-status-badge"
          data-report-status={effectiveStatus}
        >
          {t(
            {
              available: 'Available',
              not_generated: 'Not Generated',
              generation_failed: 'Generation Failed',
              outdated: 'Outdated',
              insufficient_evidence: 'Insufficient Evidence',
            }[effectiveStatus],
          )}
        </span>
      </div>

      <div className="reports-card-title">
        <h2 id={headingId}>
          <bdi>{item.analysis.course_code}</bdi>
          <span aria-hidden="true"> — </span>
          <span dir="auto">{item.analysis.course_name}</span>
        </h2>
        <p>
          {t(item.analysis.exam_type)}
          <span aria-hidden="true"> · </span>
          <bdi>{item.analysis.term}</bdi>
          {item.analysis.predecessor_analysis_id && (
            <>
              <span aria-hidden="true"> · </span>
              {t('Linked reanalysis')}
            </>
          )}
        </p>
      </div>

      {report && (
        <dl className="reports-card-metadata">
          <div>
            <dt>{t('Report identifier')}</dt>
            <dd>
              <bdi>{report.id}</bdi>
            </dd>
          </div>
          <div>
            <dt>{t('Generated')}</dt>
            <dd>
              <time dateTime={report.created_at}>
                {formatDateTime(report.created_at)}
              </time>
            </dd>
          </div>
          <div>
            <dt>{t('Report language')}</dt>
            <dd>{reportLanguageLabel(report.language, t)}</dd>
          </div>
          <div className="reports-card-score">
            <dt>{t('Overall score')}</dt>
            <dd>{scoreDisplay}</dd>
          </div>
        </dl>
      )}

      {(generationError || actionError) && (
        <div className="reports-card-error" role="alert">
          {generationError ?? actionError}
        </div>
      )}

      <div className="reports-card-actions">
        <Link
          className="ui-button ui-button--secondary"
          to={`/analyses/${item.analysis.id}`}
        >
          {t('View Analysis')}
        </Link>

        {reportIsUsable && report && (
          <>
            <Link
              className="ui-button ui-button--secondary"
              to={`/reports/${report.id}/preview`}
            >
              {t('Preview Report')}
            </Link>
            <Button
              onClick={onDownload}
              isLoading={isDownloading}
              loadingLabel={t('Downloading…')}
            >
              {t('Download PDF')}
            </Button>
          </>
        )}

        {!reportIsUsable && (
          <div className="reports-generate-controls">
            <label htmlFor={languageSelectId}>{t('Report language')}</label>
            <select
              id={languageSelectId}
              value={selectedLanguage}
              onChange={(event) =>
                onLanguageChange(event.target.value as ReportLanguage)
              }
            >
              <option value="ar">{t('Arabic Report')}</option>
              <option value="en">{t('English Report')}</option>
            </select>
            <Button
              onClick={onGenerate}
              isLoading={isGenerating}
              loadingLabel={t('Generating…')}
            >
              {t(generateLabel)}
            </Button>
          </div>
        )}
      </div>
    </Card>
  )
}

function ReportsLoadingState() {
  const { t } = useI18n()
  return (
    <section
      className="reports-loading-state"
      role="status"
      aria-busy="true"
      aria-label={t('Loading reports')}
    >
      <span className="visually-hidden">{t('Loading reports')}</span>
      {Array.from({ length: 6 }, (_, index) => (
        <div className="reports-card-skeleton" aria-hidden="true" key={index}>
          <span />
          <span />
          <span />
          <span />
        </div>
      ))}
    </section>
  )
}

export function ReportsLibrary() {
  const { locale, t } = useI18n()
  const [search, setSearch] = useState('')
  const deferredSearch = useDeferredValue(search.trim())
  const [statusFilter, setStatusFilter] = useState<ReportLibraryStatus | ''>('')
  const [examType, setExamType] = useState<ExamType | ''>('')
  const [language, setLanguage] = useState<ReportLanguage | ''>('')
  const [sort, setSort] = useState<ReportLibrarySort>('newest')
  const [page, setPage] = useState(1)
  const [reloadToken, setReloadToken] = useState(0)
  const [loadState, setLoadState] = useState<LibraryLoadState>({
    status: 'loading',
  })
  const [generationErrors, setGenerationErrors] = useState<
    Record<string, string>
  >({})
  const [actionErrors, setActionErrors] = useState<Record<string, string>>({})
  const [languageSelections, setLanguageSelections] = useState<
    Record<string, ReportLanguage>
  >({})
  const [generatingAnalysisId, setGeneratingAnalysisId] = useState<
    string | null
  >(null)
  const [downloadingReportId, setDownloadingReportId] = useState<string | null>(
    null,
  )

  const persistedStatus: ReportLibraryPersistedStatus | undefined =
    statusFilter && statusFilter !== 'generation_failed'
      ? statusFilter
      : undefined

  useEffect(() => {
    let active = true
    void listReportLibrary({
      q: deferredSearch || undefined,
      status: persistedStatus,
      exam_type: examType || undefined,
      language: language || undefined,
      sort,
      page,
      page_size: PAGE_SIZE,
    })
      .then((data) => {
        if (active) setLoadState({ status: 'ready', data })
      })
      .catch((error: unknown) => {
        if (!active) return
        setLoadState({
          status: 'error',
          message: localizeInterfaceError(
            error,
            locale,
            t,
            'Could not load reports.',
          ),
        })
      })
    return () => {
      active = false
    }
  }, [
    deferredSearch,
    examType,
    language,
    locale,
    page,
    persistedStatus,
    reloadToken,
    sort,
    t,
  ])

  const activeFilters =
    search.length > 0 ||
    statusFilter !== '' ||
    examType !== '' ||
    language !== '' ||
    sort !== 'newest'

  const visibleItems = useMemo(() => {
    if (loadState.status !== 'ready') return []
    const completedItems = loadState.data.items.filter(
      (item) => item.analysis.state === 'completed',
    )
    if (statusFilter !== 'generation_failed') return completedItems
    return completedItems.filter(
      (item) => generationErrors[reportItemKey(item)] !== undefined,
    )
  }, [generationErrors, loadState, statusFilter])

  function updateSearch(event: ChangeEvent<HTMLInputElement>): void {
    setSearch(event.target.value)
    setPage(1)
  }

  function resetFilters(): void {
    setSearch('')
    setStatusFilter('')
    setExamType('')
    setLanguage('')
    setSort('newest')
    setPage(1)
  }

  async function generate(item: ReportLibraryItemResponse): Promise<void> {
    const itemKey = reportItemKey(item)
    if (generatingAnalysisId === item.analysis.id) return
    const selectedLanguage =
      languageSelections[item.analysis.id] ?? item.report?.language ?? locale
    setGeneratingAnalysisId(item.analysis.id)
    setGenerationErrors((current) => {
      const next = { ...current }
      delete next[itemKey]
      return next
    })
    try {
      await generateReport(item.analysis.id, selectedLanguage)
      setReloadToken((current) => current + 1)
    } catch (error: unknown) {
      const message = localizeInterfaceError(
        error,
        locale,
        t,
        'Could not generate the report.',
      )
      setGenerationErrors((current) => ({ ...current, [itemKey]: message }))
    } finally {
      setGeneratingAnalysisId(null)
    }
  }

  async function download(item: ReportLibraryItemResponse): Promise<void> {
    if (!item.report) return
    const itemKey = reportItemKey(item)
    setDownloadingReportId(item.report.id)
    setActionErrors((current) => {
      const next = { ...current }
      delete next[itemKey]
      return next
    })
    try {
      const blob = await downloadReportFile(item.report.id)
      downloadBlob(
        blob,
        `report-${item.report.language}-${item.report.id}.pdf`,
      )
    } catch (error: unknown) {
      const message = localizeInterfaceError(
        error,
        locale,
        t,
        'Could not download the report.',
      )
      setActionErrors((current) => ({ ...current, [itemKey]: message }))
    } finally {
      setDownloadingReportId(null)
    }
  }

  return (
    <>
      <section className="reports-toolbar" aria-label={t('Report filters')}>
        <label className="reports-search-field">
          <span>{t('Search reports')}</span>
          <input
            type="search"
            value={search}
            onChange={updateSearch}
            placeholder={t('Search by course or report identifier')}
          />
        </label>
        <label>
          <span>{t('Report status')}</span>
          <select
            value={statusFilter}
            onChange={(event) => {
              const nextStatus = event.target.value as ReportLibraryStatus | ''
              setStatusFilter(nextStatus)
              if (nextStatus !== 'generation_failed') {
                setPage(1)
              }
            }}
          >
            <option value="">{t('All report statuses')}</option>
            <option value="available">{t('Available')}</option>
            <option value="not_generated">{t('Not Generated')}</option>
            <option value="generation_failed">{t('Generation Failed')}</option>
            <option value="outdated">{t('Outdated')}</option>
            <option value="insufficient_evidence">
              {t('Insufficient Evidence')}
            </option>
          </select>
        </label>
        <label>
          <span>{t('Exam type')}</span>
          <select
            value={examType}
            onChange={(event) => {
              setExamType(event.target.value as ExamType | '')
              setPage(1)
            }}
          >
            <option value="">{t('All exam types')}</option>
            <option value="Midterm">{t('Midterm')}</option>
            <option value="Final">{t('Final')}</option>
          </select>
        </label>
        <label>
          <span>{t('Report language')}</span>
          <select
            value={language}
            onChange={(event) => {
              setLanguage(event.target.value as ReportLanguage | '')
              setPage(1)
            }}
          >
            <option value="">{t('All report languages')}</option>
            <option value="ar">{t('Arabic Report')}</option>
            <option value="en">{t('English Report')}</option>
          </select>
        </label>
        <label>
          <span>{t('Sort reports')}</span>
          <select
            value={sort}
            onChange={(event) => {
              setSort(event.target.value as ReportLibrarySort)
              setPage(1)
            }}
          >
            <option value="newest">{t('Newest generated first')}</option>
            <option value="oldest">{t('Oldest generated first')}</option>
            <option value="course">{t('Course name')}</option>
            <option value="score">{t('Overall score')}</option>
          </select>
        </label>
        {activeFilters && (
          <Button variant="ghost" onClick={resetFilters}>
            {t('Reset filters')}
          </Button>
        )}
      </section>

      {loadState.status === 'loading' && <ReportsLoadingState />}

      {loadState.status === 'error' && (
        <PageState
          state="error"
          title={t('Reports could not be loaded')}
          message={loadState.message}
          action={
            <Button
              variant="secondary"
              onClick={() => {
                setLoadState({ status: 'loading' })
                setReloadToken((current) => current + 1)
              }}
            >
              {t('Retry')}
            </Button>
          }
        />
      )}

      {loadState.status === 'ready' &&
        visibleItems.length === 0 &&
        !activeFilters && (
          <PageState
            state="empty"
            title={t('No reports available yet')}
            message={t('Complete an analysis before generating its report.')}
            action={
              <div className="reports-empty-actions">
                <Link className="ui-button" to="/analyses/new">
                  {t('Start New Analysis')}
                </Link>
                <Link className="ui-button ui-button--secondary" to="/analyses">
                  {t('View incomplete analyses')}
                </Link>
              </div>
            }
          />
        )}

      {loadState.status === 'ready' &&
        (loadState.data.total === 0 || visibleItems.length === 0) &&
        activeFilters && (
          <PageState
            state="empty"
            title={t('No matching reports')}
            message={t('No reports match your search or filters.')}
            action={
              <Button variant="secondary" onClick={resetFilters}>
                {t('Reset filters')}
              </Button>
            }
          />
        )}

      {loadState.status === 'ready' && visibleItems.length > 0 && (
        <>
          <section className="reports-library-results" aria-label={t('Your reports')}>
            <h2 className="visually-hidden">{t('Your reports')}</h2>
            <ul className="reports-library-grid">
              {visibleItems.map((item) => {
                const itemKey = reportItemKey(item)
                const effectiveStatus: ReportLibraryStatus =
                  generationErrors[itemKey] !== undefined
                    ? 'generation_failed'
                    : item.status
                const selectedLanguage =
                  languageSelections[item.analysis.id] ??
                  item.report?.language ??
                  locale
                return (
                  <li key={itemKey}>
                    <ReportCard
                      item={item}
                      effectiveStatus={effectiveStatus}
                      generationError={generationErrors[itemKey] ?? null}
                      actionError={actionErrors[itemKey] ?? null}
                      selectedLanguage={selectedLanguage}
                      isGenerating={
                        generatingAnalysisId === item.analysis.id
                      }
                      isDownloading={
                        downloadingReportId === item.report?.id
                      }
                      onLanguageChange={(nextLanguage) =>
                        setLanguageSelections((current) => ({
                          ...current,
                          [item.analysis.id]: nextLanguage,
                        }))
                      }
                      onGenerate={() => void generate(item)}
                      onDownload={() => void download(item)}
                    />
                  </li>
                )
              })}
            </ul>
          </section>

          {statusFilter !== 'generation_failed' &&
            loadState.data.total_pages > 1 && (
              <nav
                className="reports-pagination"
                aria-label={t('Reports pagination')}
              >
                <Button
                  variant="secondary"
                  disabled={page <= 1}
                  onClick={() => setPage((current) => Math.max(1, current - 1))}
                >
                  {t('Previous')}
                </Button>
                <span aria-live="polite">
                  {t('Page {page} of {total}', {
                    page: loadState.data.page,
                    total: loadState.data.total_pages,
                  })}
                </span>
                <Button
                  variant="secondary"
                  disabled={page >= loadState.data.total_pages}
                  onClick={() =>
                    setPage((current) =>
                      Math.min(loadState.data.total_pages, current + 1),
                    )
                  }
                >
                  {t('Next')}
                </Button>
              </nav>
            )}
        </>
      )}
    </>
  )
}
