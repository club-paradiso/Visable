# Waymaker Artemis — historical model migration

Recovery base: `d3e9490e22bdf455ca0bda958106811195a49d6d`, 2026-10-29.
The original architecture error was a Gemma 3 270M default in
`LocalModelAdapter` and the CLI, paired with an MLX-LM implementation and a
revision resolver that silently accepted another cached snapshot.

The old `real_local_mlx_dev20` result is **Gemma 3 270M**, revision
`ff1143e3a10547c9f2129e94ca37059b096b23f4`: 0/20 candidate passes. It is not an
E4B or E2B measurement. Its latency/rate claims do not measure the restored
runtime. The earlier pipeline check is likewise noncanonical. Files are moved
byte-for-byte under `history/noncanonical/`, preserving existing file digests.
The dependent old shadow report is archived there too. Nothing was relabeled
as a Gemma 4 generation.

`history/FIRST-INFERENCE-20261026.md` preserves the prior chronological research
README. Earlier genuine E4B run records remain in `runs/` with their original
model/revision/runtime and fictional-case limitations. They do not certify the
new runtime and do not establish Korean legal accuracy. Historical Mission 003
and 004 reports remain historical evidence.

The current Mission 005-A report supersedes the prior completion/performance
claims. Its original wording and the old next-step proposal remain recoverable
at the recovery-base commit. Current plans no longer recommend Gemma 2 or Qwen
as substitutes. External teacher-license catalogues and unrelated Visable model
routing are outside the Artemis foundation and remain intact.

No external weights were deleted. The cleanup manifest lists exact snapshot and
resolved blob paths and sizes, each changed path, classification, action and
recovery method. Old generated data can be restored with `git show
<recovery-base>:<original-path>` into an inspection directory; restoring it to
active inference discovery requires review, not an automated fallback.

Do not pool: E4B real runs, explicitly selected E2B runs, these historical
noncanonical experiments, mock adapters, recorded fixtures, synthetic security
regressions or independently authenticated human gold. Official Gold Accuracy
is N/A in this recovery.
