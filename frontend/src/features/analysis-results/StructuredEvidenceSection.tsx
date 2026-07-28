import { useEffect, useState } from 'react'
import {
  listDocumentReferences,
  listSupportingMaterialAnnotations,
  listSupportingMaterials,
} from '../../api/analyses'
import { Card } from '../../components/ui/Card'
import { OriginalTextDisclosure } from '../../components/ui/OriginalTextDisclosure'
import { PageState } from '../../components/ui/PageState'
import { useI18n } from '../../i18n/I18nProvider'
import { localizeInterfaceError } from '../../i18n/localizeError'
import type {
  DocumentReferenceResponse,
  SupportingMaterialAnnotationResponse,
  SupportingMaterialResponse,
} from '../../types/api'

interface StructuredData {
  materials: SupportingMaterialResponse[]
  annotations: SupportingMaterialAnnotationResponse[]
  references: DocumentReferenceResponse[]
}

export function StructuredEvidenceSection({ analysisId }: { analysisId: string }) {
  const { locale, t } = useI18n()
  const [data, setData] = useState<StructuredData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([
      listSupportingMaterials(analysisId),
      listSupportingMaterialAnnotations(analysisId),
      listDocumentReferences(analysisId),
    ])
      .then(([materials, annotations, references]) => {
        if (!cancelled) setData({ materials, annotations, references })
      })
      .catch((loadError: unknown) => {
        if (!cancelled) {
          setError(
            localizeInterfaceError(
              loadError,
              locale,
              t,
              'Could not load supporting-material evidence.',
            ),
          )
        }
      })
    return () => {
      cancelled = true
    }
  }, [analysisId, locale, t])

  if (error) {
    return (
      <PageState
        state="error"
        title={t('Could not load supporting-material evidence')}
        message={error}
      />
    )
  }
  if (!data) {
    return (
      <PageState
        state="loading"
        title={t('Loading supporting-material evidence')}
        message={t('Retrieving figures, tables, code blocks, and explicit references…')}
      />
    )
  }
  if (
    data.materials.length === 0 &&
    data.annotations.length === 0 &&
    data.references.length === 0
  ) {
    return (
      <PageState
        state="empty"
        title={t('No structured supporting material')}
        message={t('No figures, tables, code blocks, or explicit references were extracted.')}
      />
    )
  }

  return (
    <div className="results-section-stack structured-evidence-section">
      <div className="results-section-heading">
        <div>
          <h2>{t('Supporting Materials & References')}</h2>
          <p>
            {t(
              'Exact labels and explicit references determine verified associations. Proximity is shown only as supporting audit evidence.',
            )}
          </p>
        </div>
      </div>

      <section>
        <h3>{t('Supporting materials')} ({data.materials.length})</h3>
        <div className="result-card-grid">
          {data.materials.map((item) => (
            <Card as="article" key={item.id}>
              <h4>{t(item.material_type.replace('_', ' '))}</h4>
              <dl>
                <div><dt>{t('Page')}</dt><dd>{item.page_number}</dd></div>
                <div><dt>{t('Extraction method')}</dt><dd>{t(item.extraction_method)}</dd></div>
                <div><dt>{t('Confidence')}</dt><dd>{Math.round(item.confidence * 100)}%</dd></div>
              </dl>
              {item.source_text && (
                locale === 'ar' ? (
                  <>
                    <p>{t('Original source content is preserved for audit.')}</p>
                    <OriginalTextDisclosure>
                      <pre>{item.source_text}</pre>
                    </OriginalTextDisclosure>
                  </>
                ) : (
                  <pre dir="auto">{item.source_text}</pre>
                )
              )}
            </Card>
          ))}
        </div>
      </section>

      <section>
        <h3>{t('Labels and captions')} ({data.annotations.length})</h3>
        <ul className="evidence-list">
          {data.annotations.map((item) => (
            <li className="evidence-item" key={item.id}>
              <strong>{t(item.annotation_type)}</strong>
              <span> · {t('Page')} {item.page_number}</span>
              <p dir="auto" className="bidi-plaintext">
                <bdi dir="auto">{item.original_text}</bdi>
              </p>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3>{t('Explicit references')} ({data.references.length})</h3>
        <ul className="evidence-list">
          {data.references.map((item) => (
            <li className="evidence-item" key={item.id}>
              <dl>
                <div><dt>{t('Target type')}</dt><dd>{t(item.target_type.replace('_', ' '))}</dd></div>
                <div><dt>{t('Page')}</dt><dd>{item.page_number}</dd></div>
                <div><dt>{t('Resolution')}</dt><dd>{t(item.resolution_status)}</dd></div>
                {locale !== 'ar' && (
                  <div><dt>{t('Target label')}</dt><dd dir="auto">{item.target_label}</dd></div>
                )}
                <div>
                  <dt>{t('Candidates')}</dt>
                  <dd>{item.association_candidates.length}</dd>
                </div>
              </dl>
              {locale === 'ar' ? (
                <>
                  <p>{t('Original reference wording is preserved for audit.')}</p>
                  <OriginalTextDisclosure>
                    <p dir="auto">{item.original_text}</p>
                    <p dir="auto">{item.target_label}</p>
                  </OriginalTextDisclosure>
                </>
              ) : (
                <p dir="auto">{item.original_text}</p>
              )}
              {item.association_candidates.length > 0 && (
                <details className="finding-audit-details">
                  <summary>{t('Audit details')}</summary>
                  <ul className="review-warning-list">
                    {item.association_candidates.map((candidate) => (
                      <li key={candidate.id}>
                        <strong>{t(candidate.basis)}</strong>
                        {' · '}
                        {candidate.selected ? t('Selected exact target') : t('Review candidate')}
                        {' · '}
                        {t('Confidence')} {Math.round(candidate.confidence * 100)}%
                        {candidate.proximity_distance !== null
                          ? ` · ${t('Distance')}: ${candidate.proximity_distance}`
                          : ''}
                        {candidate.review_revision_id
                          ? ` · ${t('Review revision')}`
                          : ` · ${t('Machine extraction')}`}
                        {' · '}
                        {t('Target identifier')}{': '}
                        <code>
                          {candidate.target_material_id ?? candidate.target_question_id}
                        </code>
                        {candidate.ambiguity_reason ? (
                          <span dir="auto">
                            {' · '}
                            {locale === 'ar'
                              ? t(
                                  candidate.basis === 'proximity_support'
                                    ? 'Proximity is supporting evidence only.'
                                    : 'Multiple exact targets share this label.',
                                )
                              : candidate.ambiguity_reason}
                          </span>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
              {item.association_candidates.some(
                (candidate) => candidate.basis === 'proximity_support',
              ) && (
                <p className="results-supporting-text">
                  {t('Proximity candidates are retained for review and never verify an association by themselves.')}
                </p>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
