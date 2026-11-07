# M56 cl-v1: thử lại spawn và probe dài cho M01, M02, M08 (08/11/2026)

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** Duy (tự xưng) trao toàn quyền ("bạn toàn quyền quyết định không cần tôi duyệt"). Claude quyết dưới ủy quyền đó.

**Thời điểm:** commit trước mọi A/B của M01, M02, M08. Ba cảnh này chưa từng có A/B, nên P5 cho mỗi cảnh một A/B.

**Luật đặt sau khi thấy số, phải ghi công khai như vậy:**
- Luật a được chọn sau hai lượt chẩn đoán spawn (`native-spawn-diag.py`; output `outputs/m56_spawn_diag*_20261108*`). Chẩn đoán chỉ
  gọi `try_spawn_actor` rồi hủy ngay, không có fixture, không có A/B, không có số đo của cảnh.
- Luật b được chọn từ lần chuẩn bị M01 ngày 24/10 (`READINESS_NOT_REACHED`, 320 frame), cũng không phải số A/B.
- Không ngưỡng nào thay đổi. Spec không đổi byte nào.

## 1. Chẩn đoán

| Cảnh | Điểm xuất phát EGO | Pose của prepare (ground + 1 cm, pitch 0) | Nâng theo bốn góc |
|---|---|---|---|
| M02 (Town04 road 40 làn −4) | road dốc −1,35° | va chạm | nâng 4,44 cm: spawn được |
| M08 (Town07 road 111, trong junction) | mặt junction gồ ghề | va chạm | nâng 2,43 cm: spawn được |

Ngoài ra (không dùng làm luật): với M02, pitch theo waypoint cũng spawn được, còn dời xuôi 1–5 m thì vẫn va chạm. Với M08,
nâng +3 cm và +4 cm spawn được, pitch theo waypoint thì không.

**Ràng buộc của proof GROUND:** `|z − 0,01 − ground| + 1e-4`, làm tròn lên 1e-4, cộng uncertainty 0,001, phải ≤ 0,05 m. Vì vậy
cách nâng cố định 5 cm bị loại.

## 2. Luật

**a. Spawn (trong `native-v2-prepare.py`):** nếu probe 1 không có frame nào và verdict có `SPAWN_ERROR:<role>`:
- đặt z của role đó = độ cao `ground_projection` lớn nhất tại tâm và bốn góc footprint của thân a2, cộng 1 cm;
- x, y, yaw giữ nguyên, pitch và roll bằng 0;
- chạy lại probe 1 **một lần** (label `probe1-lift`).

Proof GROUND của A/B vẫn đo so với ground tại tâm, nên phần nâng hiện ra trung thực trong `maximum_ground_error_m`. Nếu phần nâng +
0,0011 > 0,05 thì cảnh nhận `BLOCKED_FIXTURE SPAWN_GROUND_LIFT`.

**b. Probe dài:** nếu trong probe 1 mũi EGO không lần nào tới trong khoảng G + 1 m trước e_entry (T_end thiếu, do giới hạn
readiness 15 s của product), thì:
- mọi probe chuẩn bị còn lại của cảnh chạy với `runtime.READY_LIMIT_S = 60`, bằng giới hạn chờ pha tối thiểu;
- probe 1 được chạy lại **một lần** (label `probe1-long`).

A/B không đổi: runner vẫn dùng 15 s của product.

**Phạm vi:** cả hai luật chỉ kích hoạt ở cảnh gặp đúng điều kiện trên. Các cảnh đã chuẩn bị trước đây không được chuẩn bị lại, nên
byte của chúng không đổi.

## 3. Chạy

- Chuẩn bị M01, M02 (Town04) và M08 (Town07) dưới recipe v6, trên revision erratum 3 (v5g), product `m56-v9` (`1db746f`).
  Luật v6 về NPC rẽ (`NPC_TURN_BEFORE_EXIT` / `NPC_TURN_SPEED`) vẫn áp dụng như cũ.
- Freeze một revision C0 partial gồm nền của `run-io-revision.sh` cộng các lần chuẩn bị mới (đặt cuối nên thắng).
- Mỗi cảnh PREPARED chạy đúng một A/B (`native-v2-ab.py`), rồi tính kết quả pair bằng `native-v6-pair.py`, dưới consumer v9 và
  v6. Báo cáo theo cả hai luật.
- Cảnh hỏng hay bị chặn ở bất kỳ bước nào thì ghi lại, không chỉnh thêm và không chạy lại trong phiên này.
