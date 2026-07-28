import { fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { beforeEach, describe, expect, it } from 'vitest'
import { Tabs } from './Tabs'

const ITEMS = [
  { id: 'overview', label: 'Overview' },
  { id: 'questions', label: 'Questions' },
  { id: 'report', label: 'Report' },
] as const

function ControlledTabs() {
  const [value, setValue] = useState<(typeof ITEMS)[number]['id']>('overview')
  return (
    <Tabs
      items={[...ITEMS]}
      value={value}
      onValueChange={setValue}
      ariaLabel="Results sections"
    />
  )
}

describe('Tabs', () => {
  beforeEach(() => {
    document.documentElement.dir = 'ltr'
  })

  it('supports click selection with a single tab stop', () => {
    render(<ControlledTabs />)
    fireEvent.click(screen.getByRole('tab', { name: 'Questions' }))

    expect(screen.getByRole('tab', { name: 'Questions' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('tabindex', '-1')
  })

  it('supports Arrow, Home, and End keyboard navigation', () => {
    render(<ControlledTabs />)
    const overview = screen.getByRole('tab', { name: 'Overview' })
    overview.focus()

    fireEvent.keyDown(overview, { key: 'ArrowRight' })
    const questions = screen.getByRole('tab', { name: 'Questions' })
    expect(questions).toHaveFocus()
    expect(questions).toHaveAttribute('aria-selected', 'true')

    fireEvent.keyDown(questions, { key: 'End' })
    const report = screen.getByRole('tab', { name: 'Report' })
    expect(report).toHaveFocus()
    expect(report).toHaveAttribute('aria-selected', 'true')

    fireEvent.keyDown(report, { key: 'Home' })
    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveFocus()
  })

  it('reverses horizontal arrow movement for RTL reading order', () => {
    document.documentElement.dir = 'rtl'
    render(<ControlledTabs />)
    const overview = screen.getByRole('tab', { name: 'Overview' })
    overview.focus()

    fireEvent.keyDown(overview, { key: 'ArrowLeft' })

    expect(screen.getByRole('tab', { name: 'Questions' })).toHaveFocus()
  })
})
