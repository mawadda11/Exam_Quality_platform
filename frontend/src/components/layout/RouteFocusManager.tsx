import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'

function pageFocusKey(pathname: string): string {
  const resultsMatch = pathname.match(/^\/analyses\/[^/]+\/results\/[^/]+$/)
  return resultsMatch ? pathname.replace(/\/[^/]+$/, '') : pathname
}

export function RouteFocusManager() {
  const { pathname } = useLocation()
  const previousPageKey = useRef<string | null>(null)

  useEffect(() => {
    const nextPageKey = pageFocusKey(pathname)
    if (previousPageKey.current === null) {
      previousPageKey.current = nextPageKey
      return undefined
    }
    if (previousPageKey.current === nextPageKey) return undefined

    previousPageKey.current = nextPageKey
    const frameId = window.requestAnimationFrame(() => {
      const heading = document.querySelector<HTMLElement>('#main-content h1')
      if (!heading) return

      const alreadyFocusable = heading.hasAttribute('tabindex')
      if (!alreadyFocusable) heading.setAttribute('tabindex', '-1')
      heading.focus({ preventScroll: true })
      if (!alreadyFocusable) {
        heading.addEventListener(
          'blur',
          () => heading.removeAttribute('tabindex'),
          { once: true },
        )
      }
    })

    return () => window.cancelAnimationFrame(frameId)
  }, [pathname])

  return null
}
