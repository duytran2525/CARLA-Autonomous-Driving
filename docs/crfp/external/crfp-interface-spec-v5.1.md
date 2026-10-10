# ĐẶC TẢ GIAO DIỆN Ý ĐỊNH — v5.1 (BẢN KHÓA)

- **Ngày:** 04/10/2026. **Trạng thái:** KHÓA.
- **Phạm vi khóa:** cấu trúc, công thức dạng hàm, quy tắc tuning, sàn an toàn chung, đăng ký trước.
- **Chưa khóa:** mọi hằng số số học — tìm trên tập dev, đóng băng trước khi chạy test.
- **Quy tắc sửa tiếp theo:** chỉ khi cài đặt lộ lỗi thật → ghi v5.x kèm lý do trong sổ quyết định.
- **Lịch sử:** v1 (khung) → v2 (vá lỗi logic terminal/state, công bằng, bảng cặp) → v3 (phân lớp executor, lưới tham số, ETA chung) → v4 (macro vào executor chung, arm núm đầy đủ) → v5 (rollout chung, chính sách mặc định, ép ý định, macro NHUONG) → v5.1 (4 ghi chú: v_term đối xứng, B_off/D_off, confound C→D, đếm ứng viên thực tế).

---

## 0. Nguyên tắc [Chốt]

- Nhãn ý định do **script** sinh trực tiếp từ privileged state của simulator. Không có vector, không có rời rạc hóa ở giai đoạn này. VLM/vector latent xếp sau Gate 1.
- Killer experiment (1a, 1b, 2) chỉ dùng giao diện nhãn này; mọi thí nghiệm nhắm vào nhãn.
- Ba thí nghiệm kiểm tra *ý tưởng* (goal có đổi hành vi? hành động ego có đổi phản ứng xe khác? giao diện ý định có biểu diễn được hành vi mà núm không làm được?), không kiểm tra khả năng học.
- Q11/Q14/Q16 (tách ngữ cảnh, rời rạc hóa, tắt mục tiêu ở bản học) **hoãn sang bản học sau Gate 1**, không phải đóng.

---

## 1. Kiến trúc phân lớp [Đề xuất]

- **Executor (dùng chung cả hai arm)**:
  - Thư viện maneuver — micro: `LANE_KEEP`, `LANE_CHANGE_LEFT/RIGHT`, `TURN_LEFT/RIGHT`, `STOP`; macro: `VUOT(target_agent)`, `NHUONG(target_agent)`.
  - Trajectory tracker + controller: nhận maneuver command + tham số → sinh và bám quỹ đạo.
  - **Không tự ra quyết định rời rạc** (không tự quyết "có nên đổi làn không").
  - **Emergency monitor** (luồng riêng 10 Hz, cả hai arm dùng chung): theo dõi TTC các xe trên đường đi của ego; TTC < 3 s [đề xuất, chưa khóa] → xử lý khẩn cấp ngay, bypass mọi luật giữ/đổi. Đếm số lần kích hoạt làm metric.
  - **Safe behavior** theo trạng thái (mục 13), cả hai arm dùng chung.
- **Lớp quyết định arm ý định (D)**: script chấm điểm → xếp hạng các lựa chọn rời rạc (micro + macro) → trigger lựa chọn thắng.
- **Lớp quyết định arm núm (B)**: `k` suy từ slack → ngưỡng theo `k` → trigger cùng tập maneuver/macro.
- **Arm núm + rollout (C)**: như B, nhưng trước khi trigger phải qua kiểm tra rollout.

---

## 2. Tập ý định [Chốt cấu trúc / Đề xuất nội dung]

- Cấu trúc [Chốt]: mỗi bước quyết định (2 Hz [đề xuất]) sinh micro `(dọc, ngang, target_agent?)` hoặc trigger macro.
- Trục dọc: `TANG_TOC(v_target, a_max)`, `DUY_TRI(v_target)`, `GIAM_TOC(v_target, a_dec)`, `DUNG(d_stop)`.
- Trục ngang: `GIU_LAN(lat_tol)`, `NHAP_TRAI/PHAI(gap_min, t_complete, target_agent)`, `RE_TRAI/PHAI(exit_lane, intersection_id)`.
- Macro: `VUOT(target_agent)`, `NHUONG(target_agent)`.
- Ánh xạ nhãn → maneuver command 1-1 (`NHAP_TRAI` → `LANE_CHANGE_LEFT`, …).
- `target_agent`: id xe liên quan ("vượt xe này", "nhập vào gap giữa hai xe này") — cầu nối sang attention và sang việc chọn xe đo phản ứng ở lõi (b).

---

## 3. Macro VUOT(target_agent) [Đề xuất]

- Phase 1 `TIẾP_CẬN`: `(DUY_TRI/GIAM_TOC, GIU_LAN)`, bám sau target ở khoảng cách an toàn.
- Phase 2 `CHỜ_GAP`: `(DUY_TRI, GIU_LAN)`, chờ gap làn bên ≥ gap_min. **Timeout 15 s** [đề xuất] → hủy macro, quay về FOLLOW.
- Phase 3 `NHAP`: `(TANG_TOC, NHAP_TRAI/PHAI)`. Điểm không quay lại: dịch ngang quá 50% chiều rộng làn → bắt buộc hoàn tất hoặc xử lý khẩn cấp.
- Phase 4 `VƯỢT`: `(TANG_TOC/DUY_TRI, GIU_LAN)` ở làn mới.
- Phase 5 `TRẢ_LÀN`: `(DUY_TRI, NHAP về làn gốc)`. Điều kiện: rear_gap trong làn gốc ≥ 20 m [đề xuất] và không có xe đang nhập vào khoảng đó.
- Abort bất kỳ phase nào khi nguy hiểm → emergency handling của executor.

---

## 4. Macro NHUONG(target_agent) [Đề xuất — macro thứ hai]

- `GIẢM_TỐC` → `CHỜ` (đến khi target đi qua hoặc timeout 10 s [đề xuất]) → `TIẾP_TỤC`.
- Dùng cho: nhường xe nhập làn, nhường ở ngã tư không đèn.
- Đồng thời là scenario đẹp cho 1b: ép nhường vs ép không nhường → đo phản ứng xe được nhường.

---

## 5. Tham số và lưới giá trị [Đề xuất]

- `v_target`: lưới 3 mức `{0.6, 0.8, 1.0} × v_capped`, với `v_capped = min(giới hạn tốc độ, v_xe_trước + 5 m/s)`.
- `gap_min`: tính theo vật lý `max(15 m, v × 1.5 s)` — không phải lựa chọn tự do.
- Hệ số biên gap cho arm ý định: `m_gap ∈ {1.0, 1.5, 2.0} × sàn` [đề xuất] — dải khớp với arm núm.
- `t_complete`: nhập làn 6 s, rẽ 8 s [đề xuất].
- Dung sai: tốc độ `max(1.0 m/s, 10% × v_target)`; làn 0.3 m; heading 15° [đề xuất].

---

## 6. Bảng cặp hợp lệ [Đề xuất]

| | GIU_LAN | NHAP_TRAI/PHAI | RE_TRAI/PHAI |
|---|---|---|---|
| TANG_TOC | ✓ | ✓ | ✗ (không tăng tốc khi rẽ) |
| DUY_TRI | ✓ | ✓ | ✓ |
| GIAM_TOC | ✓ | ✓ | ✓ |
| DUNG | ✓ | ✗ | ✗ (dừng thì không nhập/rẽ) |

Script chỉ sinh cặp có ✓. Ngoại lệ khẩn cấp được override bảng.

---

## 7. Rollout động học chung [Đề xuất]

Dùng chung cho: scoring (arm D), kiểm tra khả thi + lợi ích ETA (arm C), ETA module tính `k` (arm B/C).

- Horizon H = 10 s [đề xuất, chưa khóa], dt = 0.5 s.
- **ACC trong rollout**: ego không chạy profile hở. Mỗi bước `v_ego = min(v_profile, v_acc)` với `v_acc = v_lead + max(0, gap − gap_min)/τ` (τ = 1.5 s [đề xuất, tuning]). Không có xe trước trong tầm nhìn → v_acc = +∞.
- **Xe dẫn xác định theo làn tại từng bước**: khi ego đổi làn giữa rollout, xe dẫn dùng cho ACC đổi theo làn hiện tại của ego ở bước đó.
- Xe khác: vận tốc không đổi (privileged).
- **Giá trị cuối đối xứng (v5.1)** — tốc độ duy trì sau H phụ thuộc ứng viên, cùng quy tắc cho mọi ứng viên:
  `v_term,c = min(v_capped, v_lead_trong_làn_kết_thúc)`.
  Không có xe dẫn trong làn kết thúc → `v_term = v_capped`.
  Macro chưa hoàn thành trong H → cộng thời gian hoàn thành ước tính còn lại rồi áp dụng `v_term` tương ứng.
- `ETA_c = t_sim + (D_rem − d_sim) / v_term,c`.
- An toàn trong rollout: bước nào có TTC < TTC_min hoặc gap < gap_min → safety = −∞.
- `t_wait` của CHỜ_GAP: `max(0, (gap_cần − gap_tốt_nhất_hiện_tại) / tốc_độ_mở_gap)` [đề xuất] — **bắt buộc kiểm chứng trên dev** (so ước tính vs chờ thực tế) trước khi dùng cho ETA.

---

## 8. Hàm chấm điểm — arm ý định (D) [Đề xuất]

Với mỗi ứng viên c (micro hợp lệ × mức `v_target` × `m_gap`, cộng các macro khả thi):

- `goal_term_c = clip(((deadline − now) − ETA_c) / T_scale, 0, 1)` (T_scale = T_ref, xem mục 20).
- `progress_c = clip(d_c / (v_capped × H), 0, 1)`.
- `comfort_c = 1 − clip(n_đổi_làn × 0.2 + phanh_gấp × 0.3, 0, 1)` (phanh_gấp = 1 nếu giảm tốc > 3 m/s² trong rollout) [hệ số đề xuất].
- `score_c = w_goal·goal_term + w_prog·progress + w_comf·comfort` (+ safety override), `Σw = 1` [trọng số tuning].
- Nhánh goal-off: `w_goal = 0`, các trọng số còn lại chuẩn hóa lại theo tổng còn lại.
- Log điểm **mọi** ứng viên, không chỉ cái thắng.

---

## 9. Chính sách mặc định dùng chung [Đề xuất]

Goal-independent — **cả hai arm giống hệt**:

- Bám route: trigger `RE_*` theo route; chọn làn theo route.
- Theo xe: ACC với gap_base.
- Nhập làn **bắt buộc** (hết làn, on-ramp): gap = max(sàn an toàn, gap_base) — thận trọng, không theo k/goal.
- Dừng theo luật giao thông / vật cản qua safety layer.
- **Hai arm chỉ khác ở**: mức `v_target`, chấp nhận gap cho maneuver **tự chọn** (vượt), trigger `VUOT`/`NHUONG`.

---

## 10. Arm núm (B) [Đề xuất]

- `ETA_default` = rollout mục 7 với chính sách mặc định ở `v_capped`.
- `slack = (deadline − now) − ETA_default`.
- `k = clip(1 − slack / T_ref, 0, 1)` (T_ref tuning, khởi đầu 60 s [đề xuất]).
- Quyết định phụ thuộc mục tiêu:
  - `v_target = v_capped × (0.6 + 0.4·k)` — dải 0.6–1.0, **bằng arm ý định**.
  - `gap_accept_vượt = clamp(1.5·sàn × (1.3 − 0.6·k), sàn, 2·sàn)` — base gấp 1.5 lần sàn để `k` có tác dụng toàn dải, không bao giờ dưới sàn.
  - Trigger `VUOT`: `k > 0.65` [tuning] và xe trước chậm hơn 30% và gap ≥ gap_accept_vượt.
  - Trigger `NHUONG`: `k < 0.3` và có xe cần nhường → nhường; `k` cao → đi trước.
- Biến thể hysteresis: `k` làm mượt (EMA); macro đã trigger cam kết tối thiểu 5 s [đề xuất].
- Mọi hệ số vào ngân sách tuning ngang với `w_*`.

---

## 11. Arm núm + rollout (C) [Đề xuất]

- Tính `k` như arm B (cùng công thức, cùng `T_ref`, cùng ETA module). Cùng ngưỡng trigger như B.
- **Khác**: trước khi trigger maneuver/macro, chạy rollout chung (mục 7) kiểm tra:
  (a) khả thi/an toàn trong H;
  (b) lợi ích ETA: `ETA_có_maneuver < ETA_không − margin_ETA` (margin 2 s [đề xuất, tuning]).
- Chỉ trigger khi cả ngưỡng `k` và rollout đều đồng ý.

---

## 12. Các biến thể tắt goal [Đề xuất — v5.1]

- **D_off** (dùng cho thí nghiệm 1a): arm ý định với `w_goal = 0` (các trọng số còn lại chuẩn hóa lại). So sánh D vs D_off đo tác động của mục tiêu trên cùng một arm.
- **B_off** (dùng cho thang đo): arm núm với `k = k0` hằng số. `k0` được **tìm trên dev với cùng ngân sách tuning** như mọi tham số khác — **không đặt 0 hoặc 1** (tránh baseline rơm).

---

## 13. Luật giữ/đổi [Đề xuất]

- Micro terminal đang active ở một trục → chỉ chấm lại trục còn lại trong các cặp hợp lệ.
- Micro state: chấm lại mỗi bước 2 Hz; đổi khi `score_mới − score_cũ ≥ δ` (δ = 0.15 [đề xuất, chưa khóa]) trong `K = 3` bước liên tiếp [đề xuất].
- **Chuyển state → macro dùng cùng luật δ/K** (macro là ứng viên trong bảng xếp hạng).
- Macro đang active: chạy theo phase machine; dừng khi hoàn thành / timeout / abort.
- Khẩn cấp: emergency monitor → xử lý ngay, bypass tất cả.

---

## 14. Điều kiện hoàn thành [Đề xuất]

- `NHAP`: |lệch ngang so với tâm làn đích| ≤ 0.3 m.
- `RE`: |lệch heading so với đường ra| ≤ 15° hoặc đã qua ngã tư.
- `DUNG`: v ≤ 0.5 m/s tại điểm dừng.
- Hết `t_complete` → timeout, chuyển an toàn/khẩn cấp.

---

## 15. Ý định an toàn — executor chung [Đề xuất]

- Mặc định: `(GIU_LAN, GIAM_TOC)` về v = 0 có kiểm soát.
- Đang `NHAP` qua điểm không quay lại → hoàn tất nhập làn trước.
- Giữa ngã tư → thoát ngã tư trước.
- Khẩn cấp → profile phanh **có xét xe sau**: nếu TTC_rear < 2 s [đề xuất] thì giảm độ gấp phanh, ưu tiên giữ làn + giảm tốc từ từ thay vì phanh gấp.

---

## 16. Sàn an toàn chung [Chốt nguyên tắc]

`gap_min` vật lý và `TTC_min` áp dụng cho **cả hai arm**. `k` và scoring chỉ được chọn *an toàn hơn* sàn, không được nới dưới sàn — đảm bảo metric an toàn không bị lẫn do một arm liều hơn.

---

## 17. Chế độ ép ý định — cho thí nghiệm 1b [Đề xuất]

- Bypass hoàn toàn scoring/núm. Nhận trực tiếp `(maneuver command + tham số)` → executor.
- Khai báo: scenario_id, seed, danh sách xe khác (loại agent, hành vi, vị trí đầu).
- 1b: cùng scene + seed, ép ý định A vs B (vd: `(DUY_TRI, GIU_LAN)` vs `(TANG_TOC, NHAP_TRAI)` cùng target) → đo phản ứng xe khác trong cửa sổ T.
- **Chỉ cần executor → làm được ngay, không phụ thuộc mục 7/8/10/11.**

---

## 18. Logging [Đề xuất]

Mỗi bước quyết định log: timestamp, scene_id, goal, maneuver được trigger, tham số, điểm **mọi** ứng viên, **số ứng viên thực tế** (v5.1 — không dùng số ước tính, vì RE_* do route quyết định, DUNG không có v_target, m_gap chỉ cho nhập làn/macro), phase (nếu macro), sự kiện khẩn cấp/timeout.
Cộng: quỹ đạo mọi xe trong 50 m [đề xuất], seed, config scenario. Dữ liệu tái dùng cho cả hai lõi.

---

## 19. Scenario và đăng ký [Đề xuất]

- Người chọn scenario **không tham gia chỉnh arm ý định**.
- Lấy từ Bench2Drive / CARLA Leaderboard **trước khi** thiết kế macro; chia dev/test trước khi tuning; người tuning chỉ thấy dev.
- Hai loại: đơn ngưỡng (kỳ vọng hòa) và đa bước (kỳ vọng arm ý định thắng). Thắng cả hai loại → nghi ngờ lợi thế tuning, phải kiểm tra lại.

---

## 20. Công bằng, tuning và phạm vi khóa [Chốt nguyên tắc]

- Hai arm (+ biến thể): cùng privileged inputs, cùng executor, cùng ETA module, cùng dải hành động, cùng sàn an toàn.
- Khác nhau: quy tắc quyết định (xếp hạng có cấu trúc vs ngưỡng theo `k`, ± rollout).
- Mọi hằng số (`w_*`, `δ`, `K`, `T_ref`, `T_scale = T_ref` [ghi rõ phụ thuộc], hệ số ánh xạ núm, dung sai, timeout, margin_ETA, τ, `k0`, ngưỡng trigger...) vào ngân sách **"tuning ngang nhau"**: chỉnh trên tập **dev**, **đóng băng trước khi chạy test**.
- Khóa cấu trúc + quy tắc; không khóa hằng số số học.

---

## 21. Thang đo arm và cách đọc [Đề xuất — v5.1]

| Arm | Nhận biết mục tiêu | Nhìn trước | Quy tắc quyết định |
|---|---|---|---|
| B_off | không (k = k0) | không | ngưỡng |
| D_off | không (w_goal = 0) | có | xếp hạng |
| B | có | không | ngưỡng |
| C | có | có | ngưỡng + kiểm tra rollout |
| D | có | có | xếp hạng |

- Mỗi bước thang thêm **một yếu tố chính** (không phải "đúng một yếu tố" — còn yếu tố lẫn, liệt kê dưới).
- Cách đọc: D > B nhưng D ≈ C → lợi thế từ **nhìn trước**. D > C → lợi thế từ **xếp hạng có cấu trúc**.
- Yếu tố lẫn còn lại: B→C thêm cả kiểm tra khả thi (một dạng thận trọng); C→D thêm cả độ rộng tìm kiếm (D xét ~nhiều ứng viên với hạng mục comfort/progress, C chỉ kiểm tra 1 maneuver được trigger).
- Ablation tương lai (sau Gate 1 nếu cần): D với tập ứng viên thu hẹp bằng đúng tập C có — để cô lập "xếp hạng" khỏi "độ rộng tìm kiếm".

---

## 22. Phát biểu đóng góp (để dành cho paper)

"Các arm dùng chung thư viện maneuver (gồm macro nhiều pha), executor, ETA module và sàn an toàn; khác nhau ở quy tắc quyết định: **xếp hạng có cấu trúc các lựa chọn rời rạc** vs **ngưỡng theo một vô hướng k** (± rollout kiểm tra)."

---

## 23. Giới hạn kết luận (giữ nguyên khi viết paper)

(a) Máy trạng thái viết tay — thí nghiệm 2 chỉ kiểm tra *giao diện*, chưa nói gì về khả năng học được.
(b) Luật trigger của arm núm cũng là cấu trúc viết tay → đây là so sánh các quy tắc quyết định, chưa phải "có cấu trúc vs không cấu trúc".
(c) Trần chất lượng khi dùng log huấn luyện Student sau này chính là script.
(d) Rollout giả định xe khác vận tốc không đổi → **không dự đoán phản ứng**; đây đúng là chỗ CRFP (lõi b) sẽ thay thế sau này.
(e) `goal_term` kẹp về 0 khi trễ → mọi ứng viên trễ hòa nhau (chấp nhận được).
(f) `t_wait` là ước lượng thủ công — đã đánh dấu bắt buộc kiểm chứng trên dev.

---

## 24. Thứ tự cài đặt [Đề xuất]

1. Executor + chế độ ép ý định (mục 1, 15, 17).
2. Thí nghiệm 1b — rủi ro lớn nhất của lõi (b) — kèm **pilot đo nhiễu** để tính số lần lặp (đầu vào cho mục 35).
3. Chính sách mặc định + rollout (mục 7, 9).
4. Các arm B, D, C (mục 8, 10, 11).
5. Song song từ đầu: kiểm tra tái dùng CARLA BehaviorAgent — **lưu ý**: phải strip quyết định rời rạc tự động của nó để giữ nguyên tắc phân lớp (mục 1).
