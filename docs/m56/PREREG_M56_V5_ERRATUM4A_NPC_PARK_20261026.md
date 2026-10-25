# M56 v5 erratum 4a: NPC dừng hẳn trước khi hết plan đã cắt theo erratum 4 (ĐỀ XUẤT, chờ Duy)

**Trạng thái:** PROPOSED. Chưa sửa code, chưa chạy lại.

**Lý do phải chờ Duy:**
- C01 và C05 đã dùng lần chạy lại duy nhất mà P5 cho phép (lần chạy lại theo erratum 4).
- Chạy thêm một lần nữa là đổi P5, nên nằm ngoài ủy quyền "làm theo lựa chọn Claude khuyến nghị".

**Nguồn gốc:** đề xuất đặt sau khi thấy kết quả chạy lại theo erratum 4.

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

## Lỗi (harness, do erratum 4 gây ra)

Erratum 4 cắt route và plan của NPC tại s_end, trước khúc cua nằm sau đích của NPC. Episode thì chạy tới khi EGO tới đích:
- Khi plan của NPC hết trước lúc đó, `LocalPlanner` gốc trả về lệnh phanh khẩn cấp với brake = 1,0.
- Product đã đóng băng coi brake = 1,0 là lệnh không hợp lệ (giới hạn là brake ≤ 0,3; xem test
  `test_early_empty_queue_brake_one_not_clamped_into_valid_control`).
- Runner vì vậy dừng episode với `TICK_ERROR` (`ValueError('STOCK_CONTROL_INVALID')`, ghi trong `runner/failure.json`).

| Episode (chạy lại theo erratum 4) | Frame lỗi | Event đã có | Thiếu |
|---|---|---|---|
| C01-A (`m56_v2_ab_Town04_20261025T164906Z`) | 538 | STOP, TRIGGER, NPC_ENTRY, CLEAR_N, E_ENTRY | DESTINATION_CONFIRMED |
| C05-A (`m56_v2_ab_Town05_20261025T165244Z`) | 442 | STOP, TRIGGER, NPC_ENTRY, CLEAR_N, E_ENTRY | DESTINATION_CONFIRMED |
| C05-B | 442 | như trên | DESTINATION_CONFIRMED |

- C01-B không bị lỗi này vì EGO tới đích trước khi NPC hết plan. Kết quả: d_yield 10,557 m, t_entry 9,6 s, giống lần v5f.
- Các cảnh M03, M06, M07, M05, L và C02/C03 có route NPC dài (không bị cắt, hoặc cắt sau mét 230), nên không bị ảnh hưởng.

## Thay đổi đề xuất

Chỉ áp dụng khi erratum 4 đã thực sự cắt route (`npc_route_end_e4.cut_index` khác null). Program của NPC (annex prereg v2 2.2, do
tooling dựng; hợp đồng `_forward_contract` của product chỉ ràng buộc EGO ở C/L/M) được thêm một transition:

`{'cause': 'PARK', 'after_event': 'CLEAR_N_CONFIRMED', 'delay_s': d, 'requires': ()}`, với target PARK = 0.

- **Công thức:** d = max(0, (s_end − s_front_at_clear − m) / vN), làm tròn xuống tới 0,05 s, trong đó:
  - s_front_at_clear = station của n_exit + 0,5 m + chiều dài thân xe;
  - m = vN² / (2 · 1,5 m/s²) + 5 m (quãng dừng thận trọng với brake ≤ 0,3, cộng 5 m dự phòng).
- **Khi không đủ chỗ:** nếu s_end − s_front_at_clear < m thì cảnh nhận `BLOCKED_FIXTURE NPC_PARK_ROOM`.
- **Dừng xe:** với target 0, PID dọc gốc tự phanh trong giới hạn 0,3. NPC dừng sau khi đã ra khỏi hộp, trên road đi ra của chính
  nó. Phase này giống nhau ở A và B, vì NPC dùng chung một program cho cả hai action.

**Không đổi:** ngưỡng, G, erratum 4 (s_end giữ nguyên), consumer, program của EGO.

## Chạy lại (cần Duy quyết)

Đề xuất chạy lại C01 và C05 đúng một lần nữa với recipe này. Kết quả cũ (v5f và lần chạy lại theo erratum 4) giữ nguyên làm hồ sơ.
