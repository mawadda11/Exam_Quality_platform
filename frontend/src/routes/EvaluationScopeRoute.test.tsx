import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EvaluationScopeRoute } from './EvaluationScopeRoute'

describe('EvaluationScopeRoute', () => {
  it('presents supported, limited, and planned checks as platform scope rather than exam results', () => {
    render(<EvaluationScopeRoute />)

    expect(screen.getByRole('heading', { level: 1, name: 'What the Platform Evaluates' }))
      .toBeInTheDocument()
    expect(screen.getByText('17')).toBeInTheDocument()
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Available checks' }))
      .toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Planned capabilities' }))
      .toBeInTheDocument()
    expect(screen.getByText(/planned checks are not treated as exam failures/i))
      .toBeInTheDocument()
    expect(screen.queryByText(/RULE\d{3}/)).not.toBeInTheDocument()
    expect(screen.queryByText(/v1\.0\.0|release/i)).not.toBeInTheDocument()
  })
})
