import { useEffect, useState, type ReactNode } from 'react'
import {
  listDocumentReferences,
  listSupportingMaterialAnnotations,
  listSupportingMaterials,
} from '../../api/analyses'
import { Card } from '../../components/ui/Card'
import { PageState } from '../../components/ui/PageState'
import { useI18n } from '../../i18n/I18nProvider'
import { localizeInterfaceError } from '../../i18n/localizeError'
import type {
  DocumentReferenceResponse,
  SupportingMaterialAnnotationResponse,
  SupportingMaterialResponse,
} from '../../types/api'
import { MethodologyLink } from './MethodologyLink'

interface StructuredData {
  materials: SupportingMaterialResponse[]
  annotations: SupportingMaterialAnnotationResponse[]
  references: DocumentReferenceResponse[]
}

function OriginalDocumentDisclosure({
  children,
}: {
  children: ReactNode
}) {
  const { t } = useI18n()
  return (
    <details className="original-document-disclosure">
      <summary>{t('Original document excerpt')}</summary>
      <div className="original-document-content" dir="auto">
        {children}
      </div>
    </details>
  )
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
          <h2>{t('Materials & References')}</h2>
          <p>
            {t(
              'Review figures, tables, code blocks, labels, and references identified in the exam.',
            )}
          </p>
          <MethodologyLink anchor="evidence-traceability" />
        </div>
      </div>

      <section>
        <h3>{t('Supporting materials')} ({data.materials.length})</h3>
        <div className="result-card-grid">
          {data.materials.map((item) => (
            <Card as="article" key={item.id}>
              <h4>{t(item.material_type.replace('_', ' '))}</h4>
              <p>{t('Page')} {item.page_number}</p>
              {item.source_text && (
                <OriginalDocumentDisclosure>
                  <pre dir="auto">{item.source_text}</pre>
                </OriginalDocumentDisclosure>
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
              <div className="structured-evidence-heading">
                <strong>{t(item.annotation_type)}</strong>
                <span>{t('Page')} {item.page_number}</span>
              </div>
              <strong className="source-content-label">
                {t('Original document excerpt')}
              </strong>
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
          {data.references.map((item) => {
            const hasProximityOnly = item.association_candidates.some(
              (candidate) => candidate.basis === 'proximity_support',
            )
            const hasMultipleCandidates = item.association_candidates.length > 1
            return (
              <li className="evidence-item" key={item.id}>
                <dl>
                  <div>
                    <dt>{t('Referenced material')}</dt>
                    <dd>{t(item.target_type.replace('_', ' '))}</dd>
                  </div>
                  <div><dt>{t('Page')}</dt><dd>{item.page_number}</dd></div>
                  <div>
                    <dt>{t('Relationship status')}</dt>
                    <dd>{t(item.resolution_status)}</dd>
                  </div>
                  <div>
                    <dt>{t('Referenced label')}</dt>
                    <dd dir="auto">{item.target_label}</dd>
                  </div>
                  <div>
                    <dt>{t('Possible matches')}</dt>
                    <dd>{item.association_candidates.length}</dd>
                  </div>
                </dl>
                <strong className="source-content-label">
                  {t('Original document excerpt')}
                </strong>
                <p dir="auto">{item.original_text}</p>
                {hasMultipleCandidates && (
                  <p className="results-supporting-text">
                    {t(
                      'Multiple possible matches were found, so this reference remains unresolved.',
                    )}
                  </p>
                )}
                {hasProximityOnly && (
                  <p className="results-supporting-text">
                    {t(
                      'Nearby placement is supporting evidence only and does not verify a relationship by itself.',
                    )}
                  </p>
                )}
              </li>
            )
          })}
        </ul>
      </section>
    </div>
  )
}
