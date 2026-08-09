import type { RefObject } from 'react'
import { Drawer } from '../../components/ui/Drawer'
import { useI18n } from '../../i18n/I18nProvider'
import type { CloResponse, TopicResponse } from '../../types/api'
import {
  coverageStatus,
  facultyReason,
  uniqueTargets,
  type QuestionRelationshipRow,
  type RelationshipJudgment,
} from './AlignmentCoverageSection'
import { StatusBadge } from './StatusBadge'

interface QuestionRelationshipDrawerProps {
  row: QuestionRelationshipRow | null
  clos: CloResponse[]
  topics: TopicResponse[]
  onClose: () => void
  returnFocusRef?: RefObject<HTMLElement | null>
}

export function QuestionRelationshipDrawer({
  row,
  clos,
  topics,
  onClose,
  returnFocusRef,
}: QuestionRelationshipDrawerProps) {
  const { locale, t } = useI18n()

  const renderTargets = (
    judgments: RelationshipJudgment[],
    kind: 'clo' | 'topic',
  ) => {
    const targets = uniqueTargets(judgments)
    if (targets.length === 0) return <p>{t('None')}</p>

    return (
      <ul className="drawer-finding-list">
        {targets.map((target) => {
          const relevant = judgments.filter((judgment) =>
            judgment.targets.some((item) => item.id === target.id),
          )
          const record =
            kind === 'clo'
              ? clos.find((item) => item.code === target.item_reference)
              : topics.find(
                  (item) =>
                    item.code === target.item_reference ||
                    item.text === target.item_reference,
                )
          const identifier =
            kind === 'clo'
              ? (record as CloResponse | undefined)?.code ?? target.item_reference
              : (record as TopicResponse | undefined)?.code ?? target.item_reference
          const text = record?.text ?? target.item_reference

          return (
            <li key={target.id} className="drawer-finding-item">
              <div className="drawer-finding-header">
                <strong>
                  <bdi>{identifier}</bdi>
                </strong>
                <StatusBadge status={coverageStatus(relevant)} />
              </div>
              <p dir="auto">{text}</p>
              <p dir="auto">
                <strong>{t('Relationship reason')}:</strong>{' '}
                {relevant
                  .map((judgment) =>
                    facultyReason(judgment.status, judgment.reasoning, locale, t),
                  )
                  .join(' ')}
              </p>
            </li>
          )
        })}
      </ul>
    )
  }

  return (
    <Drawer
      isOpen={row !== null}
      onClose={onClose}
      titleId="question-mapping-details-title"
      returnFocusRef={returnFocusRef}
      title={
        <>
          {t('Question')} <bdi>{row?.questionReference}</bdi>
        </>
      }
    >
      {row && (
        <>
          <section className="ui-drawer-section">
            <p dir="auto">
              {row.question?.question_text ?? t('Question text is unavailable.')}
            </p>
            <p>
              {t('Marks')}: {row.question?.marks ?? '—'} · {t('Page')}{' '}
              {row.question?.page_number ?? row.sourceEvidence?.page_number ?? '—'}
            </p>
          </section>

          <section className="ui-drawer-section">
            <h3>{t('Suggested CLO')}</h3>
            {renderTargets(row.cloJudgments, 'clo')}
          </section>

          <section className="ui-drawer-section">
            <h3>{t('Suggested Course Topic')}</h3>
            {renderTargets(row.topicJudgments, 'topic')}
          </section>

        </>
      )}
    </Drawer>
  )
}
