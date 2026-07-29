import { useEffect, type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { Card } from '../components/ui/Card'
import { PageHeader } from '../components/ui/PageHeader'
import {
  LIMITED_EVALUATION_SCOPE,
  PLANNED_EVALUATION_SCOPE,
  SUPPORTED_EVALUATION_SCOPE,
  type EvaluationScopeItem,
} from '../features/platform-scope/platformScopeData'
import {
  FINDING_STATUSES,
  scoreImpactMessage,
} from '../features/analysis-results/findingPresentation'
import { StatusBadge } from '../features/analysis-results/StatusBadge'
import { useI18n } from '../i18n/I18nProvider'

interface MethodologySectionProps {
  id: string
  title: string
  children: ReactNode
  className?: string
}

function MethodologySection({
  id,
  title,
  children,
  className = '',
}: MethodologySectionProps) {
  const { t } = useI18n()
  return (
    <Card
      as="section"
      className={`evaluation-scope-section methodology-section ${className}`}
    >
      <h2 id={id} tabIndex={-1}>{t(title)}</h2>
      {children}
    </Card>
  )
}

function ScopeList({ items }: { items: EvaluationScopeItem[] }) {
  const { t } = useI18n()
  return (
    <ul className="evaluation-scope-list">
      {items.map((item) => (
        <li key={item.ruleId}>
          <div>
            <h3>{t(item.title)}</h3>
            <p>{t(item.description)}</p>
          </div>
        </li>
      ))}
    </ul>
  )
}

const METHODOLOGY_LINKS = [
  ['what-we-evaluate', 'What the platform evaluates'],
  ['required-documents', 'Required documents'],
  ['analysis-workflow', 'Analysis workflow'],
  ['extraction-review', 'Extraction Review'],
  ['evaluation-methods', 'Evaluation methods'],
  ['academic-statuses', 'Academic statuses'],
  ['overall-score', 'Overall score'],
  ['not-verified', 'Not Verified and Not Applicable'],
  ['confidence', 'Confidence and evidence reliability'],
  ['evidence-traceability', 'Evidence traceability'],
  ['suggested-relationships', 'Suggested relationships'],
  ['local-privacy', 'Privacy and document processing'],
  ['reports-reanalysis', 'Reports and reanalysis'],
  ['limitations', 'Limitations and non-goals'],
  ['frequently-asked-questions', 'Frequently asked questions'],
] as const

export function EvaluationScopeRoute() {
  const { t } = useI18n()
  const location = useLocation()

  useEffect(() => {
    const id = decodeURIComponent(location.hash.replace(/^#/, ''))
    if (!id) return
    const target = document.getElementById(id)
    if (!target) return
    target.focus()
    target.scrollIntoView?.({ block: 'start' })
  }, [location.hash])

  return (
    <div className="route-stack route-content-wide evaluation-scope-route">
      <PageHeader
        title={t('Methodology & Help')}
        description={t(
          'Understand what the Exam Quality Analyzer evaluates, how results are determined, and how to review evidence. Planned checks are not treated as exam failures and do not reduce the score.',
        )}
      />

      <nav className="methodology-contents" aria-label={t('On this page')}>
        <strong>{t('On this page')}</strong>
        <ul>
          {METHODOLOGY_LINKS.map(([id, label]) => (
            <li key={id}>
              <a
                href={`#${id}`}
                onClick={() => {
                  window.setTimeout(() => {
                    document.getElementById(id)?.focus()
                  }, 0)
                }}
              >
                {t(label)}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <MethodologySection id="what-we-evaluate" title="What the platform evaluates">
        <p>
          {t(
            'The analyzer applies defined exam-quality checks only when the uploaded documents provide sufficient evidence. Unavailable and planned capabilities remain separate from an individual exam result.',
          )}
        </p>
        <div
          className="evaluation-scope-summary"
          aria-label={t('Current evaluation scope summary')}
        >
          <Card as="article">
            <strong>{SUPPORTED_EVALUATION_SCOPE.length}</strong>
            <span>{t('Available checks')}</span>
          </Card>
          <Card as="article">
            <strong>{LIMITED_EVALUATION_SCOPE.length}</strong>
            <span>{t('Check with a defined limitation')}</span>
          </Card>
          <Card as="article">
            <strong>{PLANNED_EVALUATION_SCOPE.length}</strong>
            <span>{t('Planned checks')}</span>
          </Card>
        </div>

        <div className="methodology-scope-group">
          <h3>{t('Available checks')}</h3>
          <p>
            {t(
              'These checks can produce an academic result when the uploaded Exam and Course Specification contain sufficient confirmed evidence.',
            )}
          </p>
          <ScopeList items={SUPPORTED_EVALUATION_SCOPE} />
        </div>
        <div className="methodology-scope-group methodology-scope-group--limited">
          <h3>{t('Available with a defined limitation')}</h3>
          <p>
            {t(
              'The documented limitation is preserved; the analyzer does not invent an academic threshold.',
            )}
          </p>
          <ScopeList items={LIMITED_EVALUATION_SCOPE} />
        </div>
        <div className="methodology-scope-group methodology-scope-group--planned">
          <h3>{t('Planned capabilities')}</h3>
          <p>
            {t(
              'Planned capabilities are shown for transparency. They are not scored and are not presented as failures.',
            )}
          </p>
          <ScopeList items={PLANNED_EVALUATION_SCOPE} />
        </div>
      </MethodologySection>

      <MethodologySection id="required-documents" title="Required documents">
        <div className="methodology-two-column">
          <div>
            <h3>{t('Exam PDF')}</h3>
            <p>
              {t(
                'Provides question text, marks, instructions, figures, tables, code blocks, and other evidence visible in the exam.',
              )}
            </p>
          </div>
          <div>
            <h3>{t('Course Specification PDF')}</h3>
            <p>
              {t(
                'Provides official course information such as CLOs, topics, and assessment methods when they are present and readable.',
              )}
            </p>
          </div>
        </div>
        <p>
          {t(
            'Both documents are required. Missing, unreadable, or unconfirmed source content is never invented.',
          )}
        </p>
      </MethodologySection>

      <MethodologySection id="analysis-workflow" title="Analysis workflow">
        <ol className="methodology-steps">
          <li><strong>{t('Upload')}</strong><span>{t('Add the Exam and Course Specification PDFs.')}</span></li>
          <li><strong>{t('Extract')}</strong><span>{t('The analyzer identifies source records and their document locations for review.')}</span></li>
          <li><strong>{t('Review')}</strong><span>{t('Correct transcription and inclusion before evaluation.')}</span></li>
          <li><strong>{t('Evaluate')}</strong><span>{t('The available checks use the confirmed evidence.')}</span></li>
          <li><strong>{t('Review results')}</strong><span>{t('Start with the result, reason, score effect, and recommendation; open evidence as needed.')}</span></li>
          <li><strong>{t('Report')}</strong><span>{t('Generate a language-specific report for the completed analysis.')}</span></li>
        </ol>
      </MethodologySection>

      <MethodologySection id="extraction-review" title="Extraction Review">
        <p>
          {t(
            'Extraction Review is a transcription checkpoint. Confirm what is visibly present, correct reading-order text, and exclude records that are not academic content.',
          )}
        </p>
        <p>
          {t(
            'A review revision does not approve academic alignment, create missing course information, or alter the original machine-extracted audit record.',
          )}
        </p>
      </MethodologySection>

      <MethodologySection id="evaluation-methods" title="Evaluation methods">
        <div className="methodology-two-column">
          <div>
            <h3>{t('Rule-based checks')}</h3>
            <p>
              {t(
                'Use defined rules and confirmed evidence for conditions that can be checked directly, such as totals or numbering.',
              )}
            </p>
          </div>
          <div>
            <h3>{t('Semantic content analysis')}</h3>
            <p>
              {t(
                'Reviews meaning-based relationships using the confirmed question and Course Specification evidence. These judgments remain advisory and traceable.',
              )}
            </p>
          </div>
        </div>
        <p className="results-supporting-text">
          {t(
            'Technical version details are retained internally for reproducibility and support.',
          )}
        </p>
      </MethodologySection>

      <MethodologySection id="academic-statuses" title="Academic statuses">
        <ul className="methodology-status-list">
          {FINDING_STATUSES.map((status) => (
            <li key={status}>
              <StatusBadge status={status} />
              <span>{t(scoreImpactMessage(status))}</span>
            </li>
          ))}
        </ul>
      </MethodologySection>

      <MethodologySection id="overall-score" title="Overall score">
        <p>
          {t(
            'The Overall Exam Quality Score summarizes applicable checks that produced a reliable judgment. It does not include planned capabilities.',
          )}
        </p>
        <p>
          {t(
            'Satisfied results are included fully, Partially Satisfied results receive partial credit, and Not Satisfied results remain unmet requirements in the score.',
          )}
        </p>
      </MethodologySection>

      <MethodologySection id="not-verified" title="Not Verified and Not Applicable">
        <p>
          <strong>{t('Not Verified')}:</strong>{' '}
          {t(
            'The evidence was insufficient for a reliable judgment. This is a request for evidence or review, not a failed requirement.',
          )}
        </p>
        <p>
          <strong>{t('Not Applicable')}:</strong>{' '}
          {t(
            'The requirement does not apply to this analysis. The reason remains visible for traceability.',
          )}
        </p>
        <p>
          {t(
            'Both statuses are excluded from the score calculation according to the approved scoring policy.',
          )}
        </p>
      </MethodologySection>

      <MethodologySection id="confidence" title="Confidence and evidence reliability">
        <p>
          {t(
            'Extraction confidence estimates how reliably source content was read. Evidence reliability describes confidence in an evaluation judgment.',
          )}
        </p>
        <p>
          {t(
            'Neither measure is a satisfaction level. A highly reliable judgment can still be Satisfied, Partially Satisfied, or Not Satisfied.',
          )}
        </p>
      </MethodologySection>

      <MethodologySection id="evidence-traceability" title="Evidence traceability">
        <p>
          {t(
            'Each finding can retain its source document, page, reference, and excerpt. Original document wording remains available when translated presentation text is shown.',
          )}
        </p>
        <p>
          {t(
            'Evidence disclosures preserve traceability without interrupting the primary faculty view.',
          )}
        </p>
      </MethodologySection>

      <MethodologySection id="suggested-relationships" title="Suggested relationships">
        <p>
          {t(
            'Question-to-CLO and question-to-topic relationships produced by the analysis are suggestions for faculty review. They are not official Course Specification mappings.',
          )}
        </p>
        <p>
          {t(
            'Suggested relationships do not overwrite source evidence. Question-level status, reason, and linked evidence remain available for review.',
          )}
        </p>
      </MethodologySection>

      <MethodologySection id="local-privacy" title="Privacy and document processing">
        <p>
          {t(
            'Document processing follows the privacy and security configuration approved for the deployed environment.',
          )}
        </p>
        <p>
          {t(
            'Only the evidence needed for the selected checks should be processed, and deployment approval remains an institutional responsibility.',
          )}
        </p>
      </MethodologySection>

      <MethodologySection id="reports-reanalysis" title="Reports and reanalysis">
        <p>
          {t(
            'Reports preserve the selected report language, score summary, findings, recommendations, evidence context, and analysis version information available at generation time.',
          )}
        </p>
        <p>
          {t(
            'Reanalysis creates a linked analysis record. It does not overwrite the historical result or its review history.',
          )}
        </p>
      </MethodologySection>

      <MethodologySection id="limitations" title="Limitations and non-goals">
        <ul>
          <li>{t('The analyzer supports faculty review; it does not replace academic judgment or institutional approval.')}</li>
          <li>{t('It does not invent missing CLOs, topics, mappings, evidence, standards, or academic thresholds.')}</li>
          <li>{t('Planned or unavailable checks are not converted into exam failures.')}</li>
          <li>{t('Source excerpts remain source evidence even when an Arabic explanation or translation is available.')}</li>
        </ul>
      </MethodologySection>

      <MethodologySection
        id="frequently-asked-questions"
        title="Frequently asked questions"
      >
        <div className="methodology-faq">
          <details>
            <summary>{t('Does Not Verified mean the exam failed?')}</summary>
            <p>{t('No. It means the available evidence was not sufficient for a reliable judgment, so the finding is excluded from the score.')}</p>
          </details>
          <details>
            <summary>{t('Can I correct extracted text?')}</summary>
            <p>{t('Yes. Save the correction as a review revision. The original machine-extracted record remains unchanged for audit.')}</p>
          </details>
          <details>
            <summary>{t('Are suggested CLO or topic relationships official?')}</summary>
            <p>{t('No. They are advisory relationships for faculty review and do not alter the Course Specification.')}</p>
          </details>
          <details>
            <summary>{t('Why can the report differ from a historical report?')}</summary>
            <p>{t('Each analysis and report retains its own version context. Reanalysis creates a linked record instead of replacing history.')}</p>
          </details>
        </div>
      </MethodologySection>
    </div>
  )
}
