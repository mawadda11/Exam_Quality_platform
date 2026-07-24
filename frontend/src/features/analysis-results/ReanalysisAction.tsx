import { useState } from 'react'
import { createReanalysis } from '../../api/analyses'
import { ApiError } from '../../api/client'
import type { AnalysisResponse } from '../../types/api'

interface ReanalysisActionProps {
  analysisId: string
  onCreated: (reanalysis: AnalysisResponse) => void
}

/** "Create a linked reanalysis for a revised examination" (PRD). The
 * revised exam always has to be uploaded fresh (M10 decision) - this action
 * only creates the new, linked analysis; the upload flow for it happens
 * exactly like any other analysis once onCreated switches the view. */
export function ReanalysisAction({ analysisId, onCreated }: ReanalysisActionProps) {
  const [reuseTp153, setReuseTp153] = useState(true)
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleCreate(): Promise<void> {
    setIsCreating(true)
    setError(null)
    try {
      const reanalysis = await createReanalysis(analysisId, { reuse_tp153: reuseTp153 })
      onCreated(reanalysis)
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Could not create the reanalysis.')
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <div className="reanalysis-action">
      <h4>Revised Exam?</h4>
      <p>
        Create a linked reanalysis for a revised examination. This analysis and its report(s)
        stay exactly as they are.
      </p>
      <label className="reanalysis-reuse-option">
        <input
          type="checkbox"
          checked={reuseTp153}
          onChange={(e) => setReuseTp153(e.target.checked)}
        />
        Reuse the previous TP-153 (uncheck to upload a new one)
      </label>
      <button type="button" onClick={() => void handleCreate()} disabled={isCreating}>
        {isCreating ? 'Creating…' : 'Create Reanalysis'}
      </button>
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
