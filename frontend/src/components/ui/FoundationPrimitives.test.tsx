import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { BrandMark } from './BrandMark'
import { Button } from './Button'
import { Card } from './Card'
import { PageHeader } from './PageHeader'
import { PageState } from './PageState'

describe('foundation primitives', () => {
  it('renders the product brand and a semantic page heading in a card', () => {
    render(
      <Card as="section">
        <BrandMark />
        <PageHeader
          eyebrow="Academic quality support"
          title="New Analysis"
          description="Upload the required documents."
          actions={<Button>Continue</Button>}
        />
      </Card>,
    )

    expect(screen.getByText('Exam Quality Analyzer')).toBeVisible()
    expect(screen.getByRole('heading', { level: 1, name: 'New Analysis' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Continue' })).toBeEnabled()
  })

  it('renders an accessible retry state', () => {
    render(
      <PageState
        state="error"
        title="Could not load analyses"
        message="Check the connection and retry."
        action={<Button>Retry</Button>}
      />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('Could not load analyses')
    expect(screen.getByRole('button', { name: 'Retry' })).toBeEnabled()
  })
})
