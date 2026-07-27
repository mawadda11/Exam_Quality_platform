import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EvaluationScopeRoute } from './EvaluationScopeRoute'

describe('EvaluationScopeRoute', () => {
  it('presents supported, limited, and planned checks as platform scope rather than exam results', () => {
    render(<EvaluationScopeRoute />)

    expect(screen.getByRole('heading', { level: 1, name: 'What the Platform Evaluates' }))
      .toBeInTheDocument()
    expect(screen.getByText('14')).toBeInTheDocument()
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('6')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Available in this release' }))
      .toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Planned for a future release' }))
      .toBeInTheDocument()
    expect(screen.getByText(/planned checks are not treated as exam failures/i))
      .toBeInTheDocument()
    expect(screen.getByText('RULE014')).toBeInTheDocument()
    expect(screen.getByText('RULE006')).toBeInTheDocument()
  })
})
