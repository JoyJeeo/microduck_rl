# MicroDuck 训练备忘

本文记录本次对话确认的训练与仿真查看方式。

## 运行环境

本仓库的所有命令都在 Conda 的 `microduck` 环境中执行。未手动激活环境时使用：

```bash
conda run -n microduck <command>
```

## 可训练任务

仓库当前注册了 33 个 MicroDuck 任务，共 13 类：

- `Velocity`：平地/粗糙地面速度与转向跟踪，是首选的基础行走任务。
- `VelStand`：行走、摔倒恢复和身体姿态控制合并在一个策略中。
- `StandUp`：从坐姿、趴地或仰面恢复站立。
- `SitStand`：一个策略完成受指令控制的坐下与起立。
- `GroundPick`：嘴部接近地面后恢复站立。
- `BallKick`：站立状态下踢球；当前默认右脚。
- `Roulade`：向前翻滚并重新站立。
- `Roller Velocity`：穿被动轮 Roller 推蹬、滑行和刹车。
- `Roller Swizzle`：双脚着地的对称葫芦步，真实机器人迁移优先于交替抬脚 Roller 任务。
- `Roller Crouch`：滑行中下蹲再站起。
- `Roller Slope`：在斜坡上滑行并保持平衡。
- `Roller StandUp`：穿 Roller 从地面起身。
- `Spin`：穿 Roller 原地快速旋转后稳定停止。

常见任务后缀：

- `Flat`：平地，适合首次训练。
- `Rough`：粗糙地形。
- `Backlash`：加入每个舵机约 +/-1 度的齿隙，用于 sim2real 鲁棒性和 A/B 对照。
- `Rollers`：14 个主动舵机关节加 4 个被动轮关节。

推荐从以下任务开始：

```text
Mjlab-Velocity-Flat-MicroDuck
```

## Smoke Test

正式长时间训练前必须先运行 64 环境、5 iterations 的 Smoke Test：

```bash
conda run -n microduck uv run train Mjlab-Velocity-Flat-MicroDuck \
  --env.scene.num-envs 64 \
  --agent.max-iterations 5 \
  --agent.run-name smoke_velocity \
  --agent.logger tensorboard \
  --enable-nan-guard True
```

成功标准：命令正常完成，没有 CUDA OOM 或 NaN，环境、观测和奖励均能计算。

`--gpu-ids 0` 不符合当前 Tyro 解析器要求。单卡 GPU 0 不需要传该参数，因为默认值已经是 `[0]`；使用全部 GPU 时可传 `--gpu-ids all`。启动时出现的 `geom-names-expr` list/tuple Tyro warning 不是训练失败原因。

## 推荐正式训练命令

假设使用单张 GPU，从零训练平地行走：

```bash
conda run -n microduck uv run train Mjlab-Velocity-Flat-MicroDuck \
  --env.scene.num-envs 4096 \
  --agent.max-iterations 5000 \
  --agent.save-interval 250 \
  --agent.run-name velocity_flat_01 \
  --agent.logger wandb \
  --agent.seed 42 \
  --enable-nan-guard True
```

核心参数：

| 参数 | 推荐值 | 说明 |
| --- | ---: | --- |
| `--env.scene.num-envs` | `4096` | 显存不足时依次降为 `2048`、`1024`；Smoke Test 用 `64`。 |
| `--agent.max-iterations` | `5000` | 行走任务通常按 `4000-6000` 规划。 |
| `--agent.save-interval` | `250` | 每 250 iterations 保存一次 checkpoint。改为 `100` 可更频繁观察，但增加 I/O。 |
| `--agent.run-name` | `velocity_flat_01` | 标识本次实验，建议每次使用不同名称。 |
| `--agent.logger` | `wandb` | 正式训练使用 W&B；一次性 Smoke Test 可用 `tensorboard`。 |
| `--agent.seed` | `42` | 重复实验可改为 `43`、`44` 等。 |
| `--enable-nan-guard` | `True` | 首次正式训练建议开启。 |

首轮训练保持仓库默认的 PPO、网络、观测归一化、Domain Randomization 和 `decimation=4`，不要同时修改这些参数。当前策略频率为 50 Hz，Actor/Critic 默认 MLP 均为 `512 -> 256 -> 128`。

## 查看训练中的策略

训练日志和 checkpoint 位于：

```text
logs/rsl_rl/velocity/<时间>_velocity_flat_01/
```

等 `model_250.pt` 出现后，在另一个终端启动 Viser：

```bash
conda run -n microduck uv run play Mjlab-Velocity-Flat-MicroDuck \
  --checkpoint-file /home/zhangyutao/Mount/yuto/codes/microduck_rl/logs/rsl_rl/velocity/<时间>_velocity_flat_01/model_250.pt \
  --num-envs 1 \
  --device cpu \
  --viewer viser
```

在 Viser 的 `Checkpoints` 页面中：

- `Sync`：重新扫描训练目录中的 checkpoint。
- `Use Latest`：加载最新 checkpoint。
- 下拉框：比较不同训练阶段的模型。

`play` 是 checkpoint 的独立评估仿真，并非训练进程中的同一个环境。使用 `--device cpu` 可以避免 Viewer 与训练争抢 GPU。

## 可选训练视频

如果还希望保留训练进程中实际随机 rollout 的视频，可在正式训练命令后增加：

```bash
--video True \
--video-length 200 \
--video-interval 6000
```

`6000 = 250 iterations * 24 steps`，所以视频与 checkpoint 对齐。视频写入：

```text
logs/rsl_rl/velocity/<run目录>/videos/train/
```

录制会降低训练速度；已经使用 Viser 时可以不启用。

## 在旧模型上继续训练

续训必须同时指定原 run、checkpoint 和 `resume=True`。本次实际使用的是：

```bash
conda run -n microduck uv run train Mjlab-Velocity-Flat-MicroDuck \
  --env.scene.num-envs 4096 \
  --agent.max-iterations 5000 \
  --agent.save-interval 250 \
  --agent.run-name velocity_flat_resume_01 \
  --agent.logger wandb \
  --agent.load-run 2026-09-03_09-57-53_velocity_flat_01 \
  --agent.load-checkpoint model_4999.pt \
  --agent.resume True \
  --enable-nan-guard True
```

这次续训从 `model_4999.pt` 开始，又训练了 5000 iterations，checkpoint 编号继续增长到 `model_9998.pt`。续训不要覆盖原 run，使用新的 `run-name` 便于对比和回退。

## 查看本次最终模型

用本地最终 checkpoint 启动独立的 Viser 评估：

```bash
conda run -n microduck uv run play Mjlab-Velocity-Flat-MicroDuck \
  --checkpoint-file /home/zhangyutao/Mount/yuto/codes/microduck_rl/yuto/weight/2026-09-03_12-08-38_velocity_flat_resume_01/model_9998.pt \
  --num-envs 1 \
  --device cpu \
  --viewer viser
```

也可以直接引用 W&B run：

```bash
conda run -n microduck uv run play Mjlab-Velocity-Flat-MicroDuck \
  --wandb-run-path z1286953465-leju/mjlab_microduck/p18m5i8n \
  --num-envs 1 \
  --device cpu \
  --viewer viser
```

## ONNX 导出和 CPU MuJoCo 演练

ONNX 必须通过仓库的 `scripts/export.py` 导出，因为观测归一化器需要烘焙进模型；不要手工转换 checkpoint。

```bash
conda run -n microduck uv run scripts/export.py \
  Mjlab-Velocity-Flat-MicroDuck \
  --wandb-run-path z1286953465-leju/mjlab_microduck/p18m5i8n
```

本次已有的 `yuto/weight/velocity.onnx` 是完整 Duck 行走策略，输入为 `1 x 61`，输出为 `1 x 14`。在 CPU MuJoCo 中运行：

```bash
conda run -n microduck --no-capture-output uv run \
  scripts/infer_policy.py \
  --walking yuto/weight/velocity.onnx \
  --new-cmd-obs
```

键盘输入由启动命令的终端读取，不由 MuJoCo 窗口读取。需要保持终端处于焦点，并保证 stdin 是 TTY；未激活 Conda 环境时使用上面的 `--no-capture-output`。方向键调整速度，`A/E` 调整转向，空格清零命令。`--new-cmd-obs` 只表示使用统一的 61D command observation，本身不会启用键盘。

## 单 XL330 Sim2Real 对比的边界

`scripts/testbench_sim2real.py` 是单 XL330 测试台工具，要求专门的测试台策略：

```text
输入：1 x 4  = [joint_pos, joint_vel, last_action, command]
输出：1 x 1  = 单舵机动作
```

当前 `velocity.onnx` 是整台 Duck 的 `61D -> 14D` 策略，不能直接传给该工具。即使绕过当前默认 BAM 仿真后端的 `joint.damping = 0.0` MuJoCo 类型报错，下一步仍会因 ONNX 输入维度不匹配而失败。

只有在获得单舵机测试台 ONNX 后，才适用以下流程：

```bash
# 仿真 XL330；mjlab 后端可绕过当前 BAM/MjSpec damping 赋值报错
conda run -n microduck uv run python scripts/testbench_sim2real.py \
  --mode sim \
  --sim-backend mjlab \
  --onnx testbench_policy.onnx \
  --out sim.npz

# 真实 XL330。执行前必须固定机械结构并确认端口、ID、急停和运动范围
conda run -n microduck uv run python scripts/testbench_sim2real.py \
  --mode real \
  --onnx testbench_policy.onnx \
  --out real.npz \
  --port /dev/ttyUSB0 \
  --motor-id 1

# 比较轨迹
conda run -n microduck uv run python scripts/testbench_sim2real.py \
  --compare sim.npz real.npz \
  --out-plot comparison.png
```

如果要比较 `velocity.onnx`，需要完整 Duck 的 14 舵机真实运行端、61D 观测构造、相同命令输入和同步记录，再与整机 MuJoCo rollout 对齐。当前单舵机测试台脚本不提供这条完整链路，本次也没有进行补齐开发。

## W&B 与本地参数记录

本次两次正式训练使用 W&B，项目为 `mjlab_microduck`：

| 训练 | W&B run ID | 本地训练目录 |
| --- | --- | --- |
| 原始训练 `velocity_flat_01` | `dwreccdt` | `yuto/weight/2026-09-03_09-57-53_velocity_flat_01/` |
| 续训 `velocity_flat_resume_01` | `p18m5i8n` | `yuto/weight/2026-09-03_12-08-38_velocity_flat_resume_01/` |

在线页面：

- 原始训练：<https://wandb.ai/z1286953465-leju/mjlab_microduck/runs/dwreccdt>
- 续训：<https://wandb.ai/z1286953465-leju/mjlab_microduck/runs/p18m5i8n>

最新续训已确认正常结束并同步。完整环境和训练参数在：

```text
yuto/wb/run-20260903_120842-p18m5i8n/files/config.yaml
```

最终指标摘要在：

```text
yuto/wb/run-20260903_120842-p18m5i8n/files/wandb-summary.json
```

`.wandb` 文件保存完整事件历史，是 W&B 的二进制记录，不适合直接作为文本打开。此前的 `smoke_velocity` 明确使用 `--agent.logger tensorboard`，因此不会出现在 W&B。

本地查看原始训练和续训的 TensorBoard 曲线：

```bash
conda run -n microduck uv run tensorboard \
  --logdir yuto/weight \
  --port 6006
```

然后访问 <http://localhost:6006>。

## 仓库中的其他常用功能

- `uv run list-envs`：列出实际注册的训练任务。
- `scripts/export.py`：从 W&B checkpoint 正确导出带观测归一化的 ONNX。
- `scripts/infer_policy.py`：在 CPU MuJoCo 中演练 ONNX 和键盘命令。
- `scripts/testbench_sim2real.py`：单 XL330 仿真/真实轨迹记录与对比。
- `uv run --with pytest pytest tests/`：运行配置不变量和 MDP 回归测试。
- 训练命令加 `--hf-jobs`：提交到 Hugging Face Jobs。
