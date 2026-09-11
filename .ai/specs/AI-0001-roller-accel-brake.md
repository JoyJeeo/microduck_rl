# AI-0001 Spec: Roller accelerate, coast, brake, and stop skill

- Issue: [../issues/AI-0001-roller-accel-brake.md](../issues/AI-0001-roller-accel-brake.md)
- Status: active
- Current phase: P3

## Goal

Deliver one deployable roller policy that responds to the existing twist command
contract with a complete low-level sequence:

```text
stable idle -> accelerate -> stable coast -> brake -> stable stop
```

Training is deliberately phased because later reward thresholds, curricula, and
randomization depend on measured physics and preceding checkpoint behavior. All
training phases continue the same policy unless a phase discovers that the core
command or objective semantics are invalid, in which case development stops for
re-preflight rather than silently restarting.

## Non-goals

- Obstacle/ToF perception, range planning, brake-trigger decisions, and changes
  to the external runtime.
- Reverse, lateral, or turning behavior.
- Actor observation changes, recurrent-policy work, action filters, automatic
  hyperparameter search, or unrelated cleanup.
- Real-hardware execution under this issue.

## Constraints and invariants

- Preserve the 61D actor layout: 48D proprioception followed by
  `[twist(3), head_pose(4), body_pose(6)]`.
- Preserve 14 unfiltered servo actions and resolve joints by name through the
  established servo helpers; wheel selectors must use `^passive_.*wheel`.
- Inherit the existing roller environment's BAM and sim2real stack.
- Keep the historical roller task unchanged for A/B comparison.
- Bake observation normalization through the official export path.
- Reward reaching/motion progress without a per-step goal jackpot. A stop bonus,
  if needed, is latched and emitted once.
- Cost functions return non-negative values with negative weights unless an
  existing explicitly self-negating repository convention is reused and tested.
- Initial development uses automatic physical metric logging plus checkpoint
  review. It does not advance merely because an iteration number was reached and
  does not automatically invent new reward weights.
- A phase that fails its maximum initial budget remains in that phase. Make one
  measured, minimal change at a checkpoint, smoke-test it, and resume only when
  the authorized phase still covers the change.

## Overall approach

1. Measure the current policy and roller physics with a deterministic evaluation
   battery before fixing thresholds.
2. Add a derived roller task with a per-environment training state machine:
   `IDLE`, `ACCEL`, `COAST`, `BRAKE`, and `STOP`. The actor observes only the
   actual twist command, not hidden phase state.
3. Replace raw wheel-speed and already-stopped rewards with body-motion,
   coast-retention, potential-based deceleration, stop-distance, overshoot, and
   wheel/body consistency signals.
4. Use explicit idle, acceleration, rolling-coast, rolling-brake, and full-cycle
   scenario buckets. Reuse the existing rolling-entry physics and coordinate it
   only with relevant scenario IDs.
5. Train and accept acceleration, braking, combined behavior, and randomized
   robustness in separate authorized phases on one checkpoint chain.
6. Export through the official path and rehearse the final ONNX in CPU MuJoCo.

The higher-level runtime contract is:

```text
cmd_x > 0  acceleration effort
cmd_x = 0  idle/coast
cmd_x < 0  braking effort
```

A higher layer may close the speed loop with a bounded proportional command and
trigger braking when remaining distance is below a conservative stopping-distance
estimate derived from P6 measurements.

## Phases

### P1: Baseline and physics evaluation

- Status: done
- Scope:
  - Build the smallest deterministic headless evaluation needed to measure the
    existing roller checkpoint/ONNX under idle, acceleration, coast, and braking
    command sequences.
  - Measure body speed/displacement, passive-wheel speed, wheel/body slip,
    acceleration time, coast retention, stop time/distance, reverse overshoot,
    upright/fall outcome, and representative friction/initial-speed slices.
  - Record the baseline and freeze provisional nominal acceptance thresholds for
    P2-P5. Do not redesign rewards in this phase.
- Non-scope:
  - New task registration, reward changes, PPO training, DR training, export, or
    real-hardware work.
- Deliverables:
  - A focused reusable evaluation command/script or a documented reuse of an
    existing evaluator if it already covers every required metric.
  - Baseline results and frozen nominal gates recorded under
    `Decisions and measured results`.
- Required inputs:
  - The existing local final roller checkpoint or ONNX and roller model. Confirm
    exact usable paths during preflight; no user upload is expected if local
    artifacts are intact.
- Acceptance criteria:
  - The same deterministic battery is repeatable and distinguishes body travel
    from passive-wheel spin.
  - Nominal speed and braking thresholds are based on measured model behavior,
    not the provisional values in the issue.
  - No training/task behavior is changed.
- Verification:
  - Focused evaluator tests where practical, then at least two repeated headless
    runs with identical seed/config and a result comparison.
- Dependencies:
  - None.

### P2: Core environment and tests

- Status: done
- Scope:
  - Add `Mjlab-RollerAccelBrake-Flat-MicroDuck` as a derived roller task with its
    own runner experiment name.
  - Add the command/scenario state, coordinated rolling resets, rewards,
    one-shot stop success, metrics, termination, curriculum parameters, and
    registration needed for nominal skill training.
  - Register a backlash twin that mirrors the roller robot model if the existing
    task registration mechanism supports it without a separate design change.
  - Add focused CPU cfg/MDP tests and run the mandatory 64-env, five-iteration
    smoke test. No long learning run belongs to P2.
- Non-scope:
  - Long PPO training, reward tuning based on learned rollouts, DR hardening,
    ONNX release, external runtime, or hardware.
- Deliverables:
  - `src/mjlab_microduck/tasks/microduck_roller_accel_brake_env_cfg.py`
  - Minimal additions to `src/mjlab_microduck/tasks/mdp.py` and task registration.
  - Focused cfg and MDP regression tests.
- Required inputs:
  - P1 results and thresholds.
- Acceptance criteria:
  - Task builds in train/play configs; actor remains 61D and action size remains
    14 on the actual roller model.
  - Exact zero, acceleration, coast, brake, and full-cycle scenarios can be
    selected and reset consistently.
  - Reward gates, signs, potential state, one-shot stop latch, and rolling-entry
    kinematics pass CPU tests.
  - Historical roller task config is unchanged.
  - Five training iterations at 64 environments complete without NaN, dimension,
    indexing, reward, or termination failures.
- Verification:
  - Focused pytest files, relevant existing roller cfg tests, task registry
    check, and the mandatory smoke test. Record actual commands and results.
- Dependencies:
  - P1 done.

#### Approved P2 implementation plan

- Authorization boundary:
  - Recording this plan does not authorize implementation. P2 remains `ready`
    until the user explicitly authorizes `AI-0001 P2` after its read-only
    preflight.
  - P2 ends after the task, tests, registry checks, and five-iteration smoke test
    pass. It does not include long training, rollout-driven tuning, P3-P6 work,
    export, runtime changes, hardware, or a Git commit.
- Execution environment:
  - Run every development command from the `microduck` conda context.
  - Use `conda run -n microduck uv run ...` for project Python, tests, registry,
    and training commands. Conda supplies the outer execution context and the
    project `.venv` supplies torch, MuJoCo, mjlab, and ONNX Runtime.
  - Use `conda run -n microduck bash -lc '...'` for shell-only inspection or for
    commands that need environment variables. Installing a second dependency
    stack into conda Python is outside P2.
- Task and files:
  - Add `Mjlab-RollerAccelBrake-Flat-MicroDuck` and
    `Mjlab-RollerAccelBrake-Flat-Backlash-MicroDuck`.
  - Add
    `src/mjlab_microduck/tasks/microduck_roller_accel_brake_env_cfg.py`, make the
    smallest necessary additions to `src/mjlab_microduck/tasks/mdp.py` and
    `src/mjlab_microduck/tasks/__init__.py`, and add
    `tests/test_roller_accel_brake.py`.
  - Build the config by calling `make_microduck_velocity_rollers_env_cfg(play)`
    and override only the command, reset/scenario event, rewards, metrics,
    terminations, scenario parameters, and runner settings required by this
    task. Do not duplicate the inherited BAM, delay/noise, NaN guard, observation,
    or domain-randomization stack.
  - Preserve the historical `Mjlab-Velocity-Flat-MicroDuck-Rollers` task without
    behavior or config changes. Register the backlash twin through the existing
    `_BACKLASH_TASKS` mechanism using the rollers model.
- Policy contract and initial config:
  - Preserve the shared 61D actor observation and 14D unfiltered action contract.
    The actor observes the existing 3D twist command; unused head/body command
    slots remain zero-padded. Do not add body- or wheel-speed observations.
  - Keep command semantics fixed: `cmd_x > 0` means acceleration effort,
    `cmd_x == 0` means idle/coast, and `cmd_x < 0` means braking effort. Negative
    command never means reverse travel.
  - Use a distinct runner experiment/run name `roller_accel_brake`, keep actor
    and critic normalization enabled, inherit the roller PPO architecture and
    defaults, keep symmetry off, and use a checkpoint interval in the existing
    100-250 range without speculative PPO changes.
  - Keep pushes, wheel-drag hardening, strong DR, and meaningful action-rate,
    torque-rate, pose/style taxes disabled during initial skill discovery. Keep
    the inherited BAM startup event `expand_bam_friction_fields` present.
- Scenario and phase state machine:
  - Implement explicit scenario IDs `IDLE`, `ACCEL`, `COAST`, `BRAKE`, and
    `FULL_CYCLE`, plus internal phase IDs `IDLE`, `ACCEL`, `COAST`, `BRAKE`,
    `STOP`, and `DONE`. Hidden IDs and timers are training state only and are not
    appended to actor observations.
  - Implement and test every scenario in P2, but freeze the Stage A sampling mix
    at `78% ACCEL + 20% exact-zero IDLE + 2% rolling-entry BRAKE seed`, with
    `COAST` and `FULL_CYCLE` at zero weight. The 2% seed gives the negative-command
    input path live rolling-state exposure without teaching the contradictory
    stationary-negative behavior.
  - Sample positive commands from explicit buckets
    `0.10/0.20/0.25/0.30/0.40/0.60`; use `-0.50` for the initial braking command.
  - Use the nominal schedule: IDLE is 6 s of exact zero; ACCEL is 1 s of exact
    zero followed by 5 s positive command; rolling BRAKE applies negative command
    for at most 4 s then exact zero during the stop dwell; COAST is a rolling
    reset followed by exact zero; FULL_CYCLE is 1 s idle, 5 s acceleration,
    0.5 s coast, at most 4 s braking, and 0.5 s stop dwell within a 12 s episode.
  - P2 must not add automatic iteration-based promotion into P4 or P5 sampling.
    Later stage weights remain checkpoint- and metric-gated under separate phase
    authorizations. The 2% brake seed is safety/coverage exposure and is not the
    P4 braking acceptance gate.
- Reset coordination and rolling-entry physics:
  - Account for mjlab reset order: reset events run before
    `command_manager.reset`. The reset event calls the command term's
    `prepare_reset(env_ids)` to select scenario, command, and rolling-entry speed,
    then writes root and passive-wheel state; the later command reset initializes
    timers and latches without resampling the prepared scenario.
  - Use rolling-entry body speeds `0.10/0.20/0.30 m/s` and initialize each wheel
    with `wheel_omega * 0.0175 = body_speed`.
  - Resolve wheels with `^passive_.*wheel` and existing joint helpers; never
    hardcode joint indices, so plain and backlash roller models follow the same
    path.
  - Keep nominal spawn yaw fixed at zero in P2 so world-X rolling velocity can be
    written deterministically without relying on stale derived quaternion state
    during reset. Any yaw-randomized extension belongs to P6 preflight.
- Command-term state and update ordering:
  - Keep per-environment scenario/phase state in the command term rather than
    scattering attributes on the environment. Minimal state is scenario ID,
    phase ID/time, sampled positive command, rolling-entry speed, previous
    forward speed, prior-motion latch, stop-dwell timer, stop-success latch,
    one-shot bonus latch, brake-start position, and maximum reverse speed.
  - Add one idempotent state-refresh helper keyed by
    `env.common_step_counter`. Terminations and rewards may both call it in the
    same step, but phase timers, previous-speed state, and latches advance only
    once. This matches the effective order physics -> termination -> rewards ->
    reset -> command update -> observations.
- Rewards, gates, and signs:
  - Measure the main acceleration objective with actual trunk forward speed and
    displacement. Passive-wheel speed alone cannot earn positive task reward.
  - Use signed acceleration progress based on
    `current_forward_speed - previous_forward_speed` and signed braking progress
    based on `previous_abs_speed - current_abs_speed`. Speed increases while
    braking therefore reduce return, and alternating acceleration/deceleration
    cannot farm an always-positive magnitude reward.
  - Implement coast retention gated by prior motion or rolling-entry state, but
    leave its Stage A weight at zero.
  - Define wheel/body slip cost as
    `abs(mean_wheel_omega * 0.0175 - body_forward_speed)` and add a non-negative
    reverse-overshoot cost. New cost functions return non-negative values and use
    negative weights; signed progress functions are explicitly positive task
    rewards.
  - Reuse the inherited upright, heading, lateral-motion, body-angular safety,
    and joint-limit terms where their existing semantics fit. Do not introduce a
    positive reward gated on a fallen, low, or stationary bad state.
  - Stop success requires prior motion, absolute forward speed at most
    `0.05 m/s`, reverse overshoot at most `0.03 m/s`, tilt at most 30 degrees,
    trunk z at least `0.09 m`, and 0.5 s continuous dwell. Emit any success bonus
    once per episode. Interrupting any gate resets the dwell; a stationary reset
    can never earn stop success.
- Terminations and metrics:
  - Add a stop-success termination backed by the stable latch and a normal
    scenario-complete/time-out path for fixed scenarios; retain inherited NaN,
    fall, and episode timeout safety.
  - Because terminations are evaluated before rewards, the shared refresh helper
    must make the success latch visible to both while still allowing the one-shot
    reward on the success step.
  - Log scenario fractions and per-scenario masked metrics for acceleration peak,
    final speed, acceleration time/displacement, body/wheel speed, mean and p95
    slip, 0.5 s coast retention, brake-entry speed, stop time/distance, residual
    speed, reverse overshoot, maximum tilt, success, and fall. Do not dilute a
    scenario metric by averaging zero placeholders from unrelated scenarios.
  - P1's deterministic evaluator remains the external checkpoint gate; P2 does
    not replace it with training reward totals.
- Focused regression coverage:
  - Command/scenario tests cover explicit selection, Stage A probabilities,
    command buckets, phase transitions, and reset/latch clearing.
  - Rolling-reset tests use both actual base and backlash roller models and cover
    the wheel selector plus `omega * radius = speed` relation.
  - Reward tests prove that wheel spin without body travel cannot earn the main
    reward, body progress can, braking/acceleration potentials have the intended
    signs, a stationary robot and oscillating speed cannot farm reward, the stop
    bonus is one-shot, dwell interruption clears progress, reverse overshoot
    blocks success, and every new raw cost/weight sign is correct.
  - Config tests lock the 61D/14D contract, command padding, joint selectors, BAM
    startup, no action filtering, symmetry off, zero initial style-tax weights,
    backlash model parity, and unchanged historical roller config.
  - Registry tests require both new task IDs to resolve.
- Verification commands, in order:

  ```bash
  conda run -n microduck uv run list-envs
  conda run -n microduck uv run --with pytest pytest -q tests/test_roller_accel_brake.py tests/test_infer_policy_bam.py tests/test_wheel_glide.py
  conda run -n microduck uv run --with pytest pytest tests/
  conda run -n microduck bash -lc 'WANDB_MODE=disabled uv run train Mjlab-RollerAccelBrake-Flat-MicroDuck --env.scene.num-envs 64 --agent.max_iterations 5'
  ```

  Record actual outputs in this spec. The smoke test is a construction and
  numerical-stability gate only; it does not authorize a long run or reward
  tuning from five iterations.

### P3: Stage A idle and acceleration training

- Status: pending
- Scope:
  - Train from the P2-frozen Stage A mix: 78% acceleration from rest, 20%
    exact-zero idle, and 2% rolling-entry brake seed. The rare brake seed keeps
    negative-command inputs live but is not evaluated as learned P4 braking.
  - Keep pushes, wheel drag, strong DR, style rewards, and meaningful
    action-rate tax out of skill discovery.
  - Evaluate every 100-250 iterations/checkpoints and make only measured,
    stage-local reward or scenario changes when the gate is missed.
- Non-scope:
  - Braking curriculum, full cycles, DR, export, or hardware.
- Deliverables:
  - One accepted acceleration checkpoint and recorded rollout metrics/video
    observations.
- Required inputs:
  - P2 smoke-tested task and authorized CUDA GPU use.
- Acceptance criteria:
  - Meet the P1-frozen idle stability, real body displacement, target-speed,
    acceleration-time, fall-rate, and wheel/body consistency gates for multiple
    consecutive evaluations.
  - No in-place wheel-spin, stationary, fall-forward, or violent-limit behavior
    is accepted as acceleration success.
- Verification:
  - Fixed deterministic battery plus visual rollout review; W&B penalties are
    all non-positive. Initial budget 600-1000 iterations, maximum initial budget
    1500 before stopping for diagnosis.
- Dependencies:
  - P2 done.

### P4: Stage B rolling-entry braking training

- Status: pending
- Scope:
  - Resume the accepted P3 checkpoint and add rolling-entry braking at measured
    initial speeds, retaining acceleration and exact-zero samples to prevent
    forgetting.
  - Train potential-based deceleration, speed/distance cost, stable-stop latch,
    and reverse-overshoot control in nominal physics.
- Non-scope:
  - Full-cycle dominance, strong DR, automatic brake-trigger planning, export,
    or hardware.
- Deliverables:
  - One accepted nominal braking checkpoint with per-initial-speed metrics.
- Required inputs:
  - Accepted P3 checkpoint and authorized CUDA GPU use.
- Acceptance criteria:
  - Meet P1-frozen stop success, time, distance, residual-speed, reverse-
    overshoot, upright, and fall-rate gates across the nominal initial-speed
    battery.
  - A robot that begins stationary cannot obtain repeated brake/stop reward.
  - P3 idle and acceleration gates remain satisfied.
- Verification:
  - Fixed braking battery, checkpoint comparisons, penalty-sign review, and
    visual rollout review. Initial budget 800-1500 iterations; do not advance
    after a failed maximum-budget review.
- Dependencies:
  - P3 done.

### P5: Stage C full-cycle and coast training

- Status: pending
- Scope:
  - Resume P4 and make full cycles the dominant scenario while retaining
    acceleration, braking, coast-only, and idle buckets.
  - Add only the smallest measured style/smoothness regularization needed after
    the physical skills exist.
- Non-scope:
  - Strong DR, obstacle decisions, reverse/turning, release export, or hardware.
- Deliverables:
  - One accepted nominal full-cycle checkpoint.
- Required inputs:
  - Accepted P4 checkpoint and authorized CUDA GPU use.
- Acceptance criteria:
  - Meet the P1-frozen full-cycle success and coast-retention gates for multiple
    consecutive evaluations.
  - Stage transitions do not introduce falls, large impacts, frantic stepping,
    limit slamming, braking regression, or idle drift.
  - P3 and P4 fixed batteries remain passing.
- Verification:
  - Full command-sequence battery, individual skill regression batteries, video
    review, and reward-mass/penalty-sign review. Initial budget 1500-2500
    iterations.
- Dependencies:
  - P4 done.

### P6: Stage D robustness, export, and deployment rehearsal

- Status: pending
- Scope:
  - Resume P5 in a rebuilt environment process and progressively introduce
    wheel-bearing friction, mass/inertia, CoM/head-CoM, actuator friction,
    armature, encoder bias, IMU misalignment, and finally measured pushes.
  - Retain nominal scenario samples and delay each hardening step when nominal
    skill metrics fall at a stage boundary.
  - Derive conservative braking deceleration/distance statistics, export the
    selected checkpoint through the official path, and run CPU MuJoCo inference
    with the production command semantics.
- Non-scope:
  - Real-robot execution, external runtime changes, perception/planning,
    reverse/turning, or policy publication unless separately authorized.
- Deliverables:
  - Accepted robust checkpoint, official ONNX, randomized evaluation report,
    conservative braking envelope for the higher-level controller, and CPU
    deployment-rehearsal results.
- Required inputs:
  - Accepted P5 checkpoint, authorized CUDA GPU use, and local disk capacity for
    checkpoints/logs.
- Acceptance criteria:
  - Meet the final nominal and randomized thresholds frozen from P1/P6 measured
    physics, including full-cycle success, fall rate, braking p95, slip, residual
    speed, and overshoot.
  - Backlash/base model relationship and observation contract remain correct.
  - ONNX contains the observation normalizer and produces the intended positive,
    zero, negative, and final-zero response in CPU rehearsal.
- Verification:
  - Randomized fixed batteries, nominal regression batteries, visual rollout
    review, relevant full CPU tests, official export validation, and
    `scripts/infer_policy.py` or the P1 evaluator against the exported ONNX.
    Initial budget 1500-2500 iterations; optional harder Stage E proceeds only
    if metrics still improve and its scope remains within this phase's preflight.
- Dependencies:
  - P5 done.

## Cross-phase risks

- Reward hacking through passive-wheel spin, fall-forward motion, stationary
  brake rewards, repeated stop bonuses, or reverse overshoot.
- The actor has no body or passive-wheel speed observation. Idle and coast must
  share a safe neutral action, and precise speed/stop confirmation remains a
  higher-level closed-loop responsibility.
- Strong early action-rate, pose, or angular-motion regularization can recreate
  the stationary optimum.
- Introducing startup DR requires rebuilding the environment process while
  loading the same checkpoint; mutating copied cfg objects is ineffective.
- Fixed training metrics may look successful while visual behavior is unsafe;
  every phase therefore includes deterministic rollout and video review.
- A reward/command semantic correction may invalidate the checkpoint chain. Such
  a discovery requires stopping, recording the decision, and re-preflighting
  rather than silently continuing.

## Final acceptance criteria

- One registered, documented, 61D-compatible roller policy completes idle,
  acceleration, coast, commanded braking, deceleration, and stable stop under
  nominal and agreed randomized conditions.
- The original roller task remains an unchanged baseline.
- Training evidence distinguishes real translation from wheel spin and records
  skill-specific metrics rather than relying on total reward.
- The selected checkpoint passes all phase regression batteries and the official
  ONNX export plus CPU inference rehearsal.
- The measured conservative braking envelope is available to the higher-level
  controller; obstacle/range logic and real-hardware use remain outside scope.

## Decisions and measured results

- 2026-09-09: Classified as `phased` because braking, combined behavior, and DR
  depend on earlier measured physics and accepted checkpoints.
- 2026-09-09: One policy and task ID will cover all low-level phases; no separate
  acceleration/braking deployment policies.
- 2026-09-09: Command semantics fixed as positive acceleration effort, exact-zero
  coast/idle, and negative braking effort. Negative is not reverse.
- 2026-09-09: Actor observation layout remains 61D. Speed estimation and brake
  trigger decisions stay above the policy.
- 2026-09-09: Initial development uses automatic metric logging and explicit
  checkpoint gates, not blind fixed-iteration promotion or automatic reward
  tuning.
- 2026-09-12: The user approved the complete P2 implementation plan for issue
  tracking. Development commands will run through the `microduck` conda context
  with project dependencies supplied by `uv run`; the Stage A mix is frozen at
  78% acceleration, 20% exact-zero idle, and 2% rolling-entry brake seed. This
  planning update does not authorize P2 implementation, training, or a commit.
- 2026-09-09 P1 evaluator:
  - Added `scripts/eval_roller_policy.py`. It reuses the BAM M6 actuator and
    61D observation implementation in `scripts/infer_policy.py`, creates a fresh
    MuJoCo/BAM runtime for every case, initializes all four wheel speeds with
    `omega * 0.0175 = body_speed`, and emits body motion, wheel motion, slip,
    tilt, heading, coast, and stop metrics as JSON.
  - Evaluated the existing final ONNX at 50 Hz, 7.4 V, voltage-drop gain 0.1,
    wheel friction `0`, `0.0015`, and `0.003`, and rolling-entry speeds `0.1`,
    `0.2`, and `0.3 m/s`. A stop means `|body_speed| <= 0.05 m/s` continuously
    for 0.5 s; a fall means tilt at least 60 degrees or trunk z at most 0.08 m.
  - Full result:
    `logs/rsl_rl/velocity_rollers/2026-09-07_17-48-02_Mjlab-Velocity-Flat-MicroDuck-Rollers_01/p1_baseline.json`.
    Two complete 16-case runs with seed 0 were numerically identical
    (`max_numeric_delta = 0`); none of the deterministic cases fell.
- 2026-09-09 measured baseline:
  - Idle settled to effectively zero speed and drifted 0.0101 m over 4 s.
  - Commands `0.10`, `0.20`, and `0.25` travelled only 0.0003, 0.0008, and
    0.0012 m in 5 s. Commands `0.30`, `0.40`, and `0.60` reached about
    `0.395-0.398 m/s`, but accumulated about 71, 72, and 89 degrees of heading
    error. This confirms a sharp command dead zone and poor straight tracking.
  - From `0.20 m/s`, 0.5 s coast retention was 0.84 at zero wheel friction,
    0.55 at nominal `0.0015`, and 0.20 at `0.003`. Nominal passive coast stopped
    in 0.78 s over 0.095 m.
  - At nominal friction, braking from `0.10`, `0.20`, and `0.30 m/s` stopped in
    0.24/0.76/1.30 s over 0.024/0.093/0.209 m. The matched `0.20 m/s` brake and
    passive-coast values differ by less than 3%; at zero wheel friction, a brake
    command left `0.157 m/s` after 4 s. Existing-policy stopping is therefore
    almost entirely bearing drag, not learned braking.
  - In the shortened full cycle, braking began while still moving at
    `0.216 m/s`, stopped in 0.92 s over 0.114 m, and held the final stop, but the
    preceding acceleration/coast accumulated unsafe heading drift.
- Frozen provisional nominal gates for P2-P5 (change only with recorded measured
  evidence):
  - P2 constants/tests: wheel radius `0.0175 m`; rolling-entry speeds
    `0.10/0.20/0.30 m/s`; stop threshold `0.05 m/s` with 0.5 s dwell; stop
    upright limit 30 degrees; reverse-overshoot cap `0.03 m/s`.
  - Common nominal safety: no fall in any fixed case, trunk z stays above
    `0.09 m`, max tilt is at most 30 degrees, and p95 absolute wheel/body slip
    is at most `0.15 m/s`. A nominal multi-rollout battery, when used, must have
    fall rate at most 5%.
  - P3 idle: at most 0.03 m drift in 4 s and final absolute speed at most
    `0.02 m/s`. Every positive command bucket `0.10-0.25` must travel at least
    0.05 m in 5 s and finish with forward speed above `0.02 m/s`. Commands
    `0.30-0.60` must reach `0.20 m/s` within 1.5 s, travel at least 1.0 m in
    5 s, hold `0.25-0.50 m/s` over the last second, and stay within 30 degrees
    of spawn heading.
  - P4 braking: from nominal `0.10/0.20/0.30 m/s`, stop within
    `0.25/0.60/1.05 s` and `0.025/0.075/0.17 m`; final residual speed is at most
    `0.05 m/s`, reverse overshoot is at most `0.03 m/s`, and the stop remains
    upright. At matched nominal `0.0015` friction, braking time and distance
    must each be at most 80% of passive-coast values. At zero wheel friction from
    `0.20 m/s`, the policy must still stop within 3.0 s and 0.50 m, proving
    active braking rather than bearing-drag dependence.
  - P5 coast/full cycle: retain at least 50% of `0.20 m/s` after a 0.5 s coast
    at nominal friction; enter the brake segment at or above `0.15 m/s`; meet
    the applicable P4 stop gate; drift at most 0.02 m during the final 2 s
    stop; and keep total heading change within 45 degrees. All fixed P3/P4
    regression cases must remain passing for three consecutive checkpoint
    evaluations before P6 preflight.
- P1 verification:
  - `uv run --with pytest pytest -q tests/test_eval_roller_policy.py tests/test_infer_policy_bam.py`
    -> 7 passed.
  - `uv run --with pytest pytest tests/` -> 204 passed, 1 skipped.
  - Two complete evaluator repeats -> identical, 16 cases each, no falls.
  - `git diff --check` -> passed.
  - `uv run ruff check ...` was attempted but no `ruff` executable is installed;
    lint was not run and is not claimed.
- P2 verification:
  - `conda run -n microduck uv run list-envs` displayed both new task IDs;
    an explicit registry assertion for both IDs passed.
  - `conda run -n microduck uv run --with pytest pytest -q
    tests/test_roller_accel_brake.py tests/test_infer_policy_bam.py
    tests/test_wheel_glide.py` -> 15 passed.
  - `conda run -n microduck uv run --with pytest pytest tests/` -> 212 passed,
    1 skipped.
  - `conda run -n microduck bash -lc 'WANDB_MODE=disabled uv run train
    Mjlab-RollerAccelBrake-Flat-MicroDuck --env.scene.num-envs 64
    --agent.max_iterations 5'` -> completed on CUDA. Actor observation shape
    was 61, action shape was 14, no NaN/dimension/indexing/reward/termination
    failure occurred, and every logged weighted penalty was non-positive.
    Final smoke log: `logs/rsl_rl/roller_accel_brake/2026-09-12_01-09-46_roller_accel_brake`.
  - `git diff --check` -> passed.
- P3 training result: pending.
- P4 training result: pending.
- P5 training result: pending.
- P6 robustness/export result: pending.
