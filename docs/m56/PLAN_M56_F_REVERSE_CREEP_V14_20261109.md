# M56 A-SEL2: kế hoạch consumer v14, lùi và bò native cho F03, F05 và F06 (09/11/2026)

Đây là kế hoạch kỹ thuật của Claude, chưa phải prereg. Thẩm quyền: A-SEL2 §1.4 ("Claude soạn recipe F") và
`PLAN_M56_F_ASEL2_20261108.md` §4, mục "F03, F06 (ngoại lệ lùi …)". Nhãn: CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

## 1. Vấn đề (đọc trên product v13)

Ba chỗ sau được viết cho composition tổng hợp, nên một episode native không bao giờ thỏa được:
- creep của F05 B: `_creep_stop_proof` và `_creep_guard`, `response.py:729–860`;
- lùi của F03 B và F06: `_reverse_inputs`, `response.py:640–700`.

Mỗi chỗ đều đòi:

| Điều kiện | Mã lỗi |
|---|---|
| route đúng 2 điểm, đi theo +x, y và z không đổi, mọi góc bằng 0 | `*_ALIGNMENT_UNSUPPORTED` |
| pose của actor có pitch/yaw/roll **đúng bằng 0** ở **mọi** khung history | `REVERSE_HISTORY_OBSERVATION_UNBOUND`, `CREEP_ALIGNMENT_UNSUPPORTED` |
| `y` của actor bằng đúng `y` của route (creep) | `CREEP_ALIGNMENT_UNSUPPORTED` |
| proof `REVERSE_STOP_BOUND` / `CREEP_STOP_BOUND` đã hiệu chỉnh, bám vào hash response/route/body/recipe | `*_STOP_BOUND_MISSING` |
| `reverse_history_ref` / `creep_history_ref` / `creep_fixture_ref` trong `frame.integrity`; proof `QUEUE_PATH` / `REVERSE_CORRIDOR` | `*_UNBOUND`, `*_UNPROVEN` |

Native đã có sẵn: ground proof theo từng khung (`recorded-ground-contact-v1`, `native_v2_kit.Kit.frame`) và control lùi
(`runtime.py:572`).

## 2. Thay đổi ở product (v14, công khai, giữ luật cũ chạy song song)

1. **Căn trục.** Route là đường thẳng theo một trục thế giới:
   - yaw của mỗi điểm cách trục ≤ 1° (`_axis_right`, như B5 và io);
   - điểm route lấy từ native, không ép đúng 2 điểm.
2. **Pose.** Yaw của actor cách trục của route ≤ 1°. Pitch/roll lệch so với tư thế spawn đã đóng băng ≤ 0,5°, theo cùng tinh
   thần A-SEL2 §6.
3. **Dịch ngang.** Thay điều kiện `y == y_route` bằng: |dịch ngang so với route| ≤ 0,15 m. Đây là cùng biên 3/20 mà corridor lùi
   đã dùng.
4. **Tiến trình theo trạm.** `_metric_station` trên route native thay cho chênh x. Phần cộng dồn quãng đi và hard limit giữ nguyên.
5. Mọi luật cũ (`*_old_rule`) được báo song song, như v12 đã làm.

## 3. Tooling (không đổi product)

1. **Hiệu chỉnh dừng.** Một probe native trên đúng site, cùng luật `bounded-reverse-stop-v2`, `bounded-forward-creep-stop-v1`:
   - đo quãng dừng và tốc độ tối đa, lặp vài lần;
   - lấy biên bất lợi;
   - viết proof `CapabilityProof`, raw refs là các file probe đã seal.
2. **Kit.** Ghi history (trajectory đã seal) và fixture ref vào `frame.integrity` ở mỗi khung, trong lúc chạy. Dựng proof
   `QUEUE_PATH` và `REVERSE_CORRIDOR` từ drivable dv1.
3. **F06:** đặt `VehicleLightState.Reverse` cho cue số lùi, và witness phải đọc lại đèn (smoke 09/11).
4. **F03:** site R3 có độ dốc thuộc khoảng của prereg F phần 2 (đang chờ grade probe).

## 4. Thứ tự và kiểm

- Product v14:
  - test cho mỗi luật mới;
  - test hồi quy: mọi test F03/F05/F06 tổng hợp phải vẫn xanh;
  - full suite chỉ chạy một lần, trên bản cuối.
- Tooling:
  - test offline (compile + contract);
  - một probe hiệu chỉnh trên mỗi site;
  - một A/B mỗi cảnh (P5).
- Mỗi cơ chế cần commit realized (F05, F06, F03) và prereg phần 2 (F03, F04') **trước** A/B.

## 5. Ước lượng và rủi ro

- **Thời gian:** khoảng 2–3 ngày.
- **Rủi ro F06:** Δ trong cảnh của §8.2 khoảng 0,10. Prereg F §2 quy định: nếu phác thảo lý tưởng không đạt ≥ 0,20 thì ghi
  `DIVERSITY_DEFICIT` trước A/B.
- **Rủi ro F05:** creep 0,5 m/s với `max_brake` 3/10 trên stock PID. Biên dừng 1 m có thể không đủ. Khi đó ghi đúng như đo.
