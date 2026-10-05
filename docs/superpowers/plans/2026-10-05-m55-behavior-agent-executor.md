# M55 BehaviorAgent Executor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trả lời CÓ/KHÔNG việc tái dùng BehaviorAgent CARLA 0.9.16 làm executor nhận lệnh, bằng audit mã và sáu phép thử, không viết lại LocalPlanner.

**Architecture:** Spike riêng với M21: subclass mỏng bỏ decision pipeline tự trị của BehaviorAgent, đưa route/tốc độ từ tầng trên vào LocalPlanner nguyên bản, rồi áp dụng safety governor dùng chung. Runner điều khiển NPC bằng script không phản ứng, ghi snapshot/command/override/collision theo tick; evaluator offline chấm protocol đã khóa. Mã mới là mã thử nghiệm, không phải executor production.

**Tech Stack:** Python 3.10 hiện có, CARLA 0.9.16, stock agents và các dependency hiện có của chúng, pytest, JSON/CSV, PowerShell/Git. Không nâng package trong spike.

**Spec:** `docs/superpowers/plans/2026-10-05-m55-behavior-agent-executor.md#spec-va-protocol-can-duyet` — brief M55 và quyết định T1 được ghi trong phần protocol dưới đây; feasibility spike không tạo production design spec riêng.

## Global Constraints

- CARLA 0.9.16; Town03; bước cố định 0.05 s; chế độ đồng bộ; đoạn đường thẳng ≥200 m.
- Xe dẫn dùng constant-speed script, cấm TrafficManager/autopilot; NPC khác cũng dùng script không phản ứng với ego.
- Các cách gọi `set_command` phải đúng mục Interfaces; public units: m, s, m/s, m/s²; stock planner/PID nhận km/h.
- Giữ nguyên `agents/navigation/local_planner.py:LocalPlanner` và stock controller; không monkey-patch, subclass thay thuật toán hoặc viết local tracker thay thế trong wrapper.
- Lớp C/lớp an toàn dùng cùng đường mã + cùng tham số ở mọi thí nghiệm; ghi hash mã/options, không branch theo trial ID.
- T1 đã duyệt: ổn định ở 10 → phát SET_SPEED(12) → khi ego đạt 12 m/s thì phát LANE_KEEP, bắt đầu đo 15 s với xe dẫn 10 m/s, khoảng cách đầu–đuôi 20 m.
- 10/12 m/s là tham số team chọn và được duyệt; không đổi giữa chừng khi chạy.
- Khóa toàn bộ tham số sau khi duyệt. Revision thay tham số cần Nguyễn Trung Dũng/người yêu cầu duyệt lại và chạy lại toàn matrix.
- Nếu phép 1,2,3,4,6 đạt mà KHÔNG phải viết lại local planner → CÓ; T5 chỉ báo số liệu, không đạt/rớt.
- Nếu phải viết lại hoặc sửa trên 500 dòng mã agent, không tính dòng trắng/chú thích/test → KHÔNG kèm lý do kỹ thuật. Đếm cả mã executor/safety mới, không chỉ diff của file stock.
- Không sửa/dùng executor M55 trong M21, pipeline/controller ego cũ hoặc raw TM cũ. Không sửa install `E:/Carla`.
- Không chạy được thì báo lý do, đừng im lặng. Không dùng unit tests/audit thay cho live evidence hoặc tạo số liệu giả.
- Không reset/stage thay đổi người dùng. Khi thực thi, dùng workspace cô lập theo using-git-worktrees; chỉ commit đường dẫn M55.

## Review Focus

1. Route hết/rẽ nhánh: fail closed, không tự sinh waypoint/reroute; Task 3 kiểm thử.
2. SET_SPEED giữa lúc nhập làn: không hủy route hoặc reset timer 6 s; Task 3 kiểm thử.
3. Bbox lệch tâm/xoay, closing speed ≤0: dùng mép thật, không trừ extent hai lần hoặc ép TTC hữu hạn; Task 2/4 kiểm thử.
4. Command/override/collision lệch một tick: liên kết snapshot trước control và frame sensor thật; Task 5 kiểm thử.
5. Thiếu tick hoặc khác config/hash/attempt: không pass, nội suy hoặc chọn run đẹp; Task 1/2/6 kiểm thử.

---

## Trạng thái và bằng chứng chỉ đọc

**Plan để duyệt, chưa cho phép implementation/live trials.** Chuỗi T1 A đã duyệt; các ngưỡng vận hành/giả định bổ sung dưới đây cần duyệt cùng plan. Chưa có kết quả sáu phép thử.

Rà soát ngày 2026-10-05; không gọi tick, spawn, apply settings/control:

| Bằng chứng | Giá trị |
|---|---|
| Workspace HEAD | `6c08969`, baseline old1b đã commit |
| Agent source | `E:/Carla/PythonAPI/carla/agents/navigation/behavior_agent.py` |
| BehaviorAgent SHA-256 | `2b8f046e4e3efa07d6d21b5ea4420a43a232ce297c3932434477563eb04b143f` |
| LocalPlanner SHA-256 | `9250a88536a04ee30ee19b01c3b3764388295cf3f438123e2b2c88b647096b4f` |
| Source git commit | Không có: install CARLA là bundle không có `.git`; workspace commit không phải commit CARLA |
| Interpreter/API | Python 3.10.11; `C:/Users/ADMIN/AppData/Local/Programs/Python/Python310/lib/site-packages/carla/__init__.py` |
| API actual | Client/server `0.9.16`, map `Carla/Maps/Town03`, sync `True`, fixed delta `0.05` |
| OpenDRIVE SHA-256 | `abf177bcd9b66cfefb7ac4919f6456815f1384f4229f1343c8a6a90bbb7713c9` |

Đã đối chiếu bốn file `behavior_agent.py`, `local_planner.py`, `basic_agent.py`, `controller.py` với [nguồn tag 0.9.16 chính thức](https://github.com/carla-simulator/carla/tree/0.9.16/PythonAPI/carla/agents/navigation): **nội dung khớp sau chuẩn hóa CRLF→LF, byte không giống do line endings**. SHA nguồn official BehaviorAgent là `d914ea06d94ebabec9b6df7148f11b3941cb55466ad0033017d6e44092a674f5`; vẫn báo SHA byte của file local ở output M55. Task 1 lưu lại provenance và kiểm tra các dependency còn lại/module thực sự import; không chuẩn hóa file local để đổi baseline hash.

Chưa chứng minh spawn, physics/control performance hoặc sensor delivery. Workspace có thay đổi ngoài scope; giữ nguyên `.gitignore`, `tests/test_dataset_builder_adaptive_radius.py`, `.agent/`, `experiments/__init__.py`, `scripts/tune_adaptive_radius.py`. Bash không hoạt động vì WSL chưa có distro; PowerShell hoạt động. Markdown bị ignore; chỉ force-add tài liệu đúng đường dẫn.

<a id="spec-va-protocol-can-duyet"></a>

## Spec và protocol cần duyệt

### T1: định nghĩa vận hành và tiêu chí 15 s

**Chuỗi A đã duyệt; ngưỡng dưới đây là đề xuất để duyệt cùng plan.**

1. Ổn định 10 m/s: `abs(v-10) <0.2 m/s` trong **60 tick liên tiếp** (3 s), dưới executor.
2. Phát `SET_SPEED(v_target=12.0,a_max=2.0,a_dec=3.0)`.
3. “Đạt 12”: `abs(v-12) <0.2 m/s` trong **20 tick liên tiếp** (1 s). Đúng 0.2 không đạt. Timeout chuẩn bị **20 s mỗi phase**; timeout → setup_invalid, không giảm ngưỡng.
4. Setup xe dẫn ở cuối preparation, trước marker LANE_KEEP: gap bbox **20.0±0.1 m tại lúc phát LANE_KEEP**, không phải SET_SPEED(12). Chỉ đo sau xác nhận actual gap. Không teleport/reset vận tốc ego trong đo.
5. Phát `LANE_KEEP`, giữ tốc độ lệnh **12 m/s**; safety được hạ tốc độ hiệu lực nhưng không đổi command state thành 10. Xe dẫn script **10 m/s mọi tick**, không quan sát ego.
6. Marker t=0 là snapshot ngay trước control tick đo đầu tiên. Lưu t=0 và 300 transition ticks đến t=15.00; thời gian mô phỏng, không wall-clock.

**T1 ĐẠT khi dữ liệu hợp lệ và đồng thời thỏa (a), (b), (c):**

- **(a) Không tự khởi xướng chuyển làn:** 0 lần `_tailgating`; 0 lần `lane_change`, `set_destination` hoặc thay global plan bởi source khác `upper_command`; không có route waypoint CHANGELANELEFT/RIGHT hay ra ngoài corridor giữ làn đã pin. Hook/counter ghi caller, reason, command_id cho route mutations. Kiểm tra độc lập mỗi tick: tâm ego trong corridor giữ làn (|e_y|≤half lane width), 0 lane-invasion sang làn kề. Road/lane ID có thể đổi ở nối đường: so với chuỗi lane của route, không bắt lane_id bất biến. Không chỉ nhìn xe chưa qua vạch để kết luận không có quyết định tự trị.
- **(b) Không va chạm:** 0 collision event liên quan ego hoặc xe dẫn trong 15 s; dùng frame sensor, drain callback trước đóng run. Collision trong preparation → setup_invalid, không bỏ qua.
- **(c) Giảm tốc bám xe dẫn:** có ≥1 tick safety override với tốc độ hiệu lực thấp hơn command 12, và ≥1 tick `v_ego <11.0 m/s` sau marker. Trong **5 s cuối** (101 snapshots t=10.00..15.00), `abs(v_ego-v_lead) ≤1.0 m/s` ở **mọi tick**. Gap >0 ở mọi tick của 15 s. Không áp dụng 5% ngoại lệ T6 cho T1. Báo first override, min/max speed/gap, max speed error 5 s cuối.

### T2–T6

| Phép | Setup/lệnh | Tiêu chí |
|---|---|---|
| T2 | Ego10; target-left front/rear script10; gap mép mỗi phía25 tại t0; LEFT(15,6) | Complete≤6 s từ command, |e_y|≤0.3 m tại completion, không collision |
| T3 | Ego10; STOP point cách50 m dọc route | Trong≤20 s, dừng±1 m, speed≤0.5 m/s |
| T4 | LEFT(15,6); front phanh6 m/s² từ trigger TTC<2, khoảng t0+2.5; fixture deviation bên dưới | Không collision; safety request giảm tốc>3 m/s² và override, tick đầu≤0.5 s sau trigger; min TTC>0.5 s |
| T5 | ChuỗiT2 đúng10 lần, cùng seed/config, fresh actor/PID | Chỉ max chênh ngang giữa repeats, không pass/fail |
| T6a | 5→10, a_max2/a_dec3, stable3 s | Cửa sổ5 s từ t_cmd+4.5 s |
| T6b | 10→5, cùng limits/stability | Cửa sổ5 s từ tick đầu≥t_cmd+11/3 s: 3.70 s |
| T6c | 10→15, cùng limits/stability | Cửa sổ5 s từ t_cmd+4.5 s |

- **T2 completion bổ sung:** tâm đúng target corridor, |e_y|≤0.3 trong10 tick liên tiếp; timestamp là tick thứ10, cả xác nhận phải≤6 s. Tiếp tục giữ làn đến hết6 s, không dừng log ngay khi complete. Gap_min kiểm tra cả front/rear tại command bằng bbox; không lấy center distance.
- **T3 bổ sung:** STOP tham chiếu **tâm bounding box ego**. Điểm50 m là tọa độ thế giới theo tiến dọc route từ tâm tại t0. Xác nhận speed≤0.5 và sai số dọc≤1.0 trong20 tick liên tiếp; tick cuối≤20 s. Giữ trong tolerance đến hết20 s, không pass do chạm ngưỡng thoáng qua.
- **T5:** `max_{i<j,t}|e_y_i(t)-e_y_j(t)|`, cùng target-lane-center convention, căn command ticks0..120. Không DTW/interpolate/realign riêng để che lệch. Thiếu full6 s → repeatability không tính được; không chấm fail/pass.
- **T6:** `first_tick=ceil((|delta_v|/a_lim+2)/0.05)`, đúng100 ticks `[first_tick,first_tick+100)`. Sai số speed≤`max(1.0,0.1*v_target)` trừ tối đa5 ticks; max|a_long|≤1.1*a_lim ở **mọi tick**, không ngoại lệ gia tốc. Limits T6a/c2.2, T6b3.3 m/s². Gia tốc = chênh vận tốc chiếu tangent giữa hai snapshots /0.05; lấy preceding snapshot cho tick đầu, không brake/throttle hoặc gia tốc gồm gravity. Không làm tròn metric trước chấm.

### T4: biến thể fixture phải duyệt tường minh

Với ego/front cùng10 m/s, gap25 m giữ nguyên trước trigger thì closing=0 và TTC=∞: không thể tự trigger phanh. Không được che mâu thuẫn bằng trigger giả.

**Đề xuất deviation chỉ cho fixture T4:** ego10, front script **5 m/s**, front gap **22.5 m tại t0**, rear10/gap25; command LEFT(15,6), executor/safety vẫn giống T2. Open-loop không can thiệp: TTC=(22.5−5t)/5, bằng2 tại2.5 s và <2 ở tick kế tiếp. Đây là dự đoán dựng cảnh, không phải số đo thật.

Trigger thật là tick đầu TTC bbox<2 khi maneuver active; từ đó front script `max(0,5−6*(t−t_trigger))`. Ghi t_trigger thật, fixture hợp lệ nếu trong **[2.0,3.0] s**. Safety có thể giảm ego sớm làm TTC không chạm2, hoặc maneuver kết thúc sớm: khi đó **fixture_invalid**, không pass và không điều chỉnh safety để ép trigger. Parameters không đổi sau duyệt; cần fixture khác phải trình diagnostic và xin duyệt revision.

**Duyệt plan phải xác nhận riêng deviation 5 m/s/22.5 m này.** Nếu phải giữ initial conditions T2, cần Dũng chỉ định scripted preconditioning khác trước chạy; không có CÓ đầy đủ khi T4 invalid/chưa chạy.

### Giả định team tự đặt

Không viết lời cam kết/đặt chữ ký thay Nguyễn Trung Dũng. Những mục chưa duyệt chỉ được khóa khi người yêu cầu chấp thuận:

| ID | Giá trị đề xuất | Phân biệt với brief/quyết định |
|---|---|---|
| A1 | T1 10→12, leader10; gap20 tại LANE_KEEP | Chuỗi A đã duyệt; mốc gap/tolerance chờ duyệt |
| A2 | Stable<0.2:60 ticks; đạt12:20 ticks; prep timeout20 s/phase | Operational definitions bổ sung |
| A3 | T1 có override/v<11; tracking5 s cuối≤1 mọi tick | Tiêu chí(c) bổ sung theo yêu cầu review |
| A4 | T2 xác nhận10 ticks; T3 tâm bbox/20 ticks/hold | Completion/STOP conventions bổ sung |
| A5 | T4 front5/gap22.5, trigger2..3 s | Deviation initial fixture T2, cần duyệt rõ |
| A6 | T5 cùng grid0..120, không truncate/interpolate | Quy tắc tính repeatability |
| A7 | T1/2/3/4/T6a/b/c mỗi1 official measured episode, T5 thêm10: tổng17 | T2 qualification không thay một repeat T5 |
| A8 | Seed55000000; blueprint `vehicle.tesla.model3` choego/NPC; ClearNoon; không traffic khác | Blueprint thiếu→blocker, không tự thay |
| A9 | “Thẳng”: yaw lệch≤5° so tangent đầu, length≥200 m; cho đi thẳng qua junction; lane change ngoài junction | Route policy cần duyệt, xem map evidence |
| A10 | Đèn liên quan frozen Green, không ignore-lights | Shared red/pedestrian safety vẫn có |
| A11 | Safety normal following gap5 + headway1.5 s; emergency TTC<2 hoặc gap≤5; request6/brake1, giữ steer | Shared code/options, không tuning riêng T4 |
| A12 | LC path: same-lane0.1 m, transition40 m, other-lane120 m, step2, check=True,1 lane | Stock helper; không custom spline/tracker |
| A13 | SET_SPEED defaults2/3; ramp target mỗi0.05; STOP envelope decel3 | Ramp target không chứng minh limits gia tốc thật |
| A14 | Budget tính cả wrapper/routes/commands/safety và geometry agent dùng | Không báo diff stock=0 để né500 dòng |

### Map proposal, chưa phải spawn đã dùng

Read-only query tìm candidate ego waypoint **road4/section0/lane3/s80.0**, x/y/z≈`(-74.0690,108.5320,0.2161)`, yaw≈`269.8438°`; left waypoint **road4/section0/lane2/s80.0**, `(-77.568947,108.541542,0.216136)`, yaw269.843750°. Lane marking cho Left. Corridor đọc được≈283.60 m với yaw tolerance5°, roads `2,3,4,742,874`, junctions `730,861`; junction đầu≈82 m.

Chưa chứng minh target route/spawn clear. Query grid20 m cấm mọi junction và yêu cầu làn trái liên tục chỉ tìm đoạn dài nhất≈134.39 m; không phải chứng minh toán học Town03 không có đoạn200 m. **A9 cho qua junction cần duyệt**, không gọi134 m là200 m hoặc tự đổi town.

Task1 xuất waypoint pairs đầy đủ, turns/exits và exact transforms thành `fixtures.json`, xin duyệt hash **trước live**. Spawn z=waypoint.z+0.5, pitch/roll theo waypoint; gap actor dùng projected bbox extents. Báo requested/actual spawn và pose tại command marker riêng; không gắn candidate tọa độ thành “đã dùng”. Không pin được route/maneuver hợp lệ→map_fixture_blocker.

### Câu hỏi cơ chế: kết quả audit để xác minh bằng tests

- **RIGHT vs LEFT: CÓ cùng path-generation mechanism**: `BasicAgent.lane_change`→`_generate_lane_change_path(direction)`; khác side waypoint/RoadOption. Wrapper dùng helper với check=True vì stock lane_change truyền False.
- **TURN_LEFT/RIGHT vs LC: KHÔNG cùng route-generation/selection**: turn dùng `GlobalRoutePlanner.trace_route/_turn_decision`, RoadOption.LEFT/RIGHT và exit đã chỉ định; LC dùng helper waypoint làn kề.
- **CÓ chung tracking** sau route: `set_global_plan`→`LocalPlanner.run_step`→`VehiclePIDController.run_step`. Không đánh đồng chung PID với chung mọi cơ chế.
- API TURN/RIGHT phải có unit delegation/validation tests; live TURN/RIGHT không thuộc6 phép bắt buộc, không tự thêm tiêu chí quyết định.

## File structure và interfaces

Prefix modules dưới đây: `experiments/m55_executor/`; tests dưới `tests/`. Không import legacy pipeline. Offline modules không import carla ở top level. Tests import factories bằng `from m55_fakes import ...` khi pytest thêm thư mục tests vào import path; không dùng fixture/plugin tự khám phá.

| File tạo mới | Trách nhiệm |
|---|---|
| `__init__.py`, `protocol.py` | Package/schema, stability, immutable approval/config locks |
| `audit.py`, `code_budget.py` | Source/A–B–C/callgraph, read-only fixture discovery, executable diff evidence |
| `geometry.py`, `metrics.py` | Bbox/projection/TTC; offline acceptance/repeatability |
| `commands.py`, `routes.py` | Command state/envelopes; delegate stock LC/turn routes |
| `executor.py`, `safety.py` | Thin BehaviorAgent subclass; invariant governor |
| `runner.py`, `report.py` | Script actors/tick/raw lifecycle; final evidence/report |
| `scripts/run_m55_executor.py` | CLI audit/freeze/preflight/run/analyze |
| `configs/m55_executor_protocol.json` | Toàn bộ values đã duyệt; không rewrite để pass |
| `tests/m55_fakes.py` | Factories import tường minh, không auto-discovery |
| `tests/test_m55_{protocol,audit,metrics,executor,safety,runner,report}.py` | Unit tests theo responsibility |
| `tests/test_m55_carla.py` | Opt-in live tests, mặc định không tick server |

Evidence ở `outputs/m55_executor/v1/`: approval/lock/fixtures, audit/source inventory, raw per attempt, budget, report. Không stage data lớn vào code commit.

**Shared type:** `Json = dict[str,Any]`, import Any/Sequence/Path; JSON phải validate schema, units và finite values. Invalid command/trace raise ValueError; command invalid không mutate state. Metadata/hash khác không được gộp.

- `load_protocol(path: Path)->Json`, `validate_protocol(protocol: Json)->None`, `protocol_hash(protocol: Json)->str` dùng canonical sorted compact JSON.
- `write_lock(protocol: Json,fixtures: Json,approval_text: str,out_dir: Path)->Json`, `verify_lock(protocol: Json,fixtures: Json,lock: Json)->None`; nonempty approval text và matching hashes bắt buộc.
- `source_inventory(agent_root: Path)->Json`, `discover_fixtures(client: carla.Client,protocol: Json)->Json`, `agent_budget(baseline: Path,final: Path)->Json`.
- `project_bbox(vertices: Sequence[tuple[float,float,float]],tangent_xy: tuple[float,float])->tuple[float,float]`.
- `gap_ttc(ego_vertices: Sequence[tuple[float,float,float]],other_vertices: Sequence[tuple[float,float,float]],ego_velocity_xy: tuple[float,float],other_velocity_xy: tuple[float,float],tangent_xy: tuple[float,float])->tuple[float,float,float|None]`: signed gap/closing/TTC; None=∞ khi closing≤0, overlap gap giữ≤0.
- `evaluate_trial(trial_id: str,trace: Json,protocol: Json)->Json`, `repeatability(traces: Sequence[Json],protocol: Json)->Json`.
- `CommandState` dataclass trong commands: `command_id:int`, `v_target_mps:float`, `a_max:float`, `a_dec:float`, `v_reference_mps:float`, `motion:str`, `motion_started_tick:int|None`, `deadline_tick:int|None`, `stop_xy:tuple[float,float]|None`, `tolerance_m:float`, `target_lane:tuple[int,int,int]|None`. Defaults speed10/limits2,3/motionLANE_KEEP. SET_SPEED giữ motion/timer; motion command giữ speedstate.
- `accept_command(state: CommandState,command: str,issued_tick: int,**kwargs: Any)->CommandState`, `speed_reference(state: CommandState,dt: float,remaining_stop_m: float|None,safety_speed_cap_mps: float)->float`: ramp target; STOP target=min(v_target,sqrt(2*3*max(remaining_stop_m,0))). Safety cap không đổi command state.
- `lane_change_plan(agent: BehaviorAgent,direction: str,protocol: Json)->list[tuple[carla.Waypoint,RoadOption]]`, `turn_plan(agent: BehaviorAgent,direction: str,intersection_id: int,exit_lane: tuple[int,int,int],fixtures: Json)->list[tuple[carla.Waypoint,RoadOption]]`.
- `BehaviorExecutor(vehicle: carla.Vehicle,protocol: Json,fixtures: Json)`; `set_command(command: str,**kwargs: Any)->None`, `run_step(debug: bool=False)->carla.VehicleControl`, `telemetry()->Json`.
- `SafetyGovernor(protocol: Json)`; `decide(sample: Json,command_speed_mps: float)->Json`, `apply(decision: Json,nominal: carla.VehicleControl)->tuple[carla.VehicleControl,Json]`. Decision schema: `speed_cap_mps,override,reason,decel_request_mps2,emergency`; không nhận trial ID.
- `script_velocity(trial_id: str,role: str,tick: int,trigger_tick: int|None,protocol: Json)->float`, `run_trial(client: carla.Client,trial_id: str,rep: int,protocol: Json,fixtures: Json,lock: Json,out_dir: Path)->Path` trả attempt metadata path, kể cả invalid.
- `build_report(run_root: Path,protocol: Json,out_dir: Path)->Json`, `main(argv: Sequence[str]|None=None)->int`: exit0 report valid,2 blocked/input invalid; scientific FAIL không phải crash.

**Public calls đúng brief:**
```python
executor.set_command('LANE_KEEP')
executor.set_command('LANE_CHANGE_LEFT', gap_min=15.0, t_complete=6.0)
executor.set_command('LANE_CHANGE_RIGHT', gap_min=15.0, t_complete=6.0)
executor.set_command('STOP', x=..., y=..., tolerance_m=1.0)
executor.set_command('SET_SPEED', v_target=10.0, a_max=2.0, a_dec=3.0)
executor.set_command('TURN_LEFT', intersection_id=..., exit_lane=...)
executor.set_command('TURN_RIGHT', intersection_id=..., exit_lane=...)
```

exit_lane=(road_id,section_id,lane_id), đúng exit của junction. Lane trái/phải phải Driving, cùng chiều và marking cho phép; front/rear gap≥gap_min tại command. Reject không reset state/deadline. Không tự chọn exit khác hoặc chờ rồi reset timer. Motion route chỉ đổi bởi upper command; safety không sửa route.

**Raw schema v1:**
- `metadata.json`: schema_version=1, trial_id/rep/attempt_id/status/reason/seed, command_marker_frame, protocol/fixtures/approval hashes, source hashes/import paths/versions, executor commit, actual world settings/physics/weather, requested/actual spawn, route points, raw/event hashes.
- `states.csv` row per actor per snapshot: relative_tick/frame/sim_time, actor_key, pose, velocity/speed/a_long, road/section/lane, route_progress/e_y, command_id, command/reference/effective speeds, throttle/brake/steer, safety_override/reason/decel_request, front/rear gaps/TTC.
- `bbox.jsonl`: 8 world vertices keyed frame/actor. `events.jsonl`: frame/relative_tick/event/command_id/source/details; command, marker, route mutation, complete, brake_trigger, override, collision, invalid.
- None TTC=∞ ghi null/empty có units/convention; không NaN. Lưu preceding preparation snapshot cho acceleration boundary. WorldSample của safety chứa cùng actor bbox/velocity, current/planned corridors và red-light state; không dùng trial ID.

## Task 1: Source audit, protocol/fixture lock và budget gate

**Deliverable:** Source/A–B–C inventory + schema/locks, không điều khiển xe.
**Files:** Create `protocol.py`, `audit.py`, `code_budget.py`, `__init__.py`, `configs/m55_executor_protocol.json`, `tests/m55_fakes.py`, `tests/test_m55_protocol.py`, `tests/test_m55_audit.py` (module prefix như trên).
**Interfaces:** Produces protocol/lock/source/fixture/budget APIs; consumes installed sources và map read-only. Fixtures JSON phải có map hash, exact transforms, đầy đủ route waypoint pairs, left/right targets, turns/junction exits.
**Estimate:** 90m; step estimates bên dưới. Approval wait/source mismatch nằm ngoài estimate.

- [ ] **Step 1 (15m): Write failing tests** `test_lock_rejects_mutation`, `test_budget_excludes_comments`. Define factories trong m55_fakes: `protocol_fixture()->Json`, `fixture_fixture()->Json` (synthetic200m), `budget_fixture(tmp_path: Path)->tuple[Path,Path]` (comments-only change +1 executable addition).
```python
def test_lock_rejects_mutation(tmp_path):
    p, f = protocol_fixture(), fixture_fixture()
    lock = write_lock(p, f, 'unit-test approval only', tmp_path)
    verify_lock(p, f, lock)
    p['t1']['v_command_mps'] = 11.0
    with pytest.raises(ValueError, match='protocol'):
        verify_lock(p, f, lock)

def test_budget_excludes_comments(tmp_path):
    before, after = budget_fixture(tmp_path)
    r = agent_budget(before, after)
    assert r['executable_additions'] == 1
    assert r['max_allowed'] == 500
```
- [ ] **Step 2 (5m): Run red** `python -m pytest tests/test_m55_protocol.py tests/test_m55_audit.py -q`; FAIL missing M55 APIs, không lỗi server.
- [ ] **Step 3 (45m): Implement declared APIs.** Validate keys/units/finiteness, require approval, source/fixture hashes; record proposed vs approved status. Source inventory checks actual module paths, upstream tag content and all dependencies. Budget captures unchanged stock sources plus commands/routes/executor/safety and geometry used by agent. Save full `git diff --stat`/`--numstat`; repeat on normalized copies removing comments/blank/AST docstrings, preserving executable strings. Count additions (replacement lines đã là additions), deletions báo riêng. Planner/controller changed→rewrite gate. Không gắn synthetic approval thành live approval.
- [ ] **Step 4 (10m): Run green** same command all PASS. Add tests missing approval, unknown schema, source/fixture mismatch, exact500 allowed/501 rejected, LocalPlanner changed→rewrite, nonfinite config. Offline import không cần CARLA.
- [ ] **Step 5 (5m): Commit** stage đúng Task1 files; `git commit -m "feat(m55): add source audit and immutable protocol gates"`.
- [ ] **Step 6 (10m): Present exact fixture/source inventory for approval**, trước Task6 live; blocked nếu route/source/T4 deviation chưa duyệt. Không lấy approval plan làm approval của một fixture khác.

**Inventory thiết kế ban đầu; audit phải xác minh/ghi line ranges:**

| Quyết định | File:hàm gốc | Hiện tại | A/B/C | Chứng minh/sửa |
|---|---|---|---|---|
| Đèn đỏ | behavior_agent:traffic_light_manager/run_step; basic_agent:_affected_by_traffic_light | red→emergency; có ignore flag | C | Shared check, cùng options; không ignore vì fixture Green |
| Biển STOP | basic_agent:ignore_stop_signs/run_step | có flag nhưng BasicAgent bỏ stop signs; BehaviorAgent không gọi sign manager | A/no-op | Không gọi đây là hỗ trợ stock STOP tại tọa độ |
| Nhường xe sau/tự đổi làn | behavior_agent:_tailgating/collision_and_car_avoid_manager | xe sau nhanh→set_destination làn kề | A | Bypass; counters chứng minh0 autonomous calls |
| Vượt xe trước chậm | behavior_agent:car_following_manager/run_step | thấy follow-speed, không explicit front-overtake branch | B speed | Không bịa flag overtaking; kiểm tra route dependency |
| Profile/speed-limit/junction speed | behavior_agent:_update_information/run_step; behavior_types | ghi đè target, profile cap, turn slowdown | B | **Nút thắt M55:** thay decision run_step, không chỉ set_target_speed |
| Follow/TTC | behavior_agent:car_following_manager | closing bị clamp≥1, profile rules | C replacement | Shared governor dùng bbox TTC thật, cùng parameters |
| Emergency brake | behavior_agent:emergency_stop/run_step | distance/profile; control mới có steer mặc định dù comment nói giữ | C replacement | Giữ steer nominal; physical request/log, cùng policy |
| Pedestrian | behavior_agent:pedestrian_avoid_manager/run_step | close walker→emergency | C | Shared corridor/bbox check |
| Destination/shortest route | basic_agent:set_destination/trace_route; global_route_planner:trace_route | tự chọn route đến đích | B | Chỉ upper command route/exit; không reroute tự trị |
| LC left/right geometry | basic_agent:lane_change/_generate_lane_change_path | chọn side waypoint | B | Delegate helper check=True; admission bbox gaps |
| Random route extension | local_planner:_compute_next_waypoints/run_step | random khi thiếu pinned plan | A | stop_waypoint_creation=True; queue hết→fail closed |
| Follow speed-limit flag | local_planner:follow_speed_limits/run_step | có thể ghi đè target | A | False cố định, test flag/unit conversion |
| Waypoint/PID tracking | local_planner:run_step; controller:VehiclePIDController.run_step | queue purge/PID/saturation/steer rate | C common execution | Bytes/options không đổi; không phải upper decision |

## Task 2: Geometry và offline metric evaluator

**Deliverable:** Chấm đúng semantics trước khi nhìn raw live.
**Files:** Create `geometry.py`, `metrics.py`, `tests/test_m55_metrics.py`; extend m55_fakes.
**Interfaces:** Consumes protocol/raw schema; produces geometry/evaluate/repeatability APIs. Factory `synthetic_trace(trial_id: str,**overrides: Any)->Json` sinh trace biết trước, không ghi làm live data.
**Estimate:** 150m.

- [ ] **Step 1 (35m): Write failing tests** T1 đủ3 điều kiện; T6 mốc/cửa sổ/outliers; bbox xoay/nonclosing; T5 max pairwise.
```python
def test_t1_requires_all_three_conditions():
    p = protocol_fixture()
    assert evaluate_trial('T1', synthetic_trace('T1'), p)['status'] == 'PASS'
    for bad in ({'autonomous_route_calls':1}, {'collision_tick':100},
                {'last5_speed_error':1.01}, {'override_ticks':[]}):
        assert evaluate_trial('T1', synthetic_trace('T1', **bad), p)['status'] == 'FAIL'

def test_t6_window_and_limits():
    p = protocol_fixture()
    r = evaluate_trial('T6b', synthetic_trace('T6b'), p)
    assert (r['first_window_tick'], r['window_tick_count']) == (74,100)
    assert evaluate_trial('T6a', synthetic_trace('T6a', speed_outlier_ticks=5), p)['status'] == 'PASS'
    assert evaluate_trial('T6a', synthetic_trace('T6a', speed_outlier_ticks=6), p)['status'] == 'FAIL'
    assert evaluate_trial('T6a', synthetic_trace('T6a', max_abs_accel=2.2001), p)['status'] == 'FAIL'

def test_repeatability_max_pairwise():
    runs = [synthetic_trace('T2', lateral_offset=i*0.01) for i in range(10)]
    r = repeatability(runs, protocol_fixture())
    assert r['max_lateral_difference_m'] == pytest.approx(0.09)
    assert 'pass' not in r and 'status' not in r
```
Bbox tests use offset center/90° rotation: projected gap20, không center20; equal/receding velocity→TTC None; overlap gap≤0. T4 request3→FAIL,3.01 eligible; response10 ticks PASS/11 FAIL; minTTC0.5 FAIL. T2 complete tick120 PASS/121 FAIL; STOP edges1.0m/0.5m/s inclusive.
- [ ] **Step 2 (5m): Run red** `python -m pytest tests/test_m55_metrics.py -q`; missing metrics/geometry FAIL.
- [ ] **Step 3 (80m): Implement declared APIs.** Route line-segment projection/bbox vertices; signed front/rear gap, closing/TTC, no clamp-to1. Validate sampling/frames/actors/hash/finiteness; invalid trace raises ValueError. T4 min TTC dùng mọi finite forward-target TTC từ command đến6s, không bỏ tick nguy hiểm. Return criterion booleans/reasons và raw metric values, không round trước chấm.
- [ ] **Step 4 (20m): Run green** metric+protocol tests all PASS; thêm missing/duplicate/nonfinite tick, hash mismatch, T1 lane invasion dù0 mutation, early false completion, no-trigger T4,11 T5 runs. T6 acceleration boundary dùng snapshot trước cửa sổ.
- [ ] **Step 5 (10m): Commit** đúng Task2 files; `git commit -m "feat(m55): pin bbox metrics and trial acceptance tests"`.

## Task 3: Command executor — xử lý speed overwrite, giữ planner

**Deliverable:** Public command API + stock tracking, không autonomous policy.
**Files:** Create `commands.py`, `routes.py`, `executor.py`, `tests/test_m55_executor.py`; extend m55_fakes.
**Interfaces:** Consumes CommandState/protocol/fixtures/stock APIs; produces BehaviorExecutor/route APIs. `fake_executor(protocol: Json|None=None)->BehaviorExecutor` dùng scoped fake modules/spies; không thay live imports. Telemetry có speed/route hashes, policy call counts, motion start/deadline.
**Estimate:** 240m; phải custom local tracker/PID→dừng với lý do KHÔNG.

- [ ] **Step 1 (45m): Write failing tests** overwrite, SET_SPEED giữa LC, exhausted route, RIGHT/TURN delegation.
```python
def test_command_speed_not_overwritten():
    ex = fake_executor()
    ex.set_command('SET_SPEED', v_target=10.0, a_max=2.0, a_dec=3.0)
    ex.set_command('LANE_KEEP')
    for _ in range(20): ex.run_step()
    assert ex.telemetry()['command_v_mps'] == 10.0
    assert ex.get_local_planner().speed_history[-1] == pytest.approx(36.0)
    assert ex.telemetry()['stock_policy_calls'] == 0
    assert ex.telemetry()['autonomous_route_calls'] == 0

def test_set_speed_preserves_maneuver():
    ex = fake_executor()
    ex.set_command('LANE_CHANGE_LEFT', gap_min=15.0, t_complete=6.0)
    before = ex.telemetry()
    ex.set_command('SET_SPEED', v_target=12.0, a_max=2.0, a_dec=3.0)
    after = ex.telemetry()
    for key in ('route_hash','motion_started_tick','deadline_tick'):
        assert after[key] == before[key]
```
Fake world roadspeed70/profile50/junction=True vẫn command10→36km/h. LEFT/RIGHT spy cùng helper direction; TURN trace_route/requested exit, không LC helper. Queue hết không random extension. Gap14.99/wrong direction/unknown command reject, state unchanged; gap15 eligible.
- [ ] **Step 2 (5m): Run red** `python -m pytest tests/test_m55_executor.py -q`; missing BehaviorExecutor FAIL.
- [ ] **Step 3 (145m): Implement commands/routes/executor APIs.** Subclass BehaviorAgent normal, thay flow run_step: sample→shared safety decision→command/STOP/ramp capped speed→LocalPlanner.set_speed(mps*3.6)→LocalPlanner.run_step **một lần**→safety apply→telemetry. Trước Task4, inject required safety test double, không live thiếu governor. Không gọi stock `_update_information`, `run_step`, `car_following_manager`, `_tailgating`. Planner/controller giữ nguyên; `follow_speed_limits(False)`. Options cố định: dt.05, sampling_radius2, lateral PID Kp1.95/Ki.05/Kd.2, longitudinal Kp1/Ki.05/Kd0, max_throttle.75/brake.3/steer.8, offset0, base_min_distance3/distance_ratio.5. Không tuning per trial; mọi mutation route phải từ upper command.
- [ ] **Step 4 (35m): Run green** protocol/metrics/executor tests all PASS; LocalPlanner/controller byte hashes unchanged. Budget mục tiêu executable additions: commands70/routes70/executor100/safety90/agent-geometry70=400, reserve100; kiểm tra thực tế, không coi estimate là proof. Không chuyển policy sang runner để né budget.
- [ ] **Step 5 (10m): Commit** đúng Task3 files; `git commit -m "feat(m55): replace autonomous policy with explicit command execution"`.

## Task 4: Invariant safety governor và physical-unit logs

**Deliverable:** Shared C-path, safety cap/emergency, giữ nominal steering.
**Files:** Create `safety.py`, `tests/test_m55_safety.py`; modify executor hook đã định nghĩa ở Task3.
**Interfaces:** Consumes geometry/WorldSample, command speed và nominal control; produces SafetyGovernor.decide/apply. Logs command/reference/effective speeds, decel_request và nominal/final controls, source/options hashes.
**Estimate:** 120m.

- [ ] **Step 1 (25m): Write failing tests** identical world sample→identical decision cho mọi trial metadata, emergency giữ steer, target-lane/front/rear/pedestrian/red hazards. Factories `safety_sample(gap: float,closing: float,**overrides: Any)->Json`, `fake_control(**values: float)->carla.VehicleControl(fake)`.
```python
def test_emergency_preserves_steering():
    g = SafetyGovernor(protocol_fixture())
    d = g.decide(safety_sample(gap=9.0, closing=5.0), 12.0)
    ctl, log = g.apply(d, fake_control(throttle=.4, brake=0, steer=.25))
    assert log['override'] is True
    assert log['decel_request_mps2'] == 6.0
    assert ctl.throttle == 0 and ctl.brake == 1
    assert ctl.steer == .25
```
Normal front g20/v_lead10/ego12→speed cap10 theo formula dưới, stored command vẫn12; log normal decel budget≤3, emergency request6>3. Rear outside corridor không tự đổi route.
- [ ] **Step 2 (5m): Run red** `python -m pytest tests/test_m55_safety.py -q`; missing governor FAIL.
- [ ] **Step 3 (60m): Implement declared governor APIs.** Normal follow cap cho forward lead cùng current lane/đã overlap: `min(command_v,v_lead+max(0,(gap-(5+1.5*v_lead))/1.5))`, đưa vào target ramp với normal decel3 trước tracking. Emergency cho current/planned path corridor: TTC<2 hoặc actual gap≤5, red/pedestrian risk→request6, throttle0/brake1, giữ nominal steer. Pedestrian corridor intersection là hazard, không dùng trial label. Đánh giá đủ forward/rear planned-lane risk, không chỉ current lane. Cùng configuration mọi run. Request6 là desired physical deceleration, brake1 dimensionless; lưu actual acceleration riêng, không gọi brake1 là measured6. Safety không set_global_plan.
- [ ] **Step 4 (20m): Run green** safety/executor tests all PASS; bổ sung TTC None/receding, rotating bbox, rear closing, same hashes/options, cap không mutate command, no second planner.run_step. Capture code budget lại; thiếu C-path proof→block live.
- [ ] **Step 5 (10m): Commit** đúng Task4 files; `git commit -m "feat(m55): add invariant safety overrides with physical-unit logs"`.

## Task 5: Script actors, single tick owner và raw lifecycle

**Deliverable:** Fake-world timing/NPC independence tests và opt-in runtime evidence.
**Files:** Create `runner.py`, `tests/test_m55_runner.py`, `tests/test_m55_carla.py`; extend m55_fakes.
**Interfaces:** Consumes executor/lock/fixtures; produces run_trial/script_velocity. `fake_world()->Json` cung cấp client/world/vehicles spies, frame increments và queued sensor callbacks; không connect server.
**Estimate:** 150m.

- [ ] **Step 1 (30m): Write failing tests** no TM/autopilot, marker before first control, T1 stable/gap gates, late last-frame collision.
```python
def test_script_velocity_schedule():
    p = protocol_fixture()
    assert script_velocity('T1','lead',0,None,p) == 10.0
    assert script_velocity('T1','lead',300,None,p) == 10.0
    assert script_velocity('T4','front',50,50,p) == 5.0
    assert script_velocity('T4','front',60,50,p) == pytest.approx(2.0)
    assert script_velocity('T4','front',100,50,p) == 0.0
```
Fake raises on get_trafficmanager/set_autopilot; khác ego state không đổi NPC schedule. Stable12 đúng19 ticks không issue LANE_KEEP,20 có; exact.2 resets counter. Marker frame100→first control transition101→relative_tick1; gap kiểm ở marker LANE_KEEP. Sensor collision frame400 đến sau last row vẫn ghi/chấm. Second tick owner/frame gap bị reject.
- [ ] **Step 2 (5m): Run red** `python -m pytest tests/test_m55_runner.py -q`; missing runner FAIL.
- [ ] **Step 3 (80m): Implement runner APIs.** Seed Python/NumPy55000000; verify actual sync/.05/substeps/map/physics. Actor physics enabled; NPC enable_constant_velocity hoặc set_target_velocity mỗi tick theo pinned route, không teleport/disable collision khi đo. T4 time-based6m/s² sau trigger. Check actual NPC speed T1/T2 trong±.2 mọi tick; T4 actual decel6±.6 đến near-zero (speed≤.5), otherwise fixture_invalid. Ego initial velocity chỉ set trước preparation; stable3 s dùng executor, không constant velocity ego.

Tick order: snapshot n→command/trigger từ n→NPC/executor control→apply→một world.tick→snapshot n+1→record. Event dùng frame đúng; trigger ở snapshot n ảnh hưởng transition tiếp theo, latency dùng timestamps requests. Collision/lane-invasion sensors; bounded callback drain, thiếu delivery confirmation→invalid không phải zero collision. Raw bao gồm preparation; flush/hash rồi complete, immutable attempt IDs. Finally destroy owned actors/sensors, restore settings; reload_world không phải server restart.
- [ ] **Step 4 (25m): Run green** offline M55 tests all PASS; `python -m pytest tests/test_m55_carla.py -q` **SKIP** nếu không M55_LIVE=1/approved lock. Test timeout setup_invalid, requested/actual settings mismatch, speed mismatch, cleanup exception, late collision; mặc định tests không tick live.
- [ ] **Step 5 (10m): Commit** đúng Task5 files; `git commit -m "feat(m55): log command-aligned trials with nonreactive scripted traffic"`.

## Task 6: CLI/report, measured matrix và conclusion audit

**Deliverable:** M55 report với dữ liệu thật hoặc blocker cụ thể.
**Files:** Create `report.py`, `scripts/run_m55_executor.py`, `tests/test_m55_report.py`; evidence dưới outputs/m55_executor/v1.
**Interfaces:** Consumes approved raw/locks/budget; produces build_report/main. CLI signatures dưới đây là yêu cầu implementation, chưa có CLI thật.
**Estimate:** 210m; live wall-clock chưa biết, dự phòng riêng1h.

- [ ] **Step 1 (20m): Write failing tests** full qualifying evidence, budget/rewrite gate, invalid≠technical NO, mixed revisions. Factory `report_fixture(path: Path,**overrides: Any)->Path` tạo manifests **synthetic** cho tests.
```python
def test_yes_requires_full_evidence(tmp_path):
    root = report_fixture(tmp_path, all_pass=True, code_lines=500, repeat_count=10)
    assert build_report(root, protocol_fixture(), tmp_path/'report')['conclusion'] == 'CÓ'

def test_blocked_is_not_technical_no(tmp_path):
    root = report_fixture(tmp_path, missing_trial='T4', reason='fixture_invalid')
    r = build_report(root, protocol_fixture(), tmp_path/'report')
    assert r['conclusion'] is None and r['status'] == 'BLOCKED'
```
Valid T4 FAIL→KHÔNG; invalid fixture→BLOCKED.501 additions/planner rewrite→KHÔNG with reason. Missing T5 chưa đủ submission; different safety/config/source hash hoặc missing raw hash reject.
- [ ] **Step 2 (5m): Run red** `python -m pytest tests/test_m55_report.py -q`; missing report FAIL.
- [ ] **Step 3 (50m): Implement CLI/report APIs.** Subcommands audit/freeze/preflight/run/analyze. Freeze requires human approval file + fixtures file, never autoapprove. Run rejects pending protocol/T4/fixture/source gates. Preflight read-only by default; reload/apply settings requires explicit world ownership permission/`--own-world`, vì server có thể đang được client khác dùng. Report all criteria/actual metrics, source commit null with bundle reason, executor/workspace commits riêng; no expected values as data.
- [ ] **Step 4 (15m): Run green** `python -m pytest tests/test_m55_protocol.py tests/test_m55_audit.py tests/test_m55_metrics.py tests/test_m55_executor.py tests/test_m55_safety.py tests/test_m55_runner.py tests/test_m55_report.py -q` all PASS; CLI --help có5 subcommands, run thiếu lock exit2 không spawn/tick.
- [ ] **Step 5 (10m): Commit** đúng Task6 files; `git commit -m "feat(m55): gate live matrix and publish evidence-based feasibility reports"`.
- [ ] **Step 6 (20m): Audit/freeze/preflight**, chưa đo. Commands:
```powershell
python scripts/run_m55_executor.py audit --protocol configs/m55_executor_protocol.json --out outputs/m55_executor/v1
python scripts/run_m55_executor.py freeze --protocol configs/m55_executor_protocol.json --fixtures outputs/m55_executor/v1/fixtures.json --approval outputs/m55_executor/v1/approval.txt --out outputs/m55_executor/v1
python scripts/run_m55_executor.py preflight --lock outputs/m55_executor/v1/lock.json
```
Expected source/map/geometry/version/C-path checks PASS, actual human approval text captured. Route/source/T4/ownership unresolved→blocker, không đổi parameters. Approval.txt không được dùng unit-test string hoặc chữ ký generated.
- [ ] **Step 7 (50m): Execute frozen matrix** sau khi được độc quyền world:
```powershell
python scripts/run_m55_executor.py run --lock outputs/m55_executor/v1/lock.json --own-world --trials T1,T2,T3,T4,T5,T6a,T6b,T6c
```
Đúng17 episodes: T5 thêm10, không lấy T2 thay repeat. First measured attempt là official; FAIL không rerun đến pass. Setup_invalid được retry tối đa1 lần khi transient cause ghi rõ và parameters không đổi; giữ cả attempts; invalid tiếp→stop. T4 không trigger hợp lệ→fixture_invalid, trình diagnostic để xin revision, không tuning safety. Không tự chạy TURN live ngoài budget.
- [ ] **Step 8 (20m): Analyze raw/budget** `python scripts/run_m55_executor.py analyze --lock outputs/m55_executor/v1/lock.json --out outputs/m55_executor/v1/report`; verify inventory/hashes, actual metrics, T5 không label. Save full/normalized agent diff stat/numstat, LocalPlanner/controller byte hashes unchanged. Exit0 không đồng nghĩa CÓ.
- [ ] **Step 9 (20m): Audit submission checklist**, đọc mọi evidence trước kết luận. CÓ chỉ khi1/2/3/4/6 PASS, T5 data đủ, C invariant/planner/budget proof đủ. Valid required trial FAIL hoặc phải rewrite/>500→KHÔNG với lý do. Missing live/invalid fixture→`CHƯA KẾT LUẬN — BLOCKED: <reason>` và thông báo dependency; không giả KHÔNG vì server unavailable. Đổi parameter sau results→approval revision +full matrix mới, không late tuning.

## Ước lượng và nhận định khả thi

| Deliverable | Person-hours |
|---|---:|
| Task1 audit/locks/fixture proposal | 1.5 |
| Task2 geometry/offline evaluator | 2.5 |
| Task3 command wrapper/routes | 4.0 |
| Task4 shared safety | 2.0 |
| Task5 scripts/runner/raw | 2.5 |
| Task6 CLI/live/report/audit | 3.5 |
| Self-review/contingency | 1.0 |
| **Tổng** | **17.0 h** |

Ngày1 khoảng8h: audit/evaluator/wrapper; ngày2 khoảng8h: safety/runner/live/report; thêm1h review/dự phòng. Approval wait hoặc external blockers ngoài estimate. Matrix đo≈**134.67 simulated seconds**, chưa tính preparation/reset/sensor drains; không quy simulated time thành wall-clock cam kết. Báo timing thật.

**Nhận định của người lập plan, không phải lời Dũng:** stock global-plan/speed inputs cho spike cơ sở để thử, chưa đủ bằng chứng CÓ. Rủi ro: helper LC tạo waypoint jump, stock PID/STOP có thể không đạt±1m hoặc acceleration limits, safety làm T4 không trigger, route qua junction cần approval, budget500 có thể không đủ. KHÔNG là kết quả hợp lệ; không kéo spike thành dự án viết planner/controller khác để cố đạt.

## Submission/evidence checklist

- [ ] Một dòng CÓ/KHÔNG có evidence; hoặc blocker rõ khi không thể kết luận.
- [ ] Bảng quyết định/file:hàm+line range/hiện tại/A–B–C/ghi chú; bao gồm dependency decisions, không bịa stock toggle.
- [ ] T1 actual stable/gap marker,15s coverage, autonomous calls/mutations/invasions, collisions, override/speed/gap/5s cuối.
- [ ] T2 front/rear actual gap/speed, command/complete frames, elapsed/error/collision.
- [ ] T3 STOP point/reference, signed error/speed/confirmation/hold/collision.
- [ ] T4 registered deviation, actual trigger/leader decel, first safety request>3/flag/latency, min TTC/collision/fixture validity.
- [ ] T5 đúng10 raw IDs/hashes/common grid, numeric max lệch ngang và worst pair/tick, không label.
- [ ] T6 mỗi start/target/stability/window ticks/outlier count/max error/max|a|/limits.
- [ ] Steps sửa file/hàm + executable code budget/diff evidence, hoặc lý do KHÔNG/rewrite/budget.
- [ ] C-path/source/options hashes giống nhau mọi run; LocalPlanner/controller bytes unchanged.
- [ ] BehaviorAgent SHA local, source git commit/null reason, import path/version, workspace/executor commit riêng.
- [ ] Tất cả actor road/section/lane,x/y/z/yaw requested/actual spawn và command marker, routes/junction exits/map hash; proposal không gắn nhãn đã dùng.
- [ ] RIGHT/LEFT và TURN/LC answers kèm code/callgraph, tách generation khỏi common tracking.
- [ ] Raw/events/bboxes/metadata/lock/approval/invalid attempts và artifact hashes đủ inventory, không thiếu tick.

## Self-review và handoff

Coverage: source/classification→Task1; six metrics/thresholds→Task2; signatures/overwrite/route gate→Task3; shared safety/T1 follow/T4 override→Task4; script/timing/provenance→Task5; matrix/budget/report/blockers→Task6. Review Focus năm mục đã có tests; interfaces/schema được định nghĩa trước consumers. Không viết product code hoặc chạy live trong planning turn.

Cần duyệt ngưỡng T1 và assumptions, **đặc biệt T4 deviation và A9 route qua junction**; sau đó Task1 xuất exact fixture để duyệt lock trước live. Chưa chọn execution method. Đề xuất **Native**: tôi thực hiện6 tasks, một fresh reviewer kiểm whole branch trước live; tiết kiệm context cho deadline1–2 ngày và interfaces phụ thuộc nhau. **Subagent-driven**: implementer/reviewer mới mỗi task, thorough hơn nhưng tốn context. Chờ duyệt plan và chọn method trước implementation; chưa dispatch subagents.
