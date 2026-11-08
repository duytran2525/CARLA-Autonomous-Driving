# M56 A-SEL2: handoff (08/11/2026, sau khi dừng an toàn)

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

## 0. Trạng thái máy lúc bàn giao

- Không còn tiến trình M56, CarlaUE4 hay watchdog nào. Cổng 2610 đã trống.
- Worktree `m56-v1` nhánh `feat/m56-v1` có tooling và docs, đã merge cục bộ `feat/m56-v11`.
- Product mới nhất là `m56-v11` nhánh `feat/m56-v11`, gồm v10 và các thay đổi của v11.
- Không push lên remote. Chỉ còn `progress.md` có sửa chưa commit; đó là file của người khác hoặc phiên cũ, không đụng tới.
- Sổ main: commit cuối của phiên này là `f55dd48` (+ mục dừng). Memory: `m56-v5-status.md`.

## 1. Mục tiêu và thẩm quyền

- Duy (người dùng tự xưng, đã trao "toàn quyền") muốn đủ **46 cảnh, 23 junction qualified và 155 phép so**, theo spec addendum
  **A-SEL2** (`docs/m56/SPEC_ADDENDUM_SELECTION_EXPANSION_20261108.md`). Các mục chính:

  | Mục | Nội dung |
  |---|---|
  | §1 | mọi town trừ Town03; trần thay cảnh 150; Claude chọn cảnh và ký review (not independent) |
  | §4 | LrefN là tham số so thứ 3 cho C/L |
  | §5 | input F theo thang |
  | §6 | pitch/roll ban đầu so với tư thế spawn (consumer v11) |
  | §7 | M dùng 2/3 tham số (vN, G, LrefN); trần (M, town) = 4; M07 dùng k = −2 |

- **Mọi thay đổi trên đều là luật đặt sau khi thấy số.** Kết quả theo spec cũ (10 cặp, RELEASE_BLOCKED,
  `M56_RELEASE_PARTIAL_COUNTS_20261108.md`) giữ nguyên, và mọi báo cáo ghi theo cả hai luật.
- **Luật cứng:**
  - P5: mỗi cảnh một A/B cho mỗi version;
  - nguyên tắc 6: không đổi ngưỡng sau khi thấy số, trừ khi Duy quyết, và khi đó phải ghi cả hai luật;
  - không push;
  - CARLA chỉ chạy trên server riêng 2610, mỗi lúc một server, chỉ dừng cây tiến trình của chính mình;
  - không xóa vĩnh viễn;
  - không sửa byte nào của spec;
  - không suy ra danh tính người dùng từ git.

## 2. Chọn cảnh

- **Fill v4:** prereg `PREREG_M56_FILL_V4_ASEL2_20261108.md`, với addendum:

  | Addendum | Nội dung |
  |---|---|
  | A | nhìn trước |
  | B | B1 cổng cua, B2 cửa sổ một road, B3 thay cảnh |
  | C | M04/M07 |
  | D | B4, đã rút lại |
  | E | chạy đà NPC nối qua junction |

- Bộ sinh: `fill-v4-generate.py`, chạy `OUT COMMIT [--replace STATE.json]`.
- Output, theo thứ tự (biến `M56_ASEL2_REPLACE` liệt kê các lần thay):
  - `outputs/m56_fill_v4a_20261108.json` (30/30);
  - `outputs/m56_fill_v4_replace1_20261108.json` (I02, O08);
  - `outputs/m56_fill_v4_replace2b_20261108.json` (L07);
  - `outputs/m56_fill_v4_replace3_20261108.json` (M04, M07, M08).
- Sổ trần thay cảnh: `outputs/m56_asel2_replacements.jsonl` (chỉ nối thêm). Đã dùng **34/150**.
- Revision: `run-asel2-revision.sh TAG [PREP_DIRS]`. Các biến:
  - `M56_ASEL2_FILL` (mặc định trỏ v4a);
  - `M56_ASEL2_REPLACE` (các lần thay, cách nhau bằng dấu phẩy);
  - `M56_ASEL2_IO=1` để dựng cả I/O.
- **Successor:** id `M56-P-<slot>-S<n>`. Cảnh tiền nhiệm bị loại khỏi revision.
- **Không bao giờ tính:** M04-S1, M07-S1 (addendum C).

## 3. Trạng thái từng cảnh

| Cảnh | Trạng thái |
|---|---|
| C01, C05, C08, L01, L04, O01, O02, O03, I03, I04 | cặp hợp lệ cũ, giữ nguyên |
| C02-S1, C03-S1, C04-S1, L02-S1 | A/B đã chạy (v10, Town12), cả 4 đều `INITIALIZATION_INVALID` (xem §4). Chưa chạy pair. Quota P5 dưới v10 đã dùng |
| L05-S1, M05-S1, M06-S1 (Town12); C07-S1, L03-S1, L06-S1, M01-S1, M03-S1 (Town13) | PREPARED, chưa A/B (L05-S1 bị dừng trước episode) |
| C04-S1, M05-S1 | sẽ chuẩn bị lại dưới v11 với spawn nghiêng (pitch EGO 0,7° / −0,97°) |
| C06-S1, M02-S1 | chuẩn bị lại dưới v11 + tilt (spawn error, NPC pitch khoảng 1°) |
| L08-S1 | chuẩn bị lại với erratum E6 (`M56_E6=1`, PHASING_ROOM) |
| L07-S2, M04-S2, M07-S2, M08-S2 | successor mới, chưa chuẩn bị |
| I01-S1, I05-S1, I06, I07-S1, I08, O04-S1, O05-S1, O06, O07-S1, I02-S2, O08-S2 | chưa chuẩn bị; batch I/O dưới v11 + tilt (`run-asel2-io.sh`) |
| F01–F06 | chưa có tooling native; mới có bản nháp prereg `PREREG_M56_F_ASEL2_DRAFT_20261108.md` |

## 4. Việc phải làm đầu tiên ở phiên mới

1. **Chẩn đoán `INITIALIZATION_INVALID` trên Town12 trước mọi A/B nào khác trên map lớn.**
   - Raw: `outputs/m56_v2_ab_Town12_20261108T115001Z/<scene>/run/episodes/<scene>/A`.
   - Đầu mối: x ở frame đầu lệch tư thế đóng băng 2–4 cm, mà `_initial_state_matches` (`m56/evidence.py`) đòi ≤ 1e-4. Thứ tự
     trường pose trong script chẩn đoán chưa được kiểm, nên phải đọc pose bằng `decode_record('Transform6', ...)`.
   - Nghi vấn: float32 ở |y| khoảng 5000 m, rebasing của large map, hoặc stream sau spawn.
   - Đây là lỗi hạ tầng, nên xử lý theo spec §4 (version kỹ thuật, giữ raw, không tự chạy lại). Nếu cần đổi luật initial-state
     thì đó là quyết định của Duy, và phải ghi cả hai luật.
2. Chạy pair (`native-v6-pair.py` dưới m56-v11) cho 4 cảnh đã có A/B, rồi ghi kết quả.
3. **Map lớn chậm:** raster vùng drivable dv1 cần khoảng 148.000 lệnh `cast_ray`, mỗi lệnh khoảng 30 ms, tức khoảng 1,5–2 giờ cho
   mỗi A/B. Nếu tối ưu (ví dụ gom ray hoặc dùng lưới thô cho phần xa route) thì phải làm thành version kỹ thuật, kiểm rằng kết quả
   trùng byte trên một cảnh cũ, và làm trước batch.

## 5. Cách chạy lại an toàn

1. Chạy watchdog: `python -I start-detached.py LABEL python -I -X utf8 asel2-watchdog.py 300 1800 1800`.
   - Checkpoint: `outputs/m56_asel2_checkpoint.json`. Sự kiện: `outputs/m56_asel2_watchdog.jsonl`.
   - Trạng thái OK/SLOW/HUNG. Khi HUNG: dump py-spy rồi dừng cây tiến trình của mình. Không bao giờ tự chạy lại.
2. Chạy hàng đợi: `run-asel2-queue.sh`, gồm smoke F, rồi I/O (v11 + tilt), rồi batch 2.
   - Bỏ dòng `until ... m56_asel2_cl_t1213 ...` ở đầu file, vì batch 1 sẽ không bao giờ in END nữa.
   - Đổi M56_CODE thành m56-v11 nếu chưa.
3. Phần còn lại của batch 1 (L05-S1, M05/M06-S1 và Town13): chạy bằng `run-asel2-ab-resume.sh REV.json "Town12:... Town13:..."`.
   Script này bỏ qua các cảnh đã AB_STARTED. Hoặc chạy A/B mới dưới v11, tùy kết quả chẩn đoán ở §4.
4. Mọi script được khởi chạy tách rời bằng `start-detached.py` với `D:\Git\usr\bin\bash.exe`. `bash` trần trỏ vào WSL.

## 6. Release

- Bộ lắp ráp: `asel2-release.py REV.json [--full]`, chạy với `M56_CODE=m56-v11`.
- Bản dry trên 10 cặp hiện có: mọi phép so REALIZED đều PASS, qualified_junctions = 5.
- Deficit còn lại: số cảnh, số junction, C0 cuối (freeze_c0 trên 46 cảnh), độ phủ 155 phép so, bằng chứng A/B.
- `--full` cần khoảng 7 GB RAM mỗi cảnh; chỉ chạy khi CARLA đang rảnh.
- Chỉ export khi không còn deficit nào. Không bao giờ ép export.

## 7. F

- Kế hoạch `PLAN_M56_F_ASEL2_20261108.md`; bản nháp prereg `PREREG_M56_F_ASEL2_DRAFT_20261108.md`.
- Thứ tự: smoke capability (`native-f-capability-smoke.py`), rồi chốt khoảng của F03, rồi prereg F, rồi product v12 (tham số hóa
  các kiểm F đang khóa cứng ở `response.py` khoảng dòng 300–370), rồi tooling native F.
- Ước 4–6 ngày.
