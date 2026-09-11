"""Nominal roller acceleration, coast, braking, and stable-stop task."""

from copy import deepcopy

from mjlab.managers import EventTermCfg, RewardTermCfg, TerminationTermCfg
from mjlab.tasks.velocity import mdp

from mjlab_microduck.tasks import mdp as microduck_mdp
from mjlab_microduck.tasks.microduck_velocity_rollers_env_cfg import (
    MicroduckRollersRlCfg,
    make_microduck_velocity_rollers_env_cfg,
)


EPISODE_LENGTH_S = 12.0


def make_microduck_roller_accel_brake_env_cfg(play: bool = False):
    """Derive from the roller recipe without copying its sim2real stack."""
    cfg = make_microduck_velocity_rollers_env_cfg(play=play)
    cfg.episode_length_s = EPISODE_LENGTH_S

    # P2 is nominal skill discovery: retain BAM/noise/delays/NaN safety, but do
    # not make a moving skill compete with pushes or randomized mechanics yet.
    for name in (
        "push_robot",
        "randomize_wheel_friction",
        "randomize_com",
        "randomize_head_com",
        "randomize_mass_inertia",
        "randomize_joint_friction",
        "randomize_armature",
        "encoder_bias",
    ):
        cfg.events.pop(name, None)
    cfg.curriculum.clear()
    cfg.observations["actor"].terms["base_ang_vel"].func = mdp.base_ang_vel
    cfg.observations["actor"].terms["base_ang_vel"].params = {}
    cfg.observations["actor"].terms["projected_gravity"].func = mdp.projected_gravity
    cfg.observations["actor"].terms["projected_gravity"].params = {}

    # The initial rolling reset writes world +X velocity, so make that direction
    # deterministic rather than reading stale post-reset derived orientation.
    cfg.events["reset_base"].params["pose_range"]["yaw"] = (0.0, 0.0)
    cfg.events["roller_accel_brake_reset"] = EventTermCfg(
        func=microduck_mdp.reset_roller_accel_brake,
        mode="reset",
        params={"command_name": "twist"},
    )

    command = cfg.commands["twist"]
    cfg.commands["twist"] = microduck_mdp.RollerAccelBrakeCommandCfg(**vars(command))

    # Replace wheel-spin and already-stopped rewards. New positive terms observe
    # trunk movement; all new costs are non-negative and have negative weights.
    keep = {"upright", "body_ang_vel", "self_collisions", "action_over_limit"}
    for name in list(cfg.rewards):
        if name not in keep:
            del cfg.rewards[name]
    cfg.rewards["body_forward_motion"] = RewardTermCfg(
        func=microduck_mdp.roller_forward_motion, weight=4.0,
    )
    cfg.rewards["acceleration_progress"] = RewardTermCfg(
        func=microduck_mdp.roller_acceleration_progress, weight=20.0,
    )
    cfg.rewards["braking_progress"] = RewardTermCfg(
        func=microduck_mdp.roller_braking_progress, weight=20.0,
    )
    cfg.rewards["coast_retention"] = RewardTermCfg(
        func=microduck_mdp.roller_coast_retention, weight=0.0,
    )
    cfg.rewards["wheel_body_slip"] = RewardTermCfg(
        func=microduck_mdp.roller_wheel_body_slip_cost, weight=-5.0,
    )
    cfg.rewards["reverse_overshoot"] = RewardTermCfg(
        func=microduck_mdp.roller_reverse_overshoot_cost, weight=-10.0,
    )
    cfg.rewards["stop_success"] = RewardTermCfg(
        func=microduck_mdp.roller_stop_success_bonus, weight=5.0,
    )

    cfg.terminations["stop_success"] = TerminationTermCfg(
        func=microduck_mdp.roller_stop_success, time_out=False,
    )
    cfg.terminations["scenario_complete"] = TerminationTermCfg(
        func=microduck_mdp.roller_scenario_complete, time_out=True,
    )
    return cfg


MicroduckRollerAccelBrakeRlCfg = deepcopy(MicroduckRollersRlCfg)
MicroduckRollerAccelBrakeRlCfg.experiment_name = "roller_accel_brake"
MicroduckRollerAccelBrakeRlCfg.run_name = "roller_accel_brake"
MicroduckRollerAccelBrakeRlCfg.save_interval = 200
