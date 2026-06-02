import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PageErrorBoundary } from './PageErrorBoundary'

function Bomb({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error('Test explosion')
  return <p>All good</p>
}

describe('PageErrorBoundary', () => {
  it('renders children when there is no error', () => {
    render(
      <PageErrorBoundary>
        <Bomb shouldThrow={false} />
      </PageErrorBoundary>,
    )
    expect(screen.getByText('All good')).toBeInTheDocument()
  })

  it('renders error fallback when a child throws', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <PageErrorBoundary>
        <Bomb shouldThrow={true} />
      </PageErrorBoundary>,
    )
    expect(screen.getByText('Test explosion')).toBeInTheDocument()
    expect(screen.getByText('Try again')).toBeInTheDocument()
    spy.mockRestore()
  })

  it('shows a Try again button in the error fallback', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <PageErrorBoundary>
        <Bomb shouldThrow={true} />
      </PageErrorBoundary>,
    )
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
    spy.mockRestore()
  })
})
