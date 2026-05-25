import { useState } from 'react'

import { RequirePermission } from '../../../auth/RequirePermission'
import { EmptyState } from '../../../components/feedback/EmptyState'
import { useDeleteCaseLink } from '../hooks'
import type { ArrowLinkRead } from '../types'

export function LinkList({
  caseId,
  links,
}: {
  caseId: number
  links: ArrowLinkRead[]
}) {
  const deleteMutation = useDeleteCaseLink(caseId)
  const [activeLinkId, setActiveLinkId] = useState<number | null>(null)

  if (links.length === 0) {
    return (
      <EmptyState
        title="No links yet"
        description="Create the first directional link for this case network."
      />
    )
  }

  async function handleDelete(linkId: number) {
    setActiveLinkId(linkId)
    try {
      await deleteMutation.mutateAsync(linkId)
    } finally {
      setActiveLinkId(null)
    }
  }

  return (
    <div className="panel stack-sm">
      <div>
        <p className="eyebrow">Links</p>
        <h2>Arrow links</h2>
      </div>

      <ul className="list-reset stack-sm">
        {links.map((link) => (
          <li className="list-row" key={link.id}>
            <div>
              <strong>
                {link.from_ref} → {link.to_ref}
              </strong>
            </div>

            <RequirePermission permission="can_delete_records">
              <button
                className="button button-danger"
                type="button"
                onClick={() => void handleDelete(link.id)}
                disabled={deleteMutation.isPending && activeLinkId === link.id}
              >
                {deleteMutation.isPending && activeLinkId === link.id
                  ? 'Deleting…'
                  : 'Delete'}
              </button>
            </RequirePermission>
          </li>
        ))}
      </ul>

      {deleteMutation.isError ? (
        <p className="error-text">{deleteMutation.error.message}</p>
      ) : null}
    </div>
  )
}
