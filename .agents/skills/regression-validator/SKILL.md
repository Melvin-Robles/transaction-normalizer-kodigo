---
name: regression-validator
description: Run the transaction-normalizer regression checks after code, adapter or validation changes, including unittest, compilation and the integrated example, with safe bounded subprocesses and explicit results.
---

# Regression validator

## Purpose

Use this skill after refactoring or modifying adapters, validation, services,
exports or configuration-related code. It verifies the existing behavior; it
does not repair failing code or weaken tests.

## Activation

Activate for requests such as:

- run regression checks before delivery;
- verify a refactor preserved the example output;
- check compilation and unittest results;
- investigate whether a code change introduced a regression.

Do not use it as a batch-quality auditor or as a rules editor.

## Checks performed

The script executes, with `shell=False` and a timeout:

1. `unittest discover` over the repository tests;
2. `compileall` for `app.py`, `src` and `tests`;
3. the integrated example through `TransactionProcessingService`.

It compares the example against the contractual result: 3 processed, 3 valid,
0 invalid, USD 201.00 and EUR 99.99.

## Command

```powershell
python .agents/skills/regression-validator/scripts/run_regression.py
python .agents/skills/regression-validator/scripts/run_regression.py --timeout 60
```

For an isolated test of the runner itself, a narrower unittest pattern may be
provided:

```powershell
python .agents/skills/regression-validator/scripts/run_regression.py --test-pattern test_characterization.py
```

Exit codes:

- `0`: every check passed.
- `1`: one or more checks failed or timed out.
- `2`: invalid invocation or controlled setup error.

## Interpretation

Read each check independently. A passing compile does not prove behavior; a
passing example does not replace the full test suite. Preserve failure output
for diagnosis and never edit tests to hide a regression.

## Resources

- [Functional contracts](references/functional-contracts.md)
- [Edge cases](references/edge-cases.md)
- [Regression guide](references/regression-guide.md)
- [Expected example](references/expected-example.md)

## Restrictions

- Do not use `shell=True`.
- Do not accept arbitrary shell commands from user input.
- Do not modify source, tests, rules or the input fixture.
- Keep subprocesses bounded by the configured timeout.
- Do not claim that Codex activated a skill merely because this script was run
  manually.

## Completion criteria

The validation is complete when the JSON report identifies all checks, includes
return codes and failure output where relevant, and `overall_passed` accurately
matches the check results.
