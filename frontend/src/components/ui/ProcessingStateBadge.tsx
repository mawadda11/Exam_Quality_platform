import type { ProcessingStage } from '../../types/api'

export function ProcessingStateBadge({ state }: { state: ProcessingStage }) {
  return (
    <span
      className="ui-processing-state-badge"
      data-processing-state={state}
      aria-label={`Processing state: ${state}`}
    >
      {state}
    </span>
  )
}
