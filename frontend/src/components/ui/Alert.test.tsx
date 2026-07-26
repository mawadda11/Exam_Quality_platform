import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Alert, type AlertVariant } from './Alert'

const VARIANTS: AlertVariant[] = ['info', 'success', 'warning', 'error']

describe('Alert', () => {
  it.each(VARIANTS)('renders the %s variant with a visible label', (variant) => {
    render(<Alert variant={variant}>Details for this state.</Alert>)

    const role = variant === 'warning' || variant === 'error' ? 'alert' : 'status'
    const alert = screen.getByRole(role)
    expect(alert).toHaveClass(`ui-alert--${variant}`)
    expect(alert).toHaveTextContent(variant === 'info' ? 'Information' : new RegExp(variant, 'i'))
    expect(alert).toHaveTextContent('Details for this state.')
  })

  it('supports a contextual title', () => {
    render (
      <Alert variant="error" title="Upload rejected">
        The PDF could not be opened.
      </Alert>,
    )
    expect(screen.getByRole('alert')).toHaveTextContent('Upload rejected')
  })
})
