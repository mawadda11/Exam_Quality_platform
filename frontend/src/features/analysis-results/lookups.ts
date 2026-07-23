import type { CloResponse, QuestionResponse, TopicResponse } from '../../types/api'

/** Deterministic display join keyed by the same codes Finding.evidence
 * items already carry (`item_reference` equals a CLO/topic `code` or a
 * question `number_label` - see backend/app/services/rules/clo_topic_coverage.py).
 * Built once per results load, not a new evaluation - just resolving a
 * code the rule engine already cited into its full extracted text. */
export interface EvidenceLookups {
  cloByCode: Map<string, CloResponse>
  topicByCode: Map<string, TopicResponse>
  questionByLabel: Map<string, QuestionResponse>
}

export const EMPTY_LOOKUPS: EvidenceLookups = {
  cloByCode: new Map(),
  topicByCode: new Map(),
  questionByLabel: new Map(),
}

export function buildLookups(
  clos: CloResponse[],
  topics: TopicResponse[],
  questions: QuestionResponse[],
): EvidenceLookups {
  return {
    cloByCode: new Map(clos.map((clo) => [clo.code, clo])),
    topicByCode: new Map(
      topics
        .filter((topic): topic is TopicResponse & { code: string } => topic.code !== null)
        .map((topic) => [topic.code, topic]),
    ),
    questionByLabel: new Map(questions.map((question) => [question.number_label, question])),
  }
}
