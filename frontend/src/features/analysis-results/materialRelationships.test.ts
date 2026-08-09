import { describe, expect, it } from 'vitest'
import type {
  DocumentReferenceResponse,
  SupportingMaterialAnnotationResponse,
  SupportingMaterialResponse,
} from '../../types/api'
import {
  buildMaterialRelationship,
  buildPhysicalMaterials,
} from './materialRelationships'

function material(
  id: string,
  page: number,
  top: number,
): SupportingMaterialResponse {
  return {
    id,
    analysis_id: 'analysis-1',
    question_id: null,
    source_document: 'exam',
    material_type: 'figure',
    page_number: page,
    source_text: '',
    geometry: { x0: 0, top, x1: 100, bottom: top + 50 },
    confidence: 1,
    extraction_method: 'direct_text',
    created_at: `2026-01-01T00:00:0${top}Z`,
  }
}

function annotation(
  id: string,
  materialId: string,
  type: 'label' | 'caption',
  text: string,
): SupportingMaterialAnnotationResponse {
  return {
    id,
    analysis_id: 'analysis-1',
    material_id: materialId,
    source_document: 'exam',
    annotation_type: type,
    original_text: text,
    normalized_label: 'figure:2',
    page_number: 5,
    geometry: null,
    confidence: 1,
    extraction_method: 'direct_text',
    created_at: '2026-01-01T00:00:00Z',
  }
}

function reference(
  resolution: DocumentReferenceResponse['resolution_status'],
  candidates: DocumentReferenceResponse['association_candidates'],
): DocumentReferenceResponse {
  return {
    id: 'reference-1',
    analysis_id: 'analysis-1',
    question_id: 'question-1',
    source_document: 'exam',
    target_type: 'figure',
    original_text: 'Figure 2',
    target_label: 'Figure 2',
    normalized_target_label: 'figure:2',
    page_number: 5,
    geometry: null,
    confidence: 1,
    extraction_method: 'direct_text',
    resolution_status: resolution,
    association_candidates: candidates,
    created_at: '2026-01-01T00:00:00Z',
  }
}

describe('material relationship presentation', () => {
  it('combines label and caption observations into one ordered physical record', () => {
    const materials = buildPhysicalMaterials(
      [material('second', 5, 20), material('first', 5, 10)],
      [
        annotation('label', 'first', 'label', 'الشكل 2: Network Structure'),
        annotation('caption', 'first', 'caption', 'الشكل 2: Network Structure'),
      ],
    )

    expect(materials.map((item) => item.material.id)).toEqual(['first', 'second'])
    expect(materials[0]).toMatchObject({
      label: 'الشكل 2',
      caption: 'Network Structure',
    })
  })

  it('never reports a duplicated exact target as resolved', () => {
    const materials = buildPhysicalMaterials(
      [material('one', 5, 10), material('two', 5, 20)],
      [],
    )
    const relationship = buildMaterialRelationship(
      reference('resolved', [
        {
          id: 'one',
          target_material_id: 'one',
          target_question_id: null,
          review_revision_id: null,
          basis: 'exact_label',
          confidence: 1,
          proximity_distance: null,
          exact_label_match: true,
          selected: true,
          ambiguity_reason: null,
        },
        {
          id: 'two',
          target_material_id: 'two',
          target_question_id: null,
          review_revision_id: null,
          basis: 'exact_label',
          confidence: 1,
          proximity_distance: null,
          exact_label_match: true,
          selected: false,
          ambiguity_reason: null,
        },
      ]),
      materials,
    )

    expect(relationship.result).toBe('ambiguous')
    expect(relationship.exactCandidates).toHaveLength(2)
    expect(relationship.matchedMaterial).toBeNull()
  })

  it('keeps proximity-only relationships advisory', () => {
    const materials = buildPhysicalMaterials([material('nearby', 6, 10)], [])
    const relationship = buildMaterialRelationship(
      reference('unresolved', [
        {
          id: 'nearby',
          target_material_id: 'nearby',
          target_question_id: null,
          review_revision_id: null,
          basis: 'proximity_support',
          confidence: 0.5,
          proximity_distance: 20,
          exact_label_match: false,
          selected: false,
          ambiguity_reason: 'Proximity is supporting evidence only.',
        },
      ]),
      materials,
    )

    expect(relationship.result).toBe('nearby')
    expect(relationship.matchedMaterial?.material.id).toBe('nearby')
  })
})

it('treats a selected deictic geometry candidate as a resolved link', () => {
  const materials = buildPhysicalMaterials([material('diagram', 6, 10)], [])
  const contextualReference: DocumentReferenceResponse = {
    ...reference('resolved', [
      {
        id: 'context',
        target_material_id: 'diagram',
        target_question_id: null,
        review_revision_id: null,
        basis: 'deictic_geometry',
        confidence: 0.85,
        proximity_distance: 10,
        exact_label_match: false,
        selected: true,
        ambiguity_reason: null,
      },
    ]),
    original_text: 'المخطط أدناه',
    target_label: 'المخطط أدناه',
    normalized_target_label: 'figure:unlabeled',
    page_number: 6,
  }

  const relationship = buildMaterialRelationship(contextualReference, materials)

  expect(relationship.result).toBe('linked')
  expect(relationship.matchedMaterial?.material.id).toBe('diagram')
  expect(relationship.contextCandidates).toHaveLength(1)
})
