import { getExamPageImage, type ExamPageImageResponse } from '../../api/analyses'
import { ApiError } from '../../api/client'
import type { ExtractionReviewGeometry } from '../../types/api'

export interface CachedExamImage extends ExamPageImageResponse {
  url: string
}

interface ImageOptions {
  crop?: boolean
  padding?: number
  dpi?: number
}

/*
 * Page previews and question crops intentionally share the same full-page image.
 * A URL can therefore still be mounted by another component when a reviewer
 * retries one view. Invalidating a cache entry must not revoke that shared URL
 * immediately; retired URLs remain alive until the review cache is explicitly
 * cleared. This prevents the page from appearing briefly and then disappearing.
 */
const imageCache = new Map<string, Promise<CachedExamImage>>()
const resolvedImageUrls = new Map<string, string>()
const retiredImageUrls = new Set<string>()

function shouldRetryImageRequest(error: unknown): boolean {
  if (error instanceof ApiError) {
    return error.status >= 500 || error.status === 408 || error.status === 429
  }
  return error instanceof TypeError
}

async function requestExamImage(
  analysisId: string,
  pageNumber: number,
  geometry: ExtractionReviewGeometry | null,
  options: ImageOptions,
): Promise<ExamPageImageResponse> {
  try {
    return await getExamPageImage(analysisId, pageNumber, geometry, options)
  } catch (error) {
    if (!shouldRetryImageRequest(error)) throw error
    await new Promise((resolve) => window.setTimeout(resolve, 250))
    return getExamPageImage(analysisId, pageNumber, geometry, options)
  }
}

function geometryKey(geometry: ExtractionReviewGeometry | null): string {
  if (!geometry) return 'page'
  return [geometry.x0, geometry.top, geometry.x1, geometry.bottom]
    .map((value) => Number(value).toFixed(3))
    .join(':')
}

export function examImageCacheKey(
  analysisId: string,
  pageNumber: number,
  geometry: ExtractionReviewGeometry | null,
  options: ImageOptions = {},
): string {
  return [
    analysisId,
    pageNumber,
    geometryKey(geometry),
    options.crop ? 'crop' : 'full',
    options.padding ?? 0,
    options.dpi ?? 120,
  ].join('|')
}

export function loadCachedExamImage(
  analysisId: string,
  pageNumber: number,
  geometry: ExtractionReviewGeometry | null,
  options: ImageOptions = {},
): Promise<CachedExamImage> {
  const key = examImageCacheKey(analysisId, pageNumber, geometry, options)
  const existing = imageCache.get(key)
  if (existing) return existing

  const request = requestExamImage(analysisId, pageNumber, geometry, options)
    .then((response) => {
      if (!response.blob.type.startsWith('image/') || response.blob.size === 0) {
        throw new Error('The exam page image response was empty or invalid.')
      }
      const asset = {
        ...response,
        url: URL.createObjectURL(response.blob),
      }
      resolvedImageUrls.set(key, asset.url)
      return asset
    })
    .catch((error: unknown) => {
      imageCache.delete(key)
      resolvedImageUrls.delete(key)
      throw error
    })
  imageCache.set(key, request)
  return request
}

export function invalidateCachedExamImage(
  analysisId: string,
  pageNumber: number,
  geometry: ExtractionReviewGeometry | null,
  options: ImageOptions = {},
): void {
  const key = examImageCacheKey(analysisId, pageNumber, geometry, options)
  const request = imageCache.get(key)
  const resolvedUrl = resolvedImageUrls.get(key)
  imageCache.delete(key)
  resolvedImageUrls.delete(key)
  if (resolvedUrl) {
    retiredImageUrls.add(resolvedUrl)
  } else {
    void request?.then((asset) => retiredImageUrls.add(asset.url), () => undefined)
  }
}

export function clearExamImageCache(analysisId?: string): void {
  for (const [key, request] of imageCache.entries()) {
    if (analysisId && !key.startsWith(`${analysisId}|`)) continue
    const resolvedUrl = resolvedImageUrls.get(key)
    imageCache.delete(key)
    resolvedImageUrls.delete(key)
    if (resolvedUrl) {
      URL.revokeObjectURL(resolvedUrl)
    } else {
      void request.then((asset) => URL.revokeObjectURL(asset.url), () => undefined)
    }
  }

  /* Retired URLs no longer have an analysis-key association. They are few and
   * are released whenever the review cache is globally cleared (tests, logout,
   * or a future explicit workspace cleanup). Keeping them alive between retries
   * is the safety property that avoids invalidating a sibling image element. */
  if (!analysisId) {
    for (const url of retiredImageUrls) URL.revokeObjectURL(url)
    retiredImageUrls.clear()
  }
}
