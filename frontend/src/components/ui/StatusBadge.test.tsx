import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { AcademicStatus } from '../../types/api'
import { StatusBadge } from './StatusBadge'

const STATUSES: AcademicStatus[] = [
  'Satisfied',
  'Partially Satisfied',
  'Not Satisfied',
  'Not Verified',
  'Not Applicable',
]

describe('StatusBadge', () => {
  it.each(STATUSES)('renders the approved %s status as visible text', (status) => {
    render(<StatusBadge status={status} />)

    const text = screen.getByText(status)
    const badge = text.closest('[data-academic-status]')
    expect(text).toBeVisible()
    expect(badge).toHaveAttribute('data-academic-status', status)
  })
})
