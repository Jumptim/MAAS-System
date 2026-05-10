# Output Repair Prompt

Your previous output did not satisfy the agent's JSON output contract.

Repair only the JSON structure and schema violations. Do not add explanations,
markdown fences, commentary, or new task content that was not present in the
previous answer.

## Validation Errors

{validation_errors}

## Previous Output

{previous_output}

## Required Response

Return only one valid JSON object that conforms to the agent's
`schemas/result.schema.json`.
