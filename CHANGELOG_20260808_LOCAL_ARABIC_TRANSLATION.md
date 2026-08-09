# Local Arabic translation — 2026-08-08

- Reverted the previous behavior that asked Gemini to generate Arabic copies of semantic reasoning.
- Gemini now returns the academic judgment and reasoning in English only.
- Dynamic English explanations and question-to-CLO/topic reasons are translated after validation by the local `Helsinki-NLP/opus-mt-en-ar` model.
- Local translation is presentation-only: it cannot change statuses, evidence links, CLO/topic targets, recommendations, or scoring.
- Translation uses no Gemini/API tokens and does not make an external AI-provider request.
- `reasoning_ar` / `explanation_ar` remain in stored/API presentation details for backwards compatibility; they are populated by the local translator for new analyses.
- If the local translation model is unavailable, analysis still succeeds and the UI shows the exact English reason instead of replacing it with a generic Arabic sentence.
- The model is loaded lazily and its Hugging Face cache is persisted in local Docker development storage; production Compose also provides a dedicated model-cache volume.
- No database migration is required.
