import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'

interface ResponsiveTableProps {
  caption: string
  children: ReactNode
  className?: string
  captionVisible?: boolean
}

export function ResponsiveTable({
  caption,
  children,
  className = '',
  captionVisible = false,
}: ResponsiveTableProps) {
  const captionId = useId()
  const topScrollRef = useRef<HTMLDivElement>(null)
  const contentScrollRef = useRef<HTMLDivElement>(null)
  const topSpacerRef = useRef<HTMLDivElement>(null)
  const [hasHorizontalOverflow, setHasHorizontalOverflow] = useState(false)

  useEffect(() => {
    const content = contentScrollRef.current
    const spacer = topSpacerRef.current
    if (!content || !spacer) return undefined

    const update = () => {
      spacer.style.width = `${content.scrollWidth}px`
      setHasHorizontalOverflow(content.scrollWidth > content.clientWidth + 1)
    }

    update()
    const observer = typeof ResizeObserver === 'function' ? new ResizeObserver(update) : null
    observer?.observe(content)
    const table = content.querySelector('table')
    if (table) observer?.observe(table)
    window.addEventListener('resize', update)
    return () => {
      observer?.disconnect()
      window.removeEventListener('resize', update)
    }
  }, [children])

  function syncFromTop(): void {
    if (topScrollRef.current && contentScrollRef.current) {
      contentScrollRef.current.scrollLeft = topScrollRef.current.scrollLeft
    }
  }

  function syncFromContent(): void {
    if (topScrollRef.current && contentScrollRef.current) {
      topScrollRef.current.scrollLeft = contentScrollRef.current.scrollLeft
    }
  }

  function handleRegionKeyDown(event: KeyboardEvent<HTMLDivElement>): void {
    const content = contentScrollRef.current
    if (!content || !hasHorizontalOverflow) return
    const step = Math.max(120, Math.round(content.clientWidth * 0.35))
    if (event.key === 'ArrowRight') {
      event.preventDefault()
      content.scrollLeft += step
      syncFromContent()
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault()
      content.scrollLeft -= step
      syncFromContent()
    } else if (event.key === 'Home') {
      event.preventDefault()
      content.scrollLeft = 0
      syncFromContent()
    } else if (event.key === 'End') {
      event.preventDefault()
      content.scrollLeft = content.scrollWidth
      syncFromContent()
    }
  }

  return (
    <div
      className="ui-responsive-table"
      role="region"
      aria-labelledby={captionId}
      tabIndex={0}
      onKeyDown={handleRegionKeyDown}
    >
      <div
        ref={topScrollRef}
        className="ui-responsive-table__top-scroll"
        aria-hidden="true"
        hidden={!hasHorizontalOverflow}
        onScroll={syncFromTop}
      >
        <div ref={topSpacerRef} className="ui-responsive-table__top-spacer" />
      </div>
      <div
        ref={contentScrollRef}
        className="ui-responsive-table__scroll"
        onScroll={syncFromContent}
      >
        <table className={['faculty-data-table', className].filter(Boolean).join(' ')}>
          <caption id={captionId} className={captionVisible ? undefined : 'visually-hidden'}>
            {caption}
          </caption>
          {children}
        </table>
      </div>
    </div>
  )
}
