# Waymaker Artemis — next execution gates

Observed outcome: dedicated runtime/imports, full checkpoint integrity and real
processor/tokenizer/template initialization passed. The 32-token probe was
not_executed because used swap was 2.73GB, above the unchanged 2GB limit.
No model weights were loaded into MLX and no response tokens were generated.

1. Obtain a host state satisfying the existing policy: at least 6GB free disk,
   at most 2GB used swap, Apple Silicon/macOS compatible with mlx-metal 0.32.4.
   Keep the 6GB MLX allocation limit, 256MiB cache limit and 120-second timeout.
   Do not terminate unrelated applications, reset swap or relax these limits.
2. Reuse the isolated `.venv` and hash-locked packages. Run `pip check`, the
   import/processor inspection and pinned streaming integrity validation. Use
   an unused evidence directory; do not overwrite this attempt.
3. Run the existing probe at 32 tokens. A valid positive-token result may be
   marked completed. Invalid JSON after real tokens is generated_but_invalid;
   retain unmodified output. A single 64/128-token retry is allowed only for a
   genuinely truncated generation while resources remain safe.
4. Only after that succeeds, run the small synthetic A/B/C checks: no evidence,
   one explicitly fictional rule with one citation ID, and two conflicting
   fictional rules. Separate raw generation, parser/citation results and
   behavior inspection. These are engineering probes, not legal accuracy.
5. Before the 20-item dev evaluation, freeze the runtime/code/config hashes,
   validate source allowlisting at the worker boundary, verify decoding and
   preserve model-specific records. Do not run the existing 40-item held-out
   set as an independent unseen benchmark.
6. Independent legal assessment requires external enforcement/key custody,
   authenticated review, independent authorship and contamination reports with
   named, hashed corpora and explicit coverage limits. Keep official gold N/A
   and isolation_not_verified until a trusted external verifier exists.

Alternative host estimate: start with at least 16GB unified memory and 10GB
free disk on Apple Silicon/macOS 15+. This is not a measured minimum or a
promise that this checkpoint fits the existing 6GB MLX cap. Measure actual
load/prefill/decode peaks under the same safety policy before choosing serving
hardware. No paid provisioning, replacement weights, training or deployment is
authorized by this plan.
