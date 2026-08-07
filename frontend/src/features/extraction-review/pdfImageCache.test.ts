import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as analysesApi from '../../api/analyses'
import {
  clearExamImageCache,
  invalidateCachedExamImage,
  loadCachedExamImage,
} from './pdfImageCache'

vi.mock('../../api/analyses')

describe('pdfImageCache', () => {
  beforeEach(() => {
    clearExamImageCache()
    vi.clearAllMocks()
    vi.mocked(analysesApi.getExamPageImage).mockResolvedValue({
      blob: new Blob(['png'], { type: 'image/png' }),
      pageWidth: 612,
      pageHeight: 792,
    })
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:stable-page')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined)
  })

  it('reuses one protected image request across repeated renders', async () => {
    const first = loadCachedExamImage('analysis-1', 2, null, { dpi: 144 })
    const second = loadCachedExamImage('analysis-1', 2, null, { dpi: 144 })

    await expect(first).resolves.toMatchObject({ url: 'blob:stable-page' })
    await expect(second).resolves.toMatchObject({ url: 'blob:stable-page' })
    expect(analysesApi.getExamPageImage).toHaveBeenCalledTimes(1)
  })

  it('reloads after explicit retry without revoking a URL still mounted elsewhere', async () => {
    await loadCachedExamImage('analysis-1', 2, null, { dpi: 144 })

    invalidateCachedExamImage('analysis-1', 2, null, { dpi: 144 })
    await Promise.resolve()
    await loadCachedExamImage('analysis-1', 2, null, { dpi: 144 })

    expect(URL.revokeObjectURL).not.toHaveBeenCalledWith('blob:stable-page')
    expect(analysesApi.getExamPageImage).toHaveBeenCalledTimes(2)
  })
})
