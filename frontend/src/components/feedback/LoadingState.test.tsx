import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { LoadingState } from './LoadingState'

describe('LoadingState', () => {
  it('renders default loading message', () => {
    render(<LoadingState />)
    expect(screen.getByText('Loading…')).toBeInTheDocument()
  })

  it('renders a custom message', () => {
    render(<LoadingState message="Fetching data…" />)
    expect(screen.getByText('Fetching data…')).toBeInTheDocument()
  })
})
