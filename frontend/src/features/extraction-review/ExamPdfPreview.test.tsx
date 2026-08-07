import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as analysesApi from '../../api/analyses'
import { ExamPdfPreview } from './ExamPdfPreview'
import { clearExamImageCache } from './pdfImageCache'

vi.mock('../../api/analyses')

describe('ExamPdfPreview', () => {
  beforeEach(() => {
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: vi.fn(),
    })
    clearExamImageCache()
    vi.clearAllMocks()
    vi.mocked(analysesApi.getExamPdf).mockResolvedValue(
      new Blob(['pdf'], { type: 'application/pdf' }),
    )
    vi.mocked(analysesApi.getExamPageImage).mockResolvedValue({
      blob: new Blob(['png'], { type: 'image/png' }),
      pageWidth: 612,
      pageHeight: 792,
    })
    vi.spyOn(URL, 'createObjectURL').mockImplementation((blob) =>
      blob instanceof Blob && blob.type === 'application/pdf'
        ? 'blob:protected-exam'
        : 'blob:protected-page',
    )
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined)
  })

  it('renders one cached authenticated page image and overlays source geometry', async () => {
    render(
      <ExamPdfPreview
        analysisId="analysis-1"
        pageNumber={3}
        geometry={{ x0: 61.2, top: 79.2, x1: 306, bottom: 158.4 }}
        onPageChange={vi.fn()}
        focusRequest={1}
      />,
    )

    const image = await screen.findByRole('img', {
      name: 'Original examination PDF — Page 3',
    })
    expect(image).toHaveAttribute('src', 'blob:protected-page')
    expect(analysesApi.getExamPageImage).toHaveBeenCalledWith(
      'analysis-1',
      3,
      null,
      { dpi: 144 },
    )
    expect(screen.getByRole('status')).toHaveTextContent(
      'Selected PDF location: Page 3',
    )
    expect(screen.getByRole('link', { name: 'Open PDF in a new tab' })).toHaveAttribute(
      'href',
      'blob:protected-exam',
    )
  })

  it('allows a reviewer to drag a replacement question region in PDF coordinates', async () => {
    const onGeometryChange = vi.fn()
    render(
      <ExamPdfPreview
        analysisId="analysis-1"
        pageNumber={2}
        geometry={null}
        onPageChange={vi.fn()}
        focusRequest={1}
        onGeometryChange={onGeometryChange}
      />,
    )

    const image = await screen.findByRole('img', {
      name: 'Original examination PDF — Page 2',
    })
    vi.spyOn(image, 'getBoundingClientRect').mockReturnValue({
      left: 10,
      top: 20,
      width: 612,
      height: 792,
      right: 622,
      bottom: 812,
      x: 10,
      y: 20,
      toJSON: () => ({}),
    })
    Object.defineProperty(image, 'setPointerCapture', {
      configurable: true,
      value: vi.fn(),
    })

    fireEvent.click(screen.getByRole('button', { name: 'Adjust question area' }))
    fireEvent.pointerDown(image, { pointerId: 1, clientX: 110, clientY: 120 })
    fireEvent.pointerMove(image, { pointerId: 1, clientX: 310, clientY: 320 })
    fireEvent.pointerUp(image, { pointerId: 1, clientX: 310, clientY: 320 })

    await waitFor(() => {
      expect(onGeometryChange).toHaveBeenCalledWith({
        x0: 100,
        top: 100,
        x1: 300,
        bottom: 300,
      })
    })
  })

  it('shows a clear page-selection result when precise geometry is unavailable', async () => {
    render(
      <ExamPdfPreview
        analysisId="analysis-1"
        pageNumber={2}
        geometry={null}
        onPageChange={vi.fn()}
        focusRequest={1}
      />,
    )

    await screen.findByRole('img', { name: 'Original examination PDF — Page 2' })
    expect(screen.getByRole('status')).toHaveTextContent(
      'Selected PDF location: Page 2 · Precise highlight is unavailable for this item.',
    )
  })
  it('keeps the authenticated original PDF available when page rendering fails', async () => {
    vi.mocked(analysesApi.getExamPageImage).mockRejectedValueOnce(new Error('render failed'))

    render(
      <ExamPdfPreview
        analysisId="analysis-1"
        pageNumber={2}
        geometry={null}
        onPageChange={vi.fn()}
        focusRequest={1}
      />,
    )

    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load exam PDF')
    const pdfLinks = screen.getAllByRole('link', { name: 'Open PDF in a new tab' })
    expect(pdfLinks.some((link) => link.getAttribute('href') === 'blob:protected-exam')).toBe(true)
    expect(document.querySelector('object[type="application/pdf"]')).not.toBeNull()
  })
})
