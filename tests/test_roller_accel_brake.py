import re

import pytest
import torch

from mjlab_microduck.tasks import mdp
from mjlab_microduck.tasks.microduck_roller_accel_brake_env_cfg import (
    EPISODE_LENGTH_S,
    MicroduckRollerAccelBrakeRlCfg,
    make_microduck_roller_accel_brake_env_cfg,
)
from mjlab_microduck.tasks.microduck_velocity_rollers_env_cfg import (
    make_microduck_velocity_rollers_env_cfg,
)


def test_stage_a_scenarios_and_command_buckets_are_fixed():
    cfg = make_microduck_roller_accel_brake_env_cfg()
    command = cfg.commands["twist"]
    assert command.scenario_probabilities == (0.20, 0.78, 0.0, 0.02, 0.0)
    assert command.positive_commands == (0.10, 0.20, 0.25, 0.30, 0.40, 0.60)
    assert command.brake_command == -0.50
    assert command.rolling_entry_speeds == (0.10, 0.20, 0.30)
    ids = mdp.roller_scenario_ids(torch.tensor([0.00, 0.199, 0.20, 0.979, 0.98]), command.scenario_probabilities)
    assert ids.tolist() == [mdp.ROLLER_IDLE, mdp.ROLLER_IDLE, mdp.ROLLER_ACCEL, mdp.ROLLER_ACCEL, mdp.ROLLER_BRAKE]


def test_cfg_preserves_contract_and_disables_early_hardening():
    cfg = make_microduck_roller_accel_brake_env_cfg()
    base = make_microduck_velocity_rollers_env_cfg()
    assert cfg.episode_length_s == EPISODE_LENGTH_S == 12.0
    for group in ("actor", "critic"):
        assert list(cfg.observations[group].terms) == list(base.observations[group].terms)
    assert "expand_bam_friction_fields" in cfg.events
    assert "roller_accel_brake_reset" in cfg.events
    for name in ("push_robot", "randomize_wheel_friction", "randomize_com", "randomize_armature"):
        assert name not in cfg.events
    assert not cfg.curriculum
    assert "action_rate_l2" not in cfg.rewards
    assert MicroduckRollerAccelBrakeRlCfg.algorithm.symmetry_cfg is None


def test_base_and_backlash_tasks_are_registered():
    from mjlab.tasks.registry import list_tasks

    import mjlab_microduck.tasks  # noqa: F401

    tasks = list_tasks()
    assert "Mjlab-RollerAccelBrake-Flat-MicroDuck" in tasks
    assert "Mjlab-RollerAccelBrake-Flat-Backlash-MicroDuck" in tasks


def test_new_rewards_have_safe_signs_and_old_wheel_farming_is_gone():
    cfg = make_microduck_roller_accel_brake_env_cfg()
    assert "wheel_speed" not in cfg.rewards
    assert "braking" not in cfg.rewards
    assert cfg.rewards["body_forward_motion"].weight > 0.0
    assert cfg.rewards["acceleration_progress"].weight > 0.0
    assert cfg.rewards["braking_progress"].weight > 0.0
    assert cfg.rewards["coast_retention"].weight == 0.0
    for name in ("wheel_body_slip", "reverse_overshoot"):
        assert cfg.rewards[name].weight < 0.0


def test_rolling_wheel_selector_matches_base_and_backlash_models():
    import mujoco

    from mjlab_microduck.robot.microduck_constants import get_rollers_backlash_spec, get_walk_rollers_spec

    for spec_fn in (get_walk_rollers_spec, get_rollers_backlash_spec):
        model = spec_fn().compile()
        names = [
            mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, joint_id)
            for joint_id in range(model.njnt)
            if model.jnt_type[joint_id] != mujoco.mjtJoint.mjJNT_FREE
        ]
        assert len([name for name in names if re.fullmatch(r"^passive_.*wheel", name)]) == 4
        assert len([name for name in names if not name.startswith("passive_")]) == 14


class _CommandManager:
    def __init__(self, command):
        self.command = command

    def get_term(self, _name):
        return self.command


class _Env:
    def __init__(self, command):
        self.command_manager = _CommandManager(command)


def _reward_command(speed=0.0, delta=0.0, phase=mdp.ROLLER_PHASE_ACCEL):
    command = object.__new__(mdp.RollerAccelBrakeCommand)
    command.previous_speed = torch.tensor([speed])
    command.speed_delta = torch.tensor([delta])
    command.phase = torch.tensor([phase])
    command.prior_motion = torch.tensor([speed != 0.0])
    command.stop_bonus_pending = torch.tensor([False])
    command.refresh_state = lambda: None
    return command


def test_body_motion_and_signed_progress_cannot_be_farmed_at_rest():
    stationary = _Env(_reward_command())
    assert mdp.roller_forward_motion(stationary).item() == 0.0
    assert mdp.roller_acceleration_progress(stationary).item() == 0.0
    braking = _Env(_reward_command(speed=0.0, delta=0.0, phase=mdp.ROLLER_PHASE_BRAKE))
    assert mdp.roller_braking_progress(braking).item() == 0.0
    assert sum(mdp.roller_signed_progress(torch.tensor([b]), torch.tensor([a])).item() for a, b in ((0.0, 0.1), (0.1, 0.0))) == 0.0


def test_braking_progress_and_stop_bonus_have_the_intended_direction_and_latch():
    command = _reward_command(speed=0.10, delta=-0.05, phase=mdp.ROLLER_PHASE_BRAKE)
    command.stop_bonus_pending[:] = True
    env = _Env(command)
    assert mdp.roller_braking_progress(env).item() == pytest.approx(0.05)
    assert mdp.roller_stop_success_bonus(env).item() == 1.0
    assert mdp.roller_stop_success_bonus(env).item() == 0.0


def test_command_reset_clears_stop_latches_without_resampling_prepared_scenario():
    command = object.__new__(mdp.RollerAccelBrakeCommand)
    command._prepared = torch.tensor([True])
    command.metrics = {}
    command.command_counter = torch.zeros(1, dtype=torch.long)
    command.scenario = torch.tensor([mdp.ROLLER_BRAKE])
    command.phase = torch.tensor([mdp.ROLLER_PHASE_DONE])
    command.elapsed = torch.ones(1)
    command.entry_speed = torch.tensor([0.2])
    command.previous_speed = torch.ones(1)
    command.speed_delta = torch.ones(1)
    command.prior_motion = torch.tensor([False])
    command.stop_dwell = torch.ones(1)
    command.stop_success = torch.tensor([True])
    command.stop_bonus_pending = torch.tensor([True])
    command.max_reverse_speed = torch.ones(1)
    command.brake_start_x = torch.ones(1)
    command._stop_speed = 0.05
    command._last_refresh_step = 5
    command._update_command = lambda: None
    command.reset(torch.tensor([0]))
    assert command.phase.item() == mdp.ROLLER_PHASE_BRAKE
    assert command.prior_motion.item() is True
    assert not command.stop_success.item()
    assert not command.stop_bonus_pending.item()
    assert command.stop_dwell.item() == 0.0
