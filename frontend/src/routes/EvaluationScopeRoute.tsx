import { useEffect, useState, type ReactNode } from 'react'
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
import type { AcademicStatus } from '../types/api'

interface MethodologySectionProps {
  id: string
  title: string
  icon: string
  children: ReactNode
  className?: string
}

interface ScopeEntry {
  item: EvaluationScopeItem
  availability: 'available' | 'limited' | 'planned'
}

const QUICK_NAVIGATION = [
  ['evaluation-model', 'Evaluation model'],
  ['overall-score', 'Scoring'],
  ['analysis-workflow', 'Workflow'],
  ['evidence-traceability', 'Evidence'],
  ['what-we-evaluate', 'Available checks'],
  ['local-privacy', 'Privacy'],
  ['limitations', 'Limitations'],
  ['frequently-asked-questions', 'FAQ'],
] as const

const STATUS_EXPLANATIONS: Readonly<Record<AcademicStatus, string>> = {
  Satisfied:
    'The requirement is fully met based on sufficient supporting evidence.',
  'Partially Satisfied':
    'The requirement is partly met, with an evidenced gap that still needs attention.',
  'Not Satisfied':
    'Reliable evidence shows that the requirement is not met.',
  'Not Verified':
    'The evidence is missing, unreadable, conflicting, or insufficient for a judgment.',
  'Not Applicable':
    'The requirement does not apply to the context of this analysis.',
}

const SCORE_VALUE_LABELS: Readonly<
  Record<'Satisfied' | 'Partially Satisfied' | 'Not Satisfied', string>
> = {
  Satisfied: 'Satisfied = 1.0',
  'Partially Satisfied': 'Partially Satisfied = 0.5',
  'Not Satisfied': 'Not Satisfied = 0.0',
}

const SCORED_STATUSES = [
  'Satisfied',
  'Partially Satisfied',
  'Not Satisfied',
] as const

const WORKFLOW_STEPS = [
  'Enter the analysis information.',
  'Upload the exam and Course Specification.',
  'Validate uploaded documents.',
  'Review extracted questions, marks, and materials.',
  'Confirm or correct extracted evidence.',
  'Run the analysis.',
  'Review results, findings, and recommendations.',
  'Preview or download the report.',
] as const

const GOVERNANCE_PRINCIPLES = [
  'No academic result is produced without supporting evidence.',
  'CLOs come from the uploaded Course Specification and are not invented.',
  'Course topics come from the uploaded Course Specification.',
  'The original documents are not modified.',
  'Suggested relationships are analytical suggestions for faculty review.',
  'Derived information is not presented as an official quotation.',
  'Not Verified is used when evidence is missing or unreliable.',
  'Processing failure remains separate from academic evaluation status.',
  'Conclusions are limited to the uploaded exam and Course Specification.',
  'The analyzer does not issue accreditation, approval, or certification decisions.',
  'Recommendations support academic review and are not mandatory institutional decisions.',
  'Original evidence remains preserved; corrections create traceable revisions.',
] as const

const SCOPE_GROUP_DEFINITIONS = [
  {
    title: 'CLO and topic relationships',
    ruleIds: ['RULE001', 'RULE002', 'RULE007', 'RULE008'],
  },
  {
    title: 'Coverage',
    ruleIds: ['RULE005', 'RULE006', 'RULE009'],
  },
  {
    title: 'Questions and clarity',
    ruleIds: ['RULE003', 'RULE004', 'RULE011', 'RULE012', 'RULE013', 'RULE021'],
  },
  {
    title: 'Marks and structure',
    ruleIds: ['RULE017', 'RULE018', 'RULE019', 'RULE020'],
  },
  {
    title: 'Materials and references',
    ruleIds: ['RULE014', 'RULE015', 'RULE016', 'RULE022'],
  },
] as const

const FAQ_ITEMS = [
  {
    question: 'Why is a result marked Not Verified?',
    answer:
      'The available evidence was missing, unreadable, conflicting, or insufficient for a reliable judgment. The result is excluded from the score.',
  },
  {
    question: 'Why is a rule excluded from the score?',
    answer:
      'Not Verified and Not Applicable results are excluded from the denominator. Planned checks are not analysis results and are not scored.',
  },
  {
    question: 'Does the analyzer modify the Course Specification?',
    answer:
      'No. The original Course Specification remains unchanged, and source wording is preserved for traceability.',
  },
  {
    question: 'Are suggested CLO and topic relationships official?',
    answer:
      'No. They are analytical suggestions for faculty review and do not replace official Course Specification mappings.',
  },
  {
    question: 'Why can the overall score show Insufficient Evidence?',
    answer:
      'Insufficient Evidence is shown when no verified and applicable results are available for the score denominator.',
  },
  {
    question: 'Can I correct extracted questions or marks?',
    answer:
      'Yes. Corrections are saved as traceable review revisions while the original extracted evidence remains unchanged.',
  },
  {
    question: 'Can another faculty member access my analysis?',
    answer:
      'No. Each analysis is private to its authenticated owner.',
  },
  {
    question: 'Does the analyzer make accreditation decisions?',
    answer:
      'No. It supports academic review and does not approve, certify, or reject an exam.',
  },
  {
    question: 'What happens when I upload a revised exam?',
    answer:
      'Create a New Analysis for the revised exam. Each analysis and its reports are evaluated and stored independently.',
  },
] as const

function MethodologySection({
  id,
  title,
  icon,
  children,
  className = '',
}: MethodologySectionProps) {
  const { t } = useI18n()
  return (
    <Card
      as="section"
      className={`evaluation-scope-section methodology-section ${className}`}
      aria-labelledby={id}
    >
      <h2 id={id} className="methodology-section-heading" tabIndex={-1}>
        <span className="methodology-section-icon" aria-hidden="true">
          {icon}
        </span>
        <span>{t(title)}</span>
      </h2>
      {children}
    </Card>
  )
}

function AnchoredHeading({ id, children }: { id: string; children: ReactNode }) {
  return (
    <h3 id={id} className="methodology-anchored-heading" tabIndex={-1}>
      {children}
    </h3>
  )
}

function scopeGroups(): Array<{
  title: string
  items: ScopeEntry[]
}> {
  const entries = new Map<string, ScopeEntry>([
    ...SUPPORTED_EVALUATION_SCOPE.map(
      (item) =>
        [item.ruleId, { item, availability: 'available' }] as const,
    ),
    ...LIMITED_EVALUATION_SCOPE.map(
      (item) => [item.ruleId, { item, availability: 'limited' }] as const,
    ),
    ...PLANNED_EVALUATION_SCOPE.map(
      (item) => [item.ruleId, { item, availability: 'planned' }] as const,
    ),
  ])

  return SCOPE_GROUP_DEFINITIONS.map((group) => ({
    title: group.title,
    items: group.ruleIds.flatMap((ruleId) => {
      const entry = entries.get(ruleId)
      return entry ? [entry] : []
    }),
  }))
}

function EvaluationScopeGroups() {
  const { t } = useI18n()

  return (
    <div className="methodology-scope-accordions">
      {scopeGroups().map((group, index) => (
        <details
          className="methodology-scope-accordion"
          key={group.title}
          open={index === 0}
        >
          <summary>
            <span>{t(group.title)}</span>
            <span className="methodology-scope-count">
              {group.items.length} {t('checks')}
            </span>
          </summary>
          <ul className="evaluation-scope-list">
            {group.items.map(({ item, availability }) => (
              <li key={item.ruleId}>
                <div>
                  <h3>{t(item.title)}</h3>
                  <p>{t(item.description)}</p>
                </div>
                {availability === 'limited' && (
                  <span className="methodology-scope-badge methodology-scope-badge--limited">
                    {t('Defined limitation')}
                  </span>
                )}
                {availability === 'planned' && (
                  <span className="methodology-scope-badge methodology-scope-badge--planned">
                    {t('Planned, not scored')}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </details>
      ))}
    </div>
  )
}

function MethodologyFaq() {
  const { t } = useI18n()
  const [openQuestion, setOpenQuestion] = useState<string | null>(
    FAQ_ITEMS[0].question,
  )

  return (
    <div className="methodology-faq">
      {FAQ_ITEMS.map(({ question, answer }, index) => {
        const isOpen = openQuestion === question
        const triggerId = `methodology-faq-trigger-${index}`
        const panelId = `methodology-faq-panel-${index}`

        return (
          <section className="methodology-faq-item" key={question}>
            <h3>
              <button
                id={triggerId}
                type="button"
                aria-expanded={isOpen}
                aria-controls={panelId}
                onClick={() =>
                  setOpenQuestion((current) =>
                    current === question ? null : question,
                  )
                }
              >
                <span>{t(question)}</span>
                <span aria-hidden="true">{isOpen ? '−' : '+'}</span>
              </button>
            </h3>
            <div
              id={panelId}
              role="region"
              aria-labelledby={triggerId}
              hidden={!isOpen}
            >
              <p>{t(answer)}</p>
            </div>
          </section>
        )
      })}
    </div>
  )
}

export function EvaluationScopeRoute() {
  const { locale, t } = useI18n()
  const location = useLocation()

  useEffect(() => {
    const id = decodeURIComponent(location.hash.replace(/^#/, ''))
    if (!id) return
    const target = document.getElementById(id)
    if (!target) return
    target.focus()
    target.scrollIntoView?.({ block: 'start' })
  }, [location.hash])

  function focusAnchor(id: string): void {
    window.setTimeout(() => {
      const target = document.getElementById(id)
      target?.focus({ preventScroll: true })
      target?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
    }, 0)
  }

  return (
    <div className="route-stack evaluation-scope-route">
      <PageHeader
        title={t('Methodology & Help')}
        description={t(
          'Understand what the Exam Quality Analyzer evaluates, how results are determined, and how to review the supporting evidence.',
        )}
      />

      <aside className="methodology-intro-note" aria-label={t('Methodology note')}>
        <span className="methodology-intro-icon" aria-hidden="true">i</span>
        <p>
          {t(
            'Checks are applied only when evidence is sufficient. Unavailable or planned checks are not treated as exam failures. The analyzer supports academic review and does not issue accreditation decisions.',
          )}
        </p>
      </aside>

      <nav className="methodology-contents" aria-label={t('Quick navigation')}>
        <ul>
          {QUICK_NAVIGATION.map(([id, label]) => (
            <li key={id}>
              <a href={`#${id}`} onClick={() => focusAnchor(id)}>
                {t(label)}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <MethodologySection
        id="evaluation-model"
        title="Evaluation Status Model"
        icon="✓"
      >
        <p className="methodology-section-intro">
          {t(
            'Every applied check returns one academic status supported by the available evidence.',
          )}
        </p>
        <div className="methodology-status-grid">
          {FINDING_STATUSES.map((status) => (
            <article
              className="methodology-status-card"
              data-testid="methodology-status-card"
              key={status}
            >
              <StatusBadge status={status} />
              <p>{t(STATUS_EXPLANATIONS[status])}</p>
            </article>
          ))}
        </div>
        <span id="academic-statuses" className="methodology-anchor-alias" tabIndex={-1} />
      </MethodologySection>

      <MethodologySection id="overall-score" title="Scoring Policy" icon="%">
        <p className="methodology-section-intro">
          {t(
            'The Overall Exam Quality Score includes only verified and applicable results.',
          )}
        </p>
        <div
          className="methodology-formula"
          dir={locale === 'ar' ? 'rtl' : 'ltr'}
          aria-label={t(
            'Overall Score equals the sum of scored status values divided by the number of verified and applicable results, multiplied by 100.',
          )}
        >
          <span className="methodology-formula-name">{t('Overall Score')}</span>
          <span aria-hidden="true">=</span>
          <span className="methodology-formula-fraction">
            <span>{t('Sum of scored status values')}</span>
            <span>{t('Number of verified and applicable results')}</span>
          </span>
          <span aria-hidden="true">×</span>
          <bdi>100</bdi>
        </div>
        <ul className="methodology-policy-list">
          {SCORED_STATUSES.map((status) => (
            <li key={status}>
              <StatusBadge status={status} />
              <strong>{t(SCORE_VALUE_LABELS[status])}</strong>
              <span>{t(scoreImpactMessage(status))}</span>
            </li>
          ))}
          <li>
            <span>
              <strong>{t('Not Verified')} / {t('Not Applicable')}:</strong>{' '}
              {t('Excluded from the score denominator.')}
            </span>
          </li>
          <li>
            <span>
              <strong>{t('Zero denominator')}:</strong>{' '}
              {t('The score is shown as Insufficient Evidence.')}
            </span>
          </li>
        </ul>
        <p className="methodology-no-weights">
          <strong>{t('No weighting is applied')}:</strong>{' '}
          {t(
            'The score uses no rule weights, dimension weights, severity weights, or readiness bands.',
          )}
        </p>
      </MethodologySection>

      <MethodologySection
        id="analysis-workflow"
        title="Analysis Workflow"
        icon="1"
      >
        <ol className="methodology-steps">
          {WORKFLOW_STEPS.map((step, index) => (
            <li key={step}>
              <span className="methodology-step-number" aria-hidden="true">
                {index + 1}
              </span>
              <span>{t(step)}</span>
            </li>
          ))}
        </ol>
      </MethodologySection>

      <MethodologySection
        id="evidence-traceability"
        title="Evidence and Governance Principles"
        icon="◇"
      >
        <AnchoredHeading id="evaluation-methods">
          {t('Evaluation methods')}
        </AnchoredHeading>
        <div className="methodology-methods">
          <div>
            <h4>{t('Rule-based checks')}</h4>
            <p>
              {t(
                'Use defined rules and confirmed evidence for conditions that can be checked directly, such as totals or numbering.',
              )}
            </p>
          </div>
          <div>
            <h4>{t('Semantic content analysis')}</h4>
            <p>
              {t(
                'Reviews meaning-based relationships using confirmed question and Course Specification evidence. Judgments remain advisory and traceable.',
              )}
            </p>
          </div>
        </div>
        <h3 className="methodology-anchored-heading">
          {t('Evidence traceability')}
        </h3>
        <p>
          {t(
            'Each finding can retain source document, page, reference, excerpt, and governed audit references. Original source wording remains available when translated presentation text is shown.',
          )}
        </p>
        <p className="methodology-technical-note">
          {t(
            'Technical version details are retained internally for reproducibility and support.',
          )}
        </p>
        <ul className="methodology-principles">
          {GOVERNANCE_PRINCIPLES.map((principle) => (
            <li key={principle}>
              <span aria-hidden="true">✓</span>
              <span>{t(principle)}</span>
            </li>
          ))}
        </ul>
      </MethodologySection>

      <MethodologySection
        id="what-we-evaluate"
        title="What the analyzer evaluates"
        icon="✓"
      >
        <p className="methodology-section-intro">
          {t(
            'Defined exam-quality checks are applied only when the uploaded documents provide sufficient confirmed evidence.',
          )}
        </p>
        <div
          className="evaluation-scope-summary"
          aria-label={t('Current evaluation scope summary')}
        >
          <article>
            <strong>{SUPPORTED_EVALUATION_SCOPE.length}</strong>
            <span>{t('Available checks')}</span>
          </article>
          <article>
            <strong>{LIMITED_EVALUATION_SCOPE.length}</strong>
            <span>{t('Checks with defined limitations')}</span>
          </article>
          <article>
            <strong>{PLANNED_EVALUATION_SCOPE.length}</strong>
            <span>{t('Planned checks')}</span>
          </article>
        </div>
        <EvaluationScopeGroups />
      </MethodologySection>

      <MethodologySection
        id="required-documents"
        title="Required Documents and Extraction Review"
        icon="▤"
      >
        <div className="methodology-two-column methodology-document-review">
          <div>
            <h3>{t('Required documents')}</h3>
            <ul>
              <li>
                <strong>{t('Exam PDF')}</strong>
                <span>
                  {t(
                    'Provides the questions, marks, instructions, and visible supporting materials.',
                  )}
                </span>
              </li>
              <li>
                <strong>{t('Populated Course Specification / TP-153')}</strong>
                <span>
                  {t(
                    'Provides the course learning outcomes, topics, and assessment information when present and readable.',
                  )}
                </span>
              </li>
            </ul>
          </div>
          <div>
            <AnchoredHeading id="extraction-review">
              {t('What to review')}
            </AnchoredHeading>
            <ul>
              <li>{t('Review extracted questions.')}</li>
              <li>{t('Verify question marks.')}</li>
              <li>{t('Verify figures, tables, diagrams, and code blocks.')}</li>
              <li>{t('Correct extraction errors before analysis.')}</li>
              <li>
                {t(
                  'Preserve original evidence and record corrections as revisions.',
                )}
              </li>
            </ul>
          </div>
        </div>
        <p>
          {t(
            'Both documents are required. Missing, unreadable, or unconfirmed source content is never invented.',
          )}
        </p>
        <p className="methodology-traceability-note">
          {t(
            'Extraction Review corrects the faculty-facing record without changing the original machine-extracted audit evidence.',
          )}
        </p>
      </MethodologySection>

      <MethodologySection
        id="not-verified"
        title="Evidence Reliability and Excluded Statuses"
        icon="?"
      >
        <div className="methodology-reliability-statuses">
          <article>
            <StatusBadge status="Not Verified" />
            <p>
              {t(
                'Evidence is missing, unreadable, conflicting, or insufficient for a reliable judgment.',
              )}
            </p>
          </article>
          <article>
            <StatusBadge status="Not Applicable" />
            <p>
              {t(
                'The requirement does not apply to the context of the uploaded exam.',
              )}
            </p>
          </article>
        </div>
        <p>
          {t(
            'Both statuses are excluded from the score denominator and are not treated as exam failures.',
          )}
        </p>
        <AnchoredHeading id="confidence">
          {t('Confidence and evidence reliability')}
        </AnchoredHeading>
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
        <ul className="methodology-compact-list">
          <li>
            {t(
              'Low-confidence semantic evidence must not produce a positive or negative academic judgment.',
            )}
          </li>
          <li>
            {t(
              'A system or processing failure is not an academic exam result.',
            )}
          </li>
        </ul>
      </MethodologySection>

      <MethodologySection
        id="suggested-relationships"
        title="Suggested Relationships"
        icon="↔"
        className="methodology-section--compact"
      >
        <p>
          {t(
            'Suggested CLO and topic relationships are analytical suggestions based on uploaded evidence. They are not official Course Specification mappings and never modify the original document.',
          )}
        </p>
        <p>
          {t(
            'Use View mapping details to review the question text, CLO, course topic, explanation, and supporting evidence.',
          )}
        </p>
      </MethodologySection>

      <MethodologySection
        id="local-privacy"
        title="Privacy and Document Processing"
        icon="◈"
        className="methodology-section--compact"
      >
        <ul className="methodology-compact-list">
          <li>{t('Analyses are private to the authenticated owner.')}</li>
          <li>
            {t('Documents are processed for the requested analysis.')}
          </li>
          <li>
            {t("Users cannot access another owner's analysis.")}
          </li>
          <li>{t('Original evidence is preserved.')}</li>
          <li>
            {t(
              'Technical logs must not expose document contents or secrets.',
            )}
          </li>
        </ul>
      </MethodologySection>

      <MethodologySection
        id="reports-reanalysis"
        title="Reports and New Analysis"
        icon="↻"
        className="methodology-section--compact"
      >
        <p>
          {t(
            'Reports preserve the selected language, score summary, findings, recommendations, evidence context, and analysis version available when the report is generated.',
          )}
        </p>
        <p>
          {t(
            'To evaluate a revised exam, create a New Analysis. Each analysis and its reports are evaluated and stored independently.',
          )}
        </p>
      </MethodologySection>

      <MethodologySection
        id="limitations"
        title="Limitations and Non-goals"
        icon="!"
        className="methodology-limitations"
      >
        <ul className="methodology-compact-list">
          <li>
            {t(
              'The analyzer supports exam-quality review; it does not evaluate full program accreditation.',
            )}
          </li>
          <li>
            {t(
              'Results depend on the quality and completeness of uploaded documents.',
            )}
          </li>
          <li>
            {t('Unreadable or missing evidence may produce Not Verified.')}
          </li>
          <li>{t('Suggested relationships require faculty review.')}</li>
          <li>
            {t('The analyzer does not approve, certify, or reject an exam.')}
          </li>
          <li>
            {t('Planned capabilities are not counted as exam failures.')}
          </li>
          <li>
            {t(
              'Results apply only to the uploaded exam and Course Specification.',
            )}
          </li>
        </ul>
      </MethodologySection>

      <MethodologySection
        id="frequently-asked-questions"
        title="Frequently Asked Questions"
        icon="?"
      >
        <MethodologyFaq />
      </MethodologySection>
    </div>
  )
}
