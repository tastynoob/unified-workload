# AGENTS.md

This file contains repository-local instructions for Codex and other coding
agents working in unified-workload.

## Scope

- This file applies to the repository rooted at the directory containing it.
- Read this file before changing code or launching a workload.
- Preserve user changes in the working tree. Do not reset, checkout, or revert
  changes that were not made by the current task.

## Long-Running Workloads

- Estimate runtime, memory use, disk use, and expected output size before
  starting a long build, QEMU run, profiling run, benchmark, or checkpoint
  generation job.
- Report that estimate before launching the job.
- Do not use timeout, watchdog, automatic deadline termination, or an
  equivalent shell wrapper for long-running jobs.
- Run long jobs in a persistent session and poll them for progress.
- Let QEMU or the workload terminate through its normal completion signal.
- Only send an interrupt or termination signal after the user explicitly asks
  to stop the running job. A question about runtime, a status request, or a
  concern about duration is not permission to interrupt.
- If the user asks to change the runtime policy, confirm the new policy before
  applying it to an already-running job.
- Before any requested interruption, report elapsed time, current progress,
  output paths, and whether the output is complete or partial.
- Preserve partial BBV, checkpoint, log, and build artifacts. Never delete or
  overwrite partial results unless the user explicitly authorizes it.
- After an unexpected interruption, first check for a surviving process and
  inspect whether the output stream can be recovered before starting a
  replacement run.

## Experiment Paths

- Put generated artifacts on the requested storage device.
- Include compiler versions, compiler prefixes, and compile flags in the
  artifact root path.
- Include workload name, input size, copy/rate mode, interval, warmup, and
  total slice length in the experiment path when applicable.
- Use the cutpoint instruction count divided by the measurement interval as
  the slice name.
- Keep invalid or partial experiments clearly separated from final results.

## QEMU

- Do not modify an external QEMU tree, plugin, binary, or build artifact unless
  the user explicitly requests a QEMU change.
- Do not infer permission to modify QEMU from a request to run a workload.
- If QEMU behavior appears wrong, inspect and report the cause first.
- Keep unified-workload changes, QEMU changes, and generated experiment
  artifacts in separate paths.

## Editing

- Use the repository's existing build and test conventions.
- Use apply_patch for manual source edits.
- Keep changes narrowly scoped to the requested behavior.
- Do not modify vendored or externally cloned benchmark source unless the user
  explicitly authorizes it.
