from contextlib import nullcontext
from types import SimpleNamespace

from mjlab_microduck.tasks.mdp import VelocityCommandCommandOnly


class _Handle:
    def __init__(self, value=None):
        self.value = value

    def on_update(self, callback):
        return callback

    def on_click(self, callback):
        return callback


class _Gui:
    def __init__(self):
        self.sliders = {}

    def add_folder(self, _name):
        return nullcontext()

    def add_checkbox(self, _name, initial_value):
        return _Handle(initial_value)

    def add_slider(self, name, *, initial_value, min, max, **_kwargs):
        assert min <= initial_value <= max
        handle = _Handle(initial_value)
        handle.min = min
        handle.max = max
        self.sliders[name] = handle
        return handle

    def add_button(self, _name, **_kwargs):
        return _Handle()


def test_velocity_gui_accepts_disabled_zero_range_axes():
    gui = _Gui()
    command = SimpleNamespace(
        cfg=SimpleNamespace(
            ranges=SimpleNamespace(
                lin_vel_x=(-0.5, 0.6),
                lin_vel_y=(0.0, 0.0),
                ang_vel_z=(0.0, 0.0),
            )
        )
    )

    VelocityCommandCommandOnly.create_gui(
        command, "twist", SimpleNamespace(gui=gui), lambda: 0
    )

    assert gui.sliders["Max lin_vel_y"].min == 0.0
    assert gui.sliders["lin_vel_y"].min == gui.sliders["lin_vel_y"].max == 0.0
