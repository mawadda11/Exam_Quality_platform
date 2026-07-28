import { useRef, type KeyboardEvent } from 'react'

export interface TabItem<T extends string> {
  id: T
  label: string
}

interface TabsProps<T extends string> {
  items: TabItem<T>[]
  value: T
  onValueChange: (value: T) => void
  ariaLabel: string
}

export function Tabs<T extends string>({
  items,
  value,
  onValueChange,
  ariaLabel,
}: TabsProps<T>) {
  const refs = useRef<Array<HTMLButtonElement | null>>([])

  function selectAt(index: number): void {
    const item = items[index]
    if (!item) return
    onValueChange(item.id)
    refs.current[index]?.focus()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number): void {
    let targetIndex: number | null = null
    const direction = document.documentElement.dir === 'rtl' ? -1 : 1
    if (event.key === 'ArrowRight') targetIndex = (index + direction + items.length) % items.length
    if (event.key === 'ArrowLeft') targetIndex = (index - direction + items.length) % items.length
    if (event.key === 'Home') targetIndex = 0
    if (event.key === 'End') targetIndex = items.length - 1
    if (targetIndex === null) return

    event.preventDefault()
    selectAt(targetIndex)
  }

  return (
    <div className="ui-tabs" role="tablist" aria-label={ariaLabel}>
      {items.map((item, index) => {
        const selected = item.id === value
        return (
          <button
            key={item.id}
            ref={(element) => {
              refs.current[index] = element
            }}
            type="button"
            id={`tab-${item.id}`}
            className="ui-tab"
            role="tab"
            aria-selected={selected}
            aria-controls={`tabpanel-${item.id}`}
            tabIndex={selected ? 0 : -1}
            onClick={() => onValueChange(item.id)}
            onKeyDown={(event) => handleKeyDown(event, index)}
          >
            {item.label}
          </button>
        )
      })}
    </div>
  )
}
