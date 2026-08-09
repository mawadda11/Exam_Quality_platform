from __future__ import annotations
import json
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.core.domain import AssociationBasis, ReferenceResolutionStatus
from app.models.document_reference import DocumentReference
from app.models.question import Question
from app.models.reference_association import ReferenceAssociation
from app.models.supporting_material import SupportingMaterial
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.provider import AiProviderError

_SCHEMA={"type":"object","properties":{"decisions":{"type":"array","items":{"type":"object","properties":{"reference_id":{"type":"string"},"decision":{"type":"string","enum":["link","ambiguous","no_reference"]},"material_id":{"type":"string"},"confidence":{"type":"string","enum":["high","medium","low"]}},"required":["reference_id","decision","material_id","confidence"],"additionalProperties":False}}},"required":["decisions"],"additionalProperties":False}

def adjudicate_nonexplicit_references(session: Session, analysis_id: UUID, settings: Settings) -> None:
    if not settings.extraction_ai_enabled:
        return
    api_key=settings.gemini_api_key.get_secret_value().strip()
    if not api_key:
        return
    refs=list(session.execute(select(DocumentReference).where(DocumentReference.analysis_id==analysis_id)).scalars())
    questions={q.id:q for q in session.execute(select(Question).where(Question.analysis_id==analysis_id)).scalars()}
    materials={m.id:m for m in session.execute(select(SupportingMaterial).where(SupportingMaterial.analysis_id==analysis_id)).scalars()}
    payload=[]; candidate_map={}
    for ref in refs:
        if not ref.normalized_target_label.endswith(":unlabeled") or ref.machine_resolution_status is not ReferenceResolutionStatus.AMBIGUOUS:
            continue
        candidates=list(session.execute(select(ReferenceAssociation).where(ReferenceAssociation.reference_id==ref.id,ReferenceAssociation.review_revision_id.is_(None),ReferenceAssociation.target_material_id.is_not(None))).scalars())
        candidate_ids=[c.target_material_id for c in candidates if c.target_material_id in materials]
        if len(candidate_ids)<2:
            continue
        candidate_map[str(ref.id)]={str(mid):mid for mid in candidate_ids}
        q=questions.get(ref.question_id)
        payload.append({"reference_id":str(ref.id),"reference_phrase":ref.original_text,"question_text":q.question_text if q else "","question_page":q.page_number if q else ref.page_number,"candidates":[{"material_id":str(mid),"type":materials[mid].material_type.value,"page":materials[mid].page_number,"source_text":(materials[mid].source_text or "")[:1200],"geometry":materials[mid].geometry} for mid in candidate_ids]})
    if not payload:
        return
    provider=GeminiProvider(api_key=api_key,model=settings.extraction_ai_model)
    system=("Resolve only ambiguous non-explicit exam references to supplied candidates. Use wording, type, page and geometry; a target may be above, below or adjacent. Choose link only with high confidence; otherwise ambiguous/no_reference. Never invent a target.")
    try:
        parsed=json.loads(provider.generate_structured(system=system,prompt=json.dumps({"references":payload},ensure_ascii=False),schema=_SCHEMA))
    except (AiProviderError,ValueError,TypeError,json.JSONDecodeError):
        return
    refs_by_id={str(r.id):r for r in refs}
    for decision in parsed.get("decisions",[]):
        if decision.get("decision")!="link" or decision.get("confidence")!="high":
            continue
        rid=str(decision.get("reference_id","")); mid=str(decision.get("material_id",""))
        if rid not in candidate_map or mid not in candidate_map[rid] or rid not in refs_by_id:
            continue
        target_id=candidate_map[rid][mid]; ref=refs_by_id[rid]
        rows=list(session.execute(select(ReferenceAssociation).where(ReferenceAssociation.reference_id==ref.id,ReferenceAssociation.review_revision_id.is_(None))).scalars())
        for row in rows:
            row.selected=(row.target_material_id==target_id)
            if row.selected:
                row.basis=AssociationBasis.AI_ADJUDICATION; row.confidence=min(row.confidence,0.85); row.ambiguity_reason=None
        ref.machine_resolution_status=ReferenceResolutionStatus.RESOLVED
    session.flush()
