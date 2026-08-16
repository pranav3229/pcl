# Intent

An **Intent** expresses consumer demand for a physical outcome.

Capability: "I can transport packages up to 25 kg."
Intent: "Transport this 10 kg package from A to B within 10 minutes."

## Inputs

Intent uses a map keyed by IOContract `name`:

```json
"inputs": {
  "object": { "ref": "package-123" },
  "origin": { "ref": "zone-A" }
}
```

## Constraints

Intent constraints use the same `name` keys as capability constraints for matching.
