# Gemini RemoteProtocolError failover fix

- Classifies `httpx.RemoteProtocolError` and other HTTP transport failures as AI availability failures.
- This allows the existing sticky route to retry the same semantic step on the configured fallback Gemini model instead of surfacing `RULE_EVALUATION_FAILED`.
- Applies the same transport classification to Gemini structure extraction so extraction follows the same availability-failover policy.
- Authentication, schema/validation, configuration, and programming failures remain non-failover errors.
