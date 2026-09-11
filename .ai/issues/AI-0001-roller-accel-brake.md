# AI-0001: Roller accelerate, coast, brake, and stop skill

- Type: phased
- Status: ready
- Priority: P1
- Created: 2026-09-09
- Current phase: P3
- Spec: [../specs/AI-0001-roller-accel-brake.md](../specs/AI-0001-roller-accel-brake.md)

## Problem

The trained `Mjlab-Velocity-Flat-MicroDuck-Rollers` policy does not provide a
reliable low-level roller motion cycle. Evaluation of the 20,000-iteration run
shows a command dead zone at low positive commands, little useful coasting, and
no demonstrated transition from motion through braking to a stable stop.

The current task makes passive-wheel speed the main positive objective and its
braking reward pays the already-stationary state on every braking step. Strong
early smoothness pressure also makes doing nothing a competitive local optimum.
More iterations alone do not correct these objective and sampling problems.

## Desired behavior

Add one hot-swappable low-level policy task:

```text
Mjlab-RollerAccelBrake-Flat-MicroDuck
```

The same policy and checkpoint chain must learn:

```text
idle -> accelerate -> coast -> brake command -> decelerate -> stable stop
```

The twist command contract remains 3D and uses `cmd_x > 0` for acceleration
effort, `cmd_x == 0` for coast/idle, and `cmd_x < 0` for braking effort. A
higher-level controller remains responsible for target selection, obstacle or
range detection, speed estimation, and deciding when to issue the brake command.

## Non-goals

- Do not change the historical `Mjlab-Velocity-Flat-MicroDuck-Rollers` task.
- Do not add ToF, obstacle, position, or base-speed observations to the actor.
- Do not change the shared 61D actor observation contract.
- Do not train turning, lateral travel, or reverse travel; negative `cmd_x`
  remains braking and cannot also mean reverse.
- Do not add action filtering or a new dependency.
- Do not build automatic reward-weight search or self-modifying training logic.
- Do not modify the external `pollen-robotics/microduck` runtime in this issue.
- Do not perform real-robot testing without a later explicit authorization and
  user-supervised hardware safety plan.

## Acceptance criteria

- A separately registered roller task inherits the existing roller velocity
  environment's BAM, delay, noise, NaN guard, and sim2real machinery.
- Actor observations remain 61D with the existing command block ordering, and
  all actuator/reward selectors remain safe for interleaved passive wheels and
  backlash joints.
- Exact-zero, positive, and negative command buckets are all trained from the
  beginning; the policy is one network across all skill stages.
- Main task reward measures real body motion, coast retention, and actual
  deceleration. Passive wheel speed cannot independently satisfy the task.
- A rolling-entry brake curriculum initializes body and wheel velocities with
  `omega * wheel_radius ~= body_speed`.
- A stationary robot cannot repeatedly farm braking or stop rewards. Stop
  success requires prior motion, bounded residual speed and reverse overshoot,
  an upright state, and a stable dwell; any success bonus is one-shot.
- Penalty sign tests and run logs establish that every weighted penalty is
  non-positive.
- Stage progression is checkpoint- and metric-gated during initial development;
  reaching a nominal iteration count alone does not authorize the next stage.
- The completed nominal policy passes the acceleration, coast, braking, stop,
  fall-rate, and slip criteria frozen from the P1 physics baseline.
- The robust policy passes the final randomized evaluation, is exported through
  the official normalizer-baking path, and passes CPU MuJoCo inference rehearsal.
- Every phase records checks actually run and does not mark unrun checks as
  passing.

## Constraints

- Follow all repository invariants in `AGENTS.md`, especially the 61D observation
  layout, servo-only selectors, passive-wheel regex, BAM friction behavior,
  non-accumulating DR, unfiltered actions, and official ONNX export.
- Put custom commands, rewards, events, metrics, curricula, and terminations in
  `src/mjlab_microduck/tasks/mdp.py`.
- Build on `make_microduck_velocity_rollers_env_cfg`; do not duplicate the base
  environment or sim2real stack.
- Use a distinct runner experiment name and keep symmetry disabled unless a
  later measured result justifies a separately authorized change.
- Introduce action-rate and style regularizers only after the corresponding
  physical skill exists.
- Change live term configurations through managers, not `env.cfg` copies.
- Always run the 64-environment, five-iteration smoke test before long training.
- Preserve unrelated worktree changes.

## Required resources

- Existing local roller run, checkpoint/ONNX, logs, and roller model for P1.
- CUDA GPU for smoke and later PPO training phases.
- W&B or equivalent local event logs for training review.
- User-supervised robot and safety area only for a future, separately authorized
  real-hardware issue; not required for this issue's software acceptance.

## Open questions

- Final acceleration time, coast-retention, stop-time, stop-distance, residual
  speed, reverse-overshoot, and slip thresholds are provisional until P1 measures
  achievable physics on the actual roller model.
- The conservative braking deceleration used by the higher-level stopping-
  distance controller must be derived from the final randomized rollout
  distribution, not assumed in advance.

Neither question blocks P1. Both are measured decisions recorded in the linked
spec before dependent phases begin.

## References and evidence

- [Phased development spec](../specs/AI-0001-roller-accel-brake.md)
- `src/mjlab_microduck/tasks/microduck_velocity_rollers_env_cfg.py`
- `src/mjlab_microduck/tasks/mdp.py`
- `scripts/infer_policy.py`
- Existing run:
  `logs/rsl_rl/velocity_rollers/2026-09-07_17-48-02_Mjlab-Velocity-Flat-MicroDuck-Rollers_01`
- Measured existing-policy behavior: approximately no body motion for positive
  commands through `0.25`, about `0.18-0.22 m/s` near commands `0.3-0.6`, and
  negligible logged glide reward near the end of training.

## Dependencies

- Each phase depends on the acceptance and recorded results of the previous
  phase; see the linked spec.
- Long PPO training depends on explicit authorization of the exact phase and GPU
  use during its preflight.

## Development record

- 2026-09-09: Issue and phased spec recorded from the approved development
  proposal. No product code changed, no preflight performed, and no development
  or verification started.
- 2026-09-09: P1 preflight completed. User authorized P1 development; P1 marked
  in progress. Scope is limited to deterministic baseline/physics evaluation.
- 2026-09-09: P1 completed. Added a deterministic CPU MuJoCo/BAM evaluator,
  ran the complete 16-case battery twice with identical results, recorded the
  measured baseline and froze nominal P2-P5 gates in the spec. No task config,
  reward, training, export, external service, or hardware operation was changed
  or run. P2 remains unpreflighted and unauthorized.
- 2026-09-12: Recorded the user-approved complete P2 implementation plan in the
  linked spec, including the `conda run -n microduck uv run ...` execution
  convention and the 78% acceleration / 20% exact-zero idle / 2% rolling-entry
  brake-seed Stage A mix. This is a planning-only update: P2 remains `ready`,
  Active Development remains `None`, and no product code, training, or commit
  was authorized.
- 2026-09-12: User authorized P2 development. P2 is in progress; scope is
  limited to the registered task, focused tests, and required smoke test.
- 2026-09-12: P2 completed. Added the derived base/backlash roller task,
  hidden command/scenario state, rolling reset, body-motion rewards, stop
  latch, CPU regression tests, and the required GPU smoke run. P3 remains
  unpreflighted and unauthorized; no long training or commit was performed.
