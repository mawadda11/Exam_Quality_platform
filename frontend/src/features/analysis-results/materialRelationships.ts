import type {
  DocumentReferenceResponse,
  ReferenceAssociationResponse,
  SupportingMaterialAnnotationResponse,
  SupportingMaterialResponse,
} from '../../types/api'

export type MaterialRelationshipResult =
  | 'linked'
  | 'missing'
  | 'ambiguous'
  | 'nearby'

export interface PhysicalMaterialView {
  material: SupportingMaterialResponse
  annotations: SupportingMaterialAnnotationResponse[]
  label: string | null
  caption: string | null
}

export interface MaterialRelationshipView {
  reference: DocumentReferenceResponse
  result: MaterialRelationshipResult
  exactCandidates: PhysicalMaterialView[]
  nearbyCandidates: PhysicalMaterialView[]
  matchedMaterial: PhysicalMaterialView | null
}

const LABEL_PREFIX =
  /^\s*[-–—]?\s*(?:(?:Fig(?:ure)?|Table|Code(?:\s+(?:Block|Listing))?)\s*(?:No\.?|Number)?|(?:الشكل|شكل|الجدول|جدول|الكود|المقطع\s+البرمجي)\s*(?:رقم)?)\s*[0-9٠-٩۰-۹]+\s*/iu

export function splitMaterialAnnotationText(value: string): {
  label: string | null
  remainder: string
} {
  const prefix = LABEL_PREFIX.exec(value)
  if (!prefix) return { label: null, remainder: value.trim() }
  const label = prefix[0].trim().replace(/^[-–—]\s*/u, '').replace(/[:.\-–—]\s*$/u, '')
  const remainder = value
    .slice(prefix[0].length)
    .replace(/^\s*[:.\-–—]\s*/u, '')
    .trim()
  return { label, remainder }
}

function materialPosition(item: SupportingMaterialResponse): number {
  const top = item.geometry?.top
  return typeof top === 'number' ? top : Number.MAX_SAFE_INTEGER
}

export function buildPhysicalMaterials(
  materials: SupportingMaterialResponse[],
  annotations: SupportingMaterialAnnotationResponse[],
): PhysicalMaterialView[] {
  return [...materials]
    .sort(
      (left, right) =>
        left.page_number - right.page_number ||
        materialPosition(left) - materialPosition(right) ||
        left.created_at.localeCompare(right.created_at) ||
        left.id.localeCompare(right.id),
    )
    .map((material) => {
      const materialAnnotations = annotations.filter(
        (annotation) => annotation.material_id === material.id,
      )
      const labelObservation = materialAnnotations.find(
        (annotation) => annotation.annotation_type === 'label',
      )
      const captionObservation = materialAnnotations.find(
        (annotation) => annotation.annotation_type === 'caption',
      )
      const labelParts = labelObservation
        ? splitMaterialAnnotationText(labelObservation.original_text)
        : null
      const captionParts = captionObservation
        ? splitMaterialAnnotationText(captionObservation.original_text)
        : null
      return {
        material,
        annotations: materialAnnotations,
        label: labelParts?.label ?? captionParts?.label ?? null,
        caption:
          captionParts?.remainder ||
          labelParts?.remainder ||
          material.source_text.trim() ||
          null,
      }
    })
}

function distinctMaterialCandidates(
  candidates: ReferenceAssociationResponse[],
  materialsById: Map<string, PhysicalMaterialView>,
  predicate: (candidate: ReferenceAssociationResponse) => boolean,
): PhysicalMaterialView[] {
  const result = new Map<string, PhysicalMaterialView>()
  for (const candidate of candidates) {
    if (!predicate(candidate) || !candidate.target_material_id) continue
    const material = materialsById.get(candidate.target_material_id)
    if (material) result.set(material.material.id, material)
  }
  return [...result.values()]
}

export function buildMaterialRelationship(
  reference: DocumentReferenceResponse,
  materials: PhysicalMaterialView[],
): MaterialRelationshipView {
  const materialsById = new Map(
    materials.map((material) => [material.material.id, material]),
  )
  const exactCandidates = distinctMaterialCandidates(
    reference.association_candidates,
    materialsById,
    (candidate) => candidate.exact_label_match,
  )
  const nearbyCandidates = distinctMaterialCandidates(
    reference.association_candidates,
    materialsById,
    (candidate) =>
      !candidate.exact_label_match && candidate.basis === 'proximity_support',
  )
  const selected = distinctMaterialCandidates(
    reference.association_candidates,
    materialsById,
    (candidate) => candidate.exact_label_match && candidate.selected,
  )

  let result: MaterialRelationshipResult
  if (reference.resolution_status === 'ambiguous' || exactCandidates.length > 1) {
    result = 'ambiguous'
  } else if (
    reference.resolution_status === 'resolved' &&
    exactCandidates.length === 1 &&
    selected.length === 1
  ) {
    result = 'linked'
  } else if (exactCandidates.length === 0 && nearbyCandidates.length > 0) {
    result = 'nearby'
  } else {
    result = 'missing'
  }

  return {
    reference,
    result,
    exactCandidates,
    nearbyCandidates,
    matchedMaterial:
      result === 'linked'
        ? selected[0]
        : result === 'nearby'
          ? nearbyCandidates[0]
          : null,
  }
}
