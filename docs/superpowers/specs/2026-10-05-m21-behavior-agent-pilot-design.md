# M21 — BehaviorAgent pilot và mode phân tích độc lập

**Trạng thái:** Thiết kế đề xuất để duyệt; chưa cho phép triển khai theo tài liệu này. Thống kê suy luận của M21 vẫn đang chờ Nguyễn Trung Dũng chốt. Phạm vi trước mắt là hạ tầng, phép tính kiểm thử được và pilot; không phải kết luận toàn bài.

## 1. Ý định và quyết định đã phê duyệt

M21 đo liệu NPC `npc_conflict` có thay đổi chuyển động khi ego đổi intent, dùng để chọn NPC cho thí nghiệm chính. Không được thay controller ego hoặc chỉnh BehaviorAgent để ép phản ứng. Đây là một phần việc độc lập với M55; không dùng executor hoặc lớp an toàn đang nghiên cứu trong M55 để điều khiển ego/NPC ở M21.

Người yêu cầu đã phê duyệt:

- Giữ nguyên controller ego cũ và chế độ phân tích cũ; được bổ sung mode M21 trong pipeline hiện có.
- Regression check: sau thay đổi, phân tích cũ trên đúng 720 run `tm_default` hiện có phải cho output giống hệt trước sửa.
- Manifest phải ghi sync mode, seed, CARLA version, GPU, session id; lưu quỹ đạo thô từng tick.
- Được code/test phép đo trên pilot; chưa tính hoặc công bố ĐẠT/KHÔNG ĐẠT trước khi chốt thống kê.
- Seed theo `(cảnh, rep, phiên)`, dùng chung cho mọi intent trong cảnh; bỏ `cặp` khỏi tuple seed. Ghép cặp theo rep, không chạy lại từng intent chỉ vì intent đó xuất hiện trong cặp khác.

## 2. Bằng chứng từ workspace hiện tại

Rà soát ngày 2026-10-05, chưa sửa mã sản phẩm hoặc chạy CARLA trong lượt rà soát này:

| Tài nguyên | Đường dẫn / bằng chứng |
|---|---|
| Pipeline cũ | `experiments/ego_intent_response/` |
| CLI cũ | `scripts/run_ego_intent_response.py` |
| Catalog | `configs/ego_intent_response_town03_scenes.yaml`: 24 cảnh, 6 loại × 4 cảnh, 3 intent/cảnh; mỗi cảnh chỉ có NPC `npc_conflict` |
| Dữ liệu TM cũ | `outputs/ego_intent_response/runs/tm_default/`: 720 `states.csv`; kiểm tra metadata `status=complete` và SHA-256 raw: 720/720 khớp, 0 lỗi. Config/catalog/coverage vẫn phải xác thực khi capture regression baseline |
| Audit TM cũ | `outputs/ego_intent_response/audits/tm_default/`: 12 `states.csv`, không phải mẫu thay thế cho toàn bộ noise calibration M21 |
| Implementation hash cũ | `d3e3b9dea51124558cf1216a2a6f121a7c1bfcf2802f3bcb8168736830aa5b34` |
| SHA-256 controller ego | `6fd128650572e3a3dbed5fe466cffdd9e59a5809cd7ca920f4e8c9c3ebfa4ad3` |
| Mã BehaviorAgent | `E:/Carla/PythonAPI/carla/agents/navigation/behavior_agent.py` |
| SHA-256 BehaviorAgent đọc được | `2b8f046e4e3efa07d6d21b5ea4420a43a232ce297c3932434477563eb04b143f` |
| Local planner | Đã xác nhận tên lớp `LocalPlanner` trong `agents/navigation/local_planner.py` |

Các hash trên định danh file hiện có, không tự chứng minh phiên bản nguồn. Khi thực thi phải xác nhận client/server 0.9.16 và đường dẫn module `agents` thực sự import, ghi hash toàn bộ dependency agent dùng trong manifest. Không có bằng chứng rằng CARLA server hiện đang chạy hoặc rằng GPU đã sẵn sàng.

Pipeline cũ dùng RMSE/B/W, bootstrap CI 95%, permutation và BH/FDR; không dùng tiêu chí M21. `runner.implementation_hash()` chỉ băm `runner.py`, `controllers.py`, `scenario_catalog.py`; effective config hash chứa implementation hash này. Vì vậy sửa một trong ba file đó sẽ làm raw cũ không còn khớp, dù controller vẫn có vẻ hoạt động giống nhau.

Workspace có thay đổi/untracked của người dùng, bao gồm pipeline cũ. Không reset, xóa, định dạng lại hoặc gom các file đó vào commit của phần việc mới. Markdown bị `.gitignore` bỏ qua bởi `*.md`; chỉ force-add tài liệu chính xác cần lưu, không sửa `.gitignore` để thực hiện phần việc này.

## 3. Kiến trúc đề xuất

### 3.1 Hai mode trong cùng CLI

Thêm `--mode {legacy,m21}`, mặc định `legacy`, trong `scripts/run_ego_intent_response.py`. Không đổi thân các hàm phân tích legacy, mặc định cũ, thứ tự output hoặc API cũ. Chỉ import các module M21 sau khi chọn mode M21; lựa chọn legacy không được yêu cầu cài thêm package hoặc import CARLA agents.

Tách mã mới dưới `experiments/ego_intent_response/m21/`. Tái dùng `SceneSpec`, `IntentSpec`, `RouteSpeedController`, `speed_from_schedule`, fixture setup/validation/cleanup, state serialization và loader/hash checks cũ qua adapter, không sửa chúng. Vòng tick M21 phải dùng đúng lựa chọn prefix/intent controller, `route_switch_s`, lịch tốc độ và thứ tự apply-control/tick/snapshot của runner cũ. Không viết controller ego khác, kể cả controller có cùng tên thông số.

M21 có implementation/config hash riêng, bao gồm module M21, dependency legacy tái dùng, CLI, CARLA agent sources và cấu hình. Dữ liệu ở `outputs/m21_behavior_agent_pilot/`, không ghi vào thư mục raw/report legacy. Resume kiểm tra schema, session, config/catalog/code hashes và hash raw; không ghi đè cell đã complete của cấu hình khác.

**Ranh giới file dự kiến:**

| File | Trách nhiệm duy nhất |
|---|---|
| `m21/protocol.py` | Danh sách cặp intent, định danh cell và seed, kiểm tra cấu hình/gate pilot |
| `m21/agent.py` | Import/định danh BehaviorAgent đúng nguồn, gắn NPC theo route và mặc định normal |
| `m21/provenance.py` | Session/manifest, GPU và software/source hashes, serialization và kiểm tra integrity |
| `m21/runner.py` | Adapter fixture legacy, vòng tick dùng controller ego cũ, marker và raw/collision events |
| `m21/measurements.py` | Phép đo mô tả và primitives trên quỹ đạo đã căn tick; không quyết định đạt/rớt |
| `m21/report.py` | CSV/pilot timing/data-quality report, không gọi legacy decision writer |
| `m21/cli.py` | Điều phối preflight, pilot, analyze-only, resume; chặn full/decision khi protocol pending |
| `tests/test_m21_*.py` | Tests từng trách nhiệm, regression legacy và integration tùy chọn |

Đường dẫn trong bảng được tính từ `experiments/ego_intent_response/`, trừ đường dẫn `tests/`. Chữ ký cụ thể và vòng TDD sẽ được khóa trong implementation plan sau khi duyệt spec này.

### 3.2 NPC BehaviorAgent

Gắn `BehaviorAgent(vehicle, behavior='normal')` với thông số mặc định, không sửa mã agent, không gọi ignore-lights, không chỉnh tốc độ/PID/safety/tailgating. NPC được `run_step()` và `apply_control()` từng tick, không bật autopilot cho `npc_conflict`.

Đích cuối lấy từ route NPC trong catalog. Dùng cơ chế route của BasicAgent và `set_global_plan` để giữ đúng route catalog, thay vì chỉ chọn đường ngắn nhất đến đích. Preflight kiểm tra trace qua các điểm catalog không đổi làn/nhánh ngoài route đã pin; không khớp thì báo lỗi, không chọn route thay thế im lặng. Lưu global plan thực tế với road/lane/junction IDs và RoadOption để kiểm tra route fidelity.

Giữ chính sách môi trường cũ: Town03, ClearNoon, đèn frozen theo `SceneSpec.traffic_light_state` (catalog hiện là Green). Agent vẫn tuân thủ đèn, không vô hiệu hóa traffic-light manager. Đây không phải thí nghiệm mới về phản ứng với đèn đỏ. Setup quay bánh/hiệu chỉnh vận tốc ban đầu không phải thời gian đo và giữ như pipeline cũ; trong thời gian đo BehaviorAgent hoàn toàn điều khiển NPC.

### 3.3 Seed và phiên

Cấu hình đề xuất cho M21: `base_seed=21000000`, `session_index` là số nguyên không âm đã đăng ký trong manifest, `scene_index` là chỉ số gốc trong catalog, `rep` từ 1 đến 10.

```text
seed = 21000000 + session_index * 1000000 + scene_index * 1000 + rep
```

Kiểm tra miền giá trị và trùng seed khi lập lịch; không dùng thứ tự lọc cảnh để đánh lại chỉ số. Ba intent của cùng scene/rep/session phải dùng chung seed. Các tuple scene/rep/session khác nhau phải khác seed; retry một cell không phải rep mới, ghi attempt riêng và không đưa hai attempt vào thống kê. Seed Python `random`, NumPy và TM nếu adapter fixture còn dùng TM; BehaviorAgent không có API `set_seed` riêng, không được ghi như thể seed bảo đảm CARLA physics quyết định tuyệt đối.

`session_id` là định danh phiên, tách khỏi `session_index` dùng công thức seed. Ghi server PID/start time hoặc boot token có bằng chứng operator restart; đổi tên session hay `reload_world` không phải phiên server độc lập. Pilot có thể chỉ dùng một phiên; không được coi nó đủ điều kiện ≥3 phiên. Khi full được duyệt, lịch cơ sở là 24 × 3 intent × 10 rep × 3 phiên = 2160 raw episodes/hồ sơ; noise-calibration runs bổ sung phải báo riêng khi thiết kế noise được chốt.

### 3.4 Manifest và raw

Trước run, ghi thông số được yêu cầu và giá trị thực tế đọc lại từ server: synchronous mode, fixed delta 0.05, no rendering=true, reload_world_each_run=true, substep settings, CARLA client/server versions, map/OpenDRIVE hash, thời tiết/đèn và fixture/catalog hash.

Ghi thêm: session id/index, restart evidence, seed và công thức seed, rep/scene/intent/profile, source/code/config hashes, Python/package versions, server executable/launch args nếu biết, GPU name/UUID/driver và renderer/device thực tế nếu xác định được. `nvidia-smi` liệt kê GPU không đủ chứng minh CARLA dùng GPU nào; ghi nguồn bằng chứng. Không xác định được GPU phải ghi `unknown` cùng lý do và báo người dùng, không bỏ cột hoặc bịa device. Machine/OS và thời gian UTC chỉ là provenance, không dùng làm seed.

Mỗi raw episode lưu:

- `states.csv`: mọi tick của ego và NPC, global frame và simulation time, run-relative time, pose XY/Z/yaw, vận tốc/tốc độ/gia tốc, control, actor key/id, road/lane IDs và collision flag.
- `events.jsonl`: marker và collision events với frame thực tế. Marker `action_start` xuất đúng một lần tại snapshot ngay trước command tick đầu tiên ở `intent.trigger_s`. Dùng mốc kích hoạt intent chung, kể cả intent chờ/không làm; không dùng thời điểm route-switch trễ hoặc khi xe bắt đầu lệch làn.
- `metadata.json`: initial snapshot/actual initial states, trạng thái complete/invalid và lý do, cấu hình/nguồn, global plan NPC, hash raw/events.
- Manifest append-only chỉ ghi complete sau khi raw/events/metadata đã flush và được kiểm tra. Invalid attempts vẫn có bản ghi; không coi thiếu dữ liệu là NPC không phản ứng.

Cửa sổ đo là 8 s từ marker; không nội suy hoặc bỏ tick thiếu để cứu run. Vòng tick lưu cả snapshot t=0 của cửa sổ, không bắt đầu ở t=0.05. Collision event frame là nguồn chính để cắt hai intent tại mốc sớm nhất, tránh phụ thuộc cờ callback xuất hiện trễ trong `states.csv`.

## 4. Phép đo được xây và test trước khi chốt thống kê

Phép tính xác định có thể test bằng quỹ đạo tổng hợp và pilot:

- Ghép NPC `npc_conflict` theo scene/session/rep và hai intent, căn global frame thành tick tương đối theo marker, kiểm tra cùng seed.
- `S_pos,r = max_t hypot(x_A-x_B, y_A-y_B)`; `S_speed,r = max_t abs(speed_A-speed_B)`. Kiểm thử đơn vị, NaN/Inf, duplicate/missing tick và cửa sổ khác độ dài. Không tráo độ chênh tốc độ vô hướng với độ chênh vector vận tốc; nếu Dũng muốn vector phải đăng ký thay đổi rõ ràng.
- Common collision limit = collision đầu tiên trong hai episode. Lưu mốc cắt, thời lượng còn lại và data-quality status, không dùng dữ liệu hậu va chạm để minh họa phản ứng.
- p90 max-difference và noise_t từ các trajectory cùng intent có định danh độc lập; không lấy counterfactual A/B làm noise và không coi cùng episode tái sử dụng là hai lần độc lập.
- Primitive onset nhận `noise_t` đã cung cấp: tick đầu có norm chênh vị trí `> max(noise_t, 0.1 m)` liên tục 10 tick; trả về tick đầu của chuỗi, không phải tick thứ 10. Không có chuỗi thì null, không tự thay bằng tick cuối cửa sổ.
- Độ biến thiên `S_pos`/`S_speed` và chênh tốc độ/khoảng cách ego tại onset có thể lưu dưới dạng descriptive, với convention được ghi trong analysis config. Pilot thiếu noise hợp lệ thì onset/noise-dependent values là null cùng lý do, không ép threshold=0.1 để tạo số liệu thật.

Không xuất CI để kết luận, scene/type response label, pass count hoặc overall decision trong phase này. Không tự chọn mean/median hay cách gộp phiên để lấp phần thống kê còn thiếu. Với noise/collision conventions chưa được duyệt, test chỉ xác nhận phép tính khi đầu vào/convention được truyền tường minh; output pilot ghi `protocol_status=pending`, không xem đó là phương pháp chính thức.

## 5. Cổng chốt thống kê và yêu cầu toàn bài được bảo toàn

Nguyễn Trung Dũng cần chốt trước triển khai suy luận/full:

1. CI percentile của estimator nào trên `S_r` (mean, median hay estimator khác); brief chỉ định `S_r` nhưng chưa chỉ định statistic được bootstrap.
2. 10 rep là 10 mỗi phiên hay tổng phân bổ qua ≥3 phiên; kiến trúc/lịch 2160 ở trên đề xuất 10 mỗi phiên. Đơn vị bootstrap và cách gộp/stratify phiên phải nhất quán, không nhân sample size bằng số tick.
3. Chọn independent same-action pairs và phân bổ noise-calibration budget: hành động nào, những rep/session nào, cách gộp trên 4 cảnh, chống tính lặp các cặp phụ thuộc. Audit TM cũ không đủ bao phủ 4 cảnh mỗi loại; không tự thay bằng audit đó.
4. Có bao gồm tick va chạm hay không; cách xét cửa sổ còn lại đúng 4 s; xử lý rep không đánh giá được trong một cell và số rep tối thiểu cần cho CI.
5. Convention tốc độ/khoảng cách ego tại onset, SD, và cách xử lý onset không xuất hiện khi lấy trung vị.

Sau khi được chốt, dùng cùng mode M21 trên BehaviorAgent và raw TM cũ, không dùng nhãn phản ứng TM từ chế độ legacy làm đối chiếu M21. Nếu raw cũ không đủ session/noise/marker bằng chứng thì báo coverage deficit; chỉ tái dựng marker từ metadata nếu được duyệt và giữ nhãn reconstructed, không ngụy tạo explicit event cũ.

Các yêu cầu brief còn lại không bị thay thế bởi pilot:

- Bootstrap percentile theo rep, có thay thế, 2000 lần; CI 98.3% (Bonferroni 3 cặp).
- Cặp phản ứng khi cả cận dưới vị trí `> max(2.0 m, 3×p90_pos)` và tốc độ `> max(1.0 m/s, 3×p90_speed)`; điều kiện là lớn hơn nghiêm ngặt.
- Collision cắt cả hai tại mốc sớm nhất; còn <4 s thì không đánh giá được.
- Cảnh phản ứng nếu ≥1/3 cặp đạt; cảnh không đánh giá được chỉ khi cả 3 cặp đều không đánh giá được, tính không phản ứng trong quyết định cảnh.
- Loại đạt nếu ≥3/4 cảnh phản ứng. Toàn bài đạt nếu ≥3/5 loại không tính rear_follow, đồng thời ≥1 loại thuộc cross_traffic/unprotected_left/overtake_slow đạt; rear_follow báo riêng.
- Báo số ô không đánh giá được/tổng ô; ô là scene × pair, không phải episode, rep hay tick. Cách gộp session của ô phụ thuộc quyết định ở mục 2.
- Onset cuối là trung vị onset_r; gradient chỉ mô tả, không kết luận liều–đáp ứng.
- Normal mặc định trước; chỉ thử cautious/aggressive sau khi normal không phản ứng và đã đăng ký trước với Dũng; không chỉnh parameter.

Cặp intent chính xác:

| Loại | Cặp 1 | Cặp 2 | Cặp 3 |
|---|---|---|---|
| cross_traffic | go_now / stop_before_crossing | go_now / yield_then_go | yield_then_go / stop_before_crossing |
| cut_in | change_now / do_not_change | change_now / wait_then_change | wait_then_change / do_not_change |
| unprotected_left | turn_now / do_not_turn | turn_now / yield_then_turn | yield_then_turn / do_not_turn |
| merge | merge_now / stay_lane | merge_now / wait_then_merge | wait_then_merge / stay_lane |
| overtake_slow | pass_now / follow_slow | pass_now / abort_pass | follow_slow / abort_pass |
| rear_follow | cruise / accelerate | cruise / brake_and_hold | brake_and_hold / accelerate |

Gradient order bảo toàn: merge_now > wait_then_merge > stay_lane; go_now > yield_then_go > stop_before_crossing; change_now > wait_then_change > do_not_change; turn_now > yield_then_turn > do_not_turn; pass_now > abort_pass > follow_slow; accelerate > cruise > brake_and_hold. Pair order không thay thế gradient order.

CSV yêu cầu theo brief gồm `scene_id, pair_id, intent_a, intent_b, rep, session, seed, collision, first_collision_tick, max_pos_diff_m, max_vel_diff_m, onset_tick`. Đây là dữ liệu của paired observation, không phải một raw intent episode; lưu file paired observation riêng với hai source run IDs và quality status, đồng thời lưu CSV raw từng episode. `max_vel_diff_m` là tên cột brief, dù đơn vị thực tế là m/s; ghi units/schema rõ, không tự đổi tên. Việc này không biến một paired observation thành hai phép thử độc lập.

## 6. Pilot và hạn mức cần duyệt

Brief ghi “20 run trước (crossing_01 × 2 cặp đầu × 10 lần lặp)”. Với quy tắc dùng chung seed/episode mới được xác nhận:

- Cặp 1: go_now / stop_before_crossing.
- Cặp 2: go_now / yield_then_go.
- Có 20 paired observations, nhưng cần 3 intent × 10 rep = **30 raw CARLA episodes**. Episode go_now mỗi rep được tái sử dụng, không chạy riêng cho từng pair.

**Đề xuất cần duyệt:** pilot là 30 raw episodes để tạo đúng 20 paired observations trong một phiên. Không khởi chạy pilot trước khi xác nhận cách hiểu này. Nếu hạn mức thực sự chỉ 20 raw episodes, cần sửa phạm vi cặp/rep, không thể tuyên bố đã đủ cả hai cặp ×10.

Báo thời gian wall-clock của setup, simulation, toàn pilot, số complete/invalid/retry, tổng simulated seconds, GPU/session evidence, dung lượng raw, và ước tính 2160 episodes dựa trên số đo thực tế. Không tự chạy hết sau khi pilot xong; chờ duyệt timing và thống kê. Nếu server/API/GPU/route thiếu thì báo blocker cụ thể và giữ logs, không im lặng hoặc tạo dữ liệu giả.

## 7. Hồi quy legacy: bằng chứng theo byte, không chỉ tolerance

Trước bất kỳ sửa mã sản phẩm nào, xác thực 720 run TM, lưu hash raw/metadata và capture baseline bằng chính đường phân tích legacy vào thư mục snapshot riêng, không ghi đè raw hoặc outputs cũ. Giữ cùng input, config, provenance, package versions, resampling seed/count, tham số CLI và output path logic trong hai lần so sánh.

So sánh trước/sau toàn bộ artifacts do phân tích legacy sinh cho `tm_default`: `actor_effects.csv`, `intent_pair_metrics.csv`, `scene_signal_metrics.csv`, `summary_by_scene.csv`, `response_report.md`, `decision.json`, `reproducibility_audit.csv` và `baseline_failure_notice.md` nếu invocation tạo nó. Snapshot/regression harness phải ghi inventory để phát hiện cả file thiếu/thừa. Không loại bỏ provenance, làm tròn số, đổi thứ tự hàng hoặc bỏ dòng để che khác biệt. Giữ riêng baseline capture trước sửa và danh sách SHA-256; report kiểm chứng có `before_sha256 == after_sha256` cho từng file.

Các report hiện lưu gồm cả reactive profile, nên không so report full-profile với report TM-only. Baseline là cùng invocation trên đúng 720 TM observations trước sửa, rồi cùng invocation sau sửa; nếu muốn đối chiếu toàn report hiện lưu, phải dùng nguyên bộ input/profile tương ứng. Cả hai kiểm tra không được chạm vào raw cũ.

Giữ byte của `controllers.py`, `runner.py`, `scenario_catalog.py`, `metrics.py`, `report.py` và catalog/config legacy. Regression bổ sung default mode so với explicit `--mode legacy`, absence/import failure của CARLA agents không được ảnh hưởng legacy offline. Dependency nâng cấp hoặc đổi serializer không nằm trong phạm vi.

## 8. Kiểm chứng và tiêu chí hoàn thành phase pilot

1. Unit tests xác nhận seed chung giữa intent nhưng khác scene/rep/session; indices không đổi khi filter; trùng seed/tuple/retry không tạo rep độc lập.
2. Fake-world tests chứng minh prefix/intent controller và output ego trùng vòng legacy, marker không lệch một tick, delayed/no-action intent vẫn có cùng t=0.
3. Measurement tests dùng quỹ đạo tổng hợp có giá trị biết trước, hai cửa sổ va chạm khác nhau, missing/duplicate/nonfinite tick, onset 9 và 10 tick, null onset/noise.
4. Provenance tests xác nhận requested vs observed settings, session evidence, GPU unknown có reason, source/hash mismatch và resume không ghi đè.
5. Regression thực trên 720 raw TM hợp lệ có inventory + SHA-256 toàn output giống hệt; legacy unit tests vẫn chạy qua.
6. Pilot được duyệt đủ quota, timing/raw/events/manifest và diagnostic CSV/report có sẵn. Không xuất M21 decision labels hoặc overall decision file; CLI full/decision bị chặn khi `protocol_status=pending`.

Không có tiêu chí nào ở đây tương đương ĐẠT/KHÔNG ĐẠT M21. Không có kết luận M55 từ việc đọc file hoặc xây mode M21.

## 9. Handoff

Duyệt thiết kế này, đặc biệt đề xuất 30 raw pilot episodes/20 paired observations, trước khi viết implementation plan task-by-task. Sau khi duyệt plan, chọn Native hoặc Subagent-driven rồi mới triển khai. Quyết định thống kê ở mục 5 là cổng riêng, có thể chốt sau khi xây/test hạ tầng và pilot, nhưng phải chốt trước suy luận và full matrix.

Tự rà soát: phạm vi pilot/legacy regression được tách khỏi suy luận; quyết định seed mới thay quy tắc cặp cũ; mọi yêu cầu full được bảo toàn ở mục 5; không có giả định đã chạy pilot hoặc hồi quy; các điểm cần Dũng chốt được liệt kê, không bị tự quyết trong thiết kế.
