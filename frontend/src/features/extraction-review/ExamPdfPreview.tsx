import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from 'react'
import { getCourseSpecificationPdf, getExamPdf } from '../../api/analyses'
import { Button } from '../../components/ui/Button'
import { useI18n } from '../../i18n/I18nProvider'
import { localizeInterfaceError } from '../../i18n/localizeError'
import type { ExtractionReviewGeometry, UploadedFileType } from '../../types/api'
import {
  invalidateCachedExamImage,
  loadCachedExamImage,
} from './pdfImageCache'

interface ExamPdfPreviewProps {
  analysisId: string
  sourceDocument?: UploadedFileType
  pageNumber: number
  geometry: ExtractionReviewGeometry | null
  onPageChange: (page: number) => void
  focusRequest: number
  onGeometryChange?: (geometry: ExtractionReviewGeometry) => void
}

interface Point {
  x: number
  y: number
}

interface PageAsset {
  pageNumber: number
  url: string
  width: number
  height: number
}

interface PdfLoadResult {
  requestKey: string
  url: string | null
  error: string | null
}

interface PageLoadResult {
  requestKey: string
  asset: PageAsset | null
  error: string | null
}

const PAGE_IMAGE_OPTIONS = { dpi: 144 } as const

function normalizeSelection(start: Point, end: Point): ExtractionReviewGeometry {
  return {
    x0: Math.min(start.x, end.x),
    top: Math.min(start.y, end.y),
    x1: Math.max(start.x, end.x),
    bottom: Math.max(start.y, end.y),
  }
}

function overlayStyle(
  geometry: ExtractionReviewGeometry | null,
  width: number,
  height: number,
): React.CSSProperties | undefined {
  if (!geometry || width <= 0 || height <= 0) return undefined
  return {
    left: `${Math.max(0, Math.min(100, (geometry.x0 / width) * 100))}%`,
    top: `${Math.max(0, Math.min(100, (geometry.top / height) * 100))}%`,
    width: `${Math.max(0.5, Math.min(100, ((geometry.x1 - geometry.x0) / width) * 100))}%`,
    height: `${Math.max(0.5, Math.min(100, ((geometry.bottom - geometry.top) / height) * 100))}%`,
  }
}

export function ExamPdfPreview({
  analysisId,
  sourceDocument = 'exam',
  pageNumber,
  geometry,
  onPageChange,
  focusRequest,
  onGeometryChange,
}: ExamPdfPreviewProps) {
  const { locale, t } = useI18n()
  const [zoom, setZoom] = useState(100)
  const [viewMode, setViewMode] = useState<'region' | 'copy'>('region')
  const [selectionMode, setSelectionMode] = useState(false)
  const [dragStart, setDragStart] = useState<Point | null>(null)
  const [pageLoadNonce, setPageLoadNonce] = useState(0)
  const pdfRequestKey = `${analysisId}:${sourceDocument}:${locale}`
  const pageRequestKey = `${analysisId}:${sourceDocument}:${pageNumber}:${pageLoadNonce}:${locale}`
  const [pdfResult, setPdfResult] = useState<PdfLoadResult>({
    requestKey: '',
    url: null,
    error: null,
  })
  const [pageResult, setPageResult] = useState<PageLoadResult>({
    requestKey: '',
    asset: null,
    error: null,
  })
  const [draftSelectionState, setDraftSelectionState] = useState<{
    requestKey: string
    geometry: ExtractionReviewGeometry | null
  }>({ requestKey: '', geometry: null })
  const previewRef = useRef<HTMLElement | null>(null)
  const pageImageRef = useRef<HTMLImageElement | null>(null)

  useEffect(() => {
    let active = true
    let objectUrl: string | null = null
    const getPdf = sourceDocument === 'tp153' ? getCourseSpecificationPdf : getExamPdf
    void getPdf(analysisId)
      .then((blob) => {
        if (!active) return
        const pdfBlob =
          blob.type === 'application/pdf'
            ? blob
            : new Blob([blob], { type: 'application/pdf' })
        objectUrl = URL.createObjectURL(pdfBlob)
        setPdfResult({ requestKey: pdfRequestKey, url: objectUrl, error: null })
      })
      .catch((loadError: unknown) => {
        if (active) {
          setPdfResult({
            requestKey: pdfRequestKey,
            url: null,
            error: localizeInterfaceError(loadError, locale, t, sourceDocument === 'tp153' ? 'Could not load Course Specification PDF' : 'Could not load exam PDF'),
          })
        }
      })
    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [analysisId, locale, pdfRequestKey, sourceDocument, t])

  useEffect(() => {
    let active = true
    void loadCachedExamImage(analysisId, pageNumber, null, PAGE_IMAGE_OPTIONS, sourceDocument)
      .then((response) => {
        if (!active) return
        setPageResult({
          requestKey: pageRequestKey,
          asset: {
            pageNumber,
            url: response.url,
            width: response.pageWidth,
            height: response.pageHeight,
          },
          error: null,
        })
      })
      .catch((loadError: unknown) => {
        if (!active) return
        setPageResult({
          requestKey: pageRequestKey,
          asset: null,
          error: localizeInterfaceError(loadError, locale, t, sourceDocument === 'tp153' ? 'Could not load Course Specification PDF' : 'Could not load exam PDF'),
        })
      })
    return () => {
      active = false
    }
  }, [analysisId, locale, pageLoadNonce, pageNumber, pageRequestKey, sourceDocument, t])

  useEffect(() => {
    if (focusRequest <= 0) return
    setViewMode('region')
    previewRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'nearest' })
    previewRef.current?.focus?.({ preventScroll: true })
  }, [focusRequest])

  const pdfUrl = pdfResult.requestKey === pdfRequestKey ? pdfResult.url : null
  const pdfError = pdfResult.requestKey === pdfRequestKey ? pdfResult.error : null
  const visiblePageResult = pageResult.requestKey === pageRequestKey ? pageResult : null
  const visibleAsset = visiblePageResult?.asset ?? null
  const pageError = visiblePageResult?.error ?? null
  const isPageLoading = visiblePageResult === null
  const draftSelection = draftSelectionState.requestKey === pageRequestKey
    ? draftSelectionState.geometry
    : null
  const pageSize = visibleAsset
    ? { width: visibleAsset.width, height: visibleAsset.height }
    : { width: 612, height: 792 }

  function setDraftSelection(geometryValue: ExtractionReviewGeometry | null): void {
    setDraftSelectionState({ requestKey: pageRequestKey, geometry: geometryValue })
  }

  function pointFromPointer(event: ReactPointerEvent<HTMLImageElement>): Point | null {
    const image = pageImageRef.current
    if (!image) return null
    const rect = image.getBoundingClientRect()
    if (!rect.width || !rect.height) return null
    return {
      x: Math.max(0, Math.min(pageSize.width, ((event.clientX - rect.left) / rect.width) * pageSize.width)),
      y: Math.max(0, Math.min(pageSize.height, ((event.clientY - rect.top) / rect.height) * pageSize.height)),
    }
  }

  function handlePointerDown(event: ReactPointerEvent<HTMLImageElement>): void {
    if (!selectionMode || !onGeometryChange) return
    const point = pointFromPointer(event)
    if (!point) return
    event.currentTarget.setPointerCapture(event.pointerId)
    setDragStart(point)
    setDraftSelection({ x0: point.x, top: point.y, x1: point.x, bottom: point.y })
  }

  function handlePointerMove(event: ReactPointerEvent<HTMLImageElement>): void {
    if (!dragStart || !selectionMode) return
    const point = pointFromPointer(event)
    if (!point) return
    setDraftSelection(normalizeSelection(dragStart, point))
  }

  function handlePointerUp(event: ReactPointerEvent<HTMLImageElement>): void {
    if (!dragStart || !selectionMode || !onGeometryChange) return
    const point = pointFromPointer(event)
    setDragStart(null)
    if (!point) return
    const selected = normalizeSelection(dragStart, point)
    if (selected.x1 - selected.x0 < 8 || selected.bottom - selected.top < 8) {
      setDraftSelection(null)
      return
    }
    onGeometryChange(selected)
    setDraftSelection(null)
    setSelectionMode(false)
  }

  const currentSelectionStyle = useMemo(
    () => overlayStyle(geometry, pageSize.width, pageSize.height),
    [geometry, pageSize.height, pageSize.width],
  )
  const draftSelectionStyle = useMemo(
    () => overlayStyle(draftSelection, pageSize.width, pageSize.height),
    [draftSelection, pageSize.height, pageSize.width],
  )

  function retryPageImage(): void {
    invalidateCachedExamImage(analysisId, pageNumber, null, PAGE_IMAGE_OPTIONS, sourceDocument)
    setPageLoadNonce((value) => value + 1)
  }

  const originalPdfLabel = t(
    sourceDocument === 'tp153' ? 'Original Course Specification PDF' : 'Original examination PDF',
  )
  const selectablePdfLabel = t(
    sourceDocument === 'tp153' ? 'Selectable Course Specification PDF' : 'Selectable examination PDF',
  )

  return (
    <aside
      ref={previewRef}
      className="exam-pdf-preview"
      aria-label={originalPdfLabel}
      tabIndex={-1}
    >
      <div className="exam-pdf-preview__toolbar">
        <Button
          variant="ghost"
          aria-label={t('Previous page')}
          disabled={pageNumber <= 1}
          onClick={() => onPageChange(Math.max(1, pageNumber - 1))}
        >
          −
        </Button>
        <span>{t('Page')} {pageNumber}</span>
        <Button
          variant="ghost"
          aria-label={t('Next page')}
          onClick={() => onPageChange(pageNumber + 1)}
        >
          +
        </Button>
        <Button
          variant="ghost"
          aria-label={t('Zoom out')}
          onClick={() => setZoom((value) => Math.max(50, value - 25))}
        >
          −
        </Button>
        <span>{zoom}%</span>
        <Button
          variant="ghost"
          aria-label={t('Zoom in')}
          onClick={() => setZoom((value) => Math.min(200, value + 25))}
        >
          +
        </Button>
        {pdfUrl && (
          <>
            <Button
              variant={viewMode === 'copy' ? 'primary' : 'secondary'}
              aria-pressed={viewMode === 'copy'}
              onClick={() => {
                setViewMode('copy')
                setSelectionMode(false)
                setDraftSelection(null)
                setDragStart(null)
              }}
            >
              {t('Copy text')}
            </Button>
            <Button
              variant={viewMode === 'region' ? 'secondary' : 'ghost'}
              aria-pressed={viewMode === 'region'}
              onClick={() => setViewMode('region')}
            >
              {t('Region view')}
            </Button>
          </>
        )}
        {onGeometryChange && (
          <Button
            variant={selectionMode ? 'primary' : 'secondary'}
            aria-pressed={selectionMode}
            onClick={() => {
              setViewMode('region')
              setSelectionMode((value) => !value)
              setDraftSelection(null)
              setDragStart(null)
            }}
          >
            {selectionMode
              ? t('Cancel area adjustment')
              : t(sourceDocument === 'tp153' ? 'Adjust source area' : 'Adjust question area')}
          </Button>
        )}
      </div>
      {focusRequest > 0 && (
        <p className="exam-pdf-preview__selection-status" role="status" aria-live="polite">
          {t('Selected PDF location')}: {t('Page')} {pageNumber}
          {!geometry && ` · ${t('Precise highlight is unavailable for this item.')}`}
        </p>
      )}
      {selectionMode && (
        <p className="exam-pdf-preview__selection-help">
          {t(sourceDocument === 'tp153'
            ? 'Drag over the complete source record in the Course Specification PDF.'
            : 'Drag over the complete original question, including its table, figure, or answer area.')}
        </p>
      )}
      {pdfError && <p className="exam-pdf-preview__error" role="alert">{pdfError}</p>}
      {pageError && viewMode === 'region' && (
        <div className="exam-pdf-preview__error" role="alert">
          <p>{pageError}</p>
          <Button variant="secondary" onClick={retryPageImage}>{t('Try again')}</Button>
        </div>
      )}
      {viewMode === 'region' && isPageLoading && !visibleAsset && !pageError && (
        <p className="exam-pdf-preview__loading">{t('Rendering exam PDF…')}</p>
      )}
      {pageError && pdfUrl && viewMode === 'region' && (
        <div className="exam-pdf-preview__fallback">
          <p>{t('The original PDF remains available while the page image is retried.')}</p>
          <object
            data={`${pdfUrl}#page=${pageNumber}`}
            type="application/pdf"
            aria-label={`${originalPdfLabel} — ${t('Page')} ${pageNumber}`}
          >
            <a href={pdfUrl} target="_blank" rel="noreferrer">
              {t('Open PDF in a new tab')}
            </a>
          </object>
        </div>
      )}
      {viewMode === 'copy' && pdfUrl && (
        <div className="exam-pdf-preview__copy-view">
          <p>{t('Select text in the PDF, copy it, then paste it into the exact editable field you want on the right.')}</p>
          <object
            data={`${pdfUrl}#page=${pageNumber}&zoom=${zoom}`}
            type="application/pdf"
            aria-label={`${selectablePdfLabel} — ${t('Page')} ${pageNumber}`}
          >
            <a href={pdfUrl} target="_blank" rel="noreferrer">
              {t('Open PDF in a new tab')}
            </a>
          </object>
        </div>
      )}
      {viewMode === 'region' && visibleAsset && !pageError && (
        <div className="exam-pdf-preview__viewport">
          <div
            className="exam-pdf-preview__page"
            style={{ width: `${zoom}%`, aspectRatio: `${pageSize.width} / ${pageSize.height}` }}
          >
            <img
              ref={pageImageRef}
              src={visibleAsset.url}
              alt={`${originalPdfLabel} — ${t('Page')} ${pageNumber}`}
              draggable={false}
              className={selectionMode ? 'exam-pdf-preview__image exam-pdf-preview__image--selecting' : 'exam-pdf-preview__image'}
              onPointerDown={handlePointerDown}
              onPointerMove={handlePointerMove}
              onPointerUp={handlePointerUp}
              onPointerCancel={() => {
                setDragStart(null)
                setDraftSelection(null)
              }}
              onError={() => {
                setPageResult({
                  requestKey: pageRequestKey,
                  asset: null,
                  error: t('The rendered page image could not be displayed. Use the PDF fallback below or try again.'),
                })
              }}
            />
            {currentSelectionStyle && !selectionMode && (
              <span
                key={focusRequest}
                className="exam-pdf-preview__highlight"
                style={currentSelectionStyle}
                aria-hidden="true"
              />
            )}
            {draftSelectionStyle && (
              <span
                className="exam-pdf-preview__draft-selection"
                style={draftSelectionStyle}
                aria-hidden="true"
              />
            )}
          </div>
        </div>
      )}
      {pdfUrl && (
        <a className="exam-pdf-preview__open" href={pdfUrl} target="_blank" rel="noreferrer">
          {t('Open PDF in a new tab')}
        </a>
      )}
    </aside>
  )
}
