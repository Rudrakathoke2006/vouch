# Evaluation Harness Workflow

Executes the 30-case evaluation manifest across three passes:
1. Loads 12 legitimate and 18 fraudulent synthetic invoice scenarios.
2. Invokes the Evidence Auditor and Decision Engine.
3. Compares verdicts against blinded truth labels.
4. Calculates False-Release Rate, False-Hold Rate, Human-Review Rate, and Run-to-Run variance.
5. Emits the summary report to `docs/EVAL.md`.
