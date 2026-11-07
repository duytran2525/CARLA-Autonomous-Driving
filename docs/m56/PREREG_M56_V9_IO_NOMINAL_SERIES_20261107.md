# M56 consumer v9: tốc độ nominal I/O theo chuỗi k đã duyệt (đăng ký trước, 07/11/2026)

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:**
- [chat] 07/11/2026, người dùng tự xưng Duy: "tôi cho bạn toàn quyền quyết định … làm theo điều bạn recommended … hoàn thiện task
  m56".
- Bản này do **Claude quyết dưới ủy quyền toàn quyền của Duy**. Không phải Duy review.
- Ghi sổ: `docs/crfp/crfp-main-ledger.md` (`114cba1`).

## 1. Vấn đề (mục c của `PROPOSAL_M56_ROAD_TO_46_20261026.md`)

Hai văn bản đã duyệt mâu thuẫn nhau:
- **Spec §6.1:** "I/O E01–03 = 6 / 7.5 / 9.375 m/s"; "I NPC01–03 = 5 / 6.5 / 8.375 m/s".
- **`PREREG_M56_FILL20_20261022.md` §4** (Duy duyệt 22/10, `dd2954c`), cho các chỗ mới: I và O dùng `vE(k) = 6·(5/4)^(k−1)`; I dùng
  `vN = vE − 1`. Fill v3 (Duy duyệt 24/10, `4a26a66`, quy tắc F3-2) thêm k = −2.

Consumer (v5 C2 tới v8) cố định cứng tập `{6, 15/2, 75/8}` cho EGO và `{5, 13/2, 67/8}` cho NPC loại I. Tập đó đúng bằng k = 1, 2, 3
của chuỗi FILL20. Vì vậy mọi cảnh I/O có k ∉ {1, 2, 3} (I04/O04 k = 4; I05/O05 k = 0; I07/O07 k = −1; I06/O06 k = −2) đều bị
`LATERAL_NOMINAL_INVALID` / `NORMATIVE_NOMINAL_INVALID` ngay lúc admission, dù tooling làm đúng đến đâu.

**Sửa một nhận định cũ:** đề xuất 26/10 cho rằng đây "có vẻ là lỗi đơn vị k" của catalog. Kiểm lại thì nhận định đó sai: catalog
khớp đúng FILL20. Mâu thuẫn nằm ở consumer, vì consumer chỉ mã hóa E01–03 của spec.

## 2. Vì sao đây không phải là đổi luật sau khi thấy số

- Chưa có A/B, prep hay compile native nào cho các cảnh có k ∉ {1, 2, 3}. Tức là chưa có số nào về các cảnh mà luật này mở ra.
- Với k ∈ {1, 2, 3}, luật mới cho đúng tập cũ. O01, O02, O03 và mọi kết quả đã có vì vậy **không đổi**; test bắt buộc chứng
  minh điều này.
- Luật không nới ngưỡng nào. Nó chỉ cho consumer đọc đúng chuỗi tốc độ mà catalog đã duyệt dùng.
- Nhận định của Claude: đây là một mâu thuẫn khách quan giữa hai văn bản đã duyệt, không phải một luật "hơi chặt".

## 3. Luật v9 (nguyên văn)

Một tốc độ nominal `v` của EGO trong cảnh I hoặc O là **hợp lệ** khi và chỉ khi tồn tại số nguyên `k` với `−4 ≤ k ≤ 8` sao cho
`v == 6·(5/4)^(k−1)`, so khớp **chính xác** bằng số hữu tỉ.
- Nominal của NPC trong cảnh I hợp lệ khi và chỉ khi `v + 1` thỏa đúng điều kiện trên (spec: `vN = vE − 1`).
- Khoảng k ∈ [−4, 8] bao trọn các k mà spec §6.1 và FILL20/v2/v3 dùng (1–8, 0, −1, −2), cộng biên 2.
- O-B follow giữ đúng 5/2 m/s như cũ.

Luật áp dụng ở cả năm chỗ: `_lateral_contract` (EGO và NPC) và bốn normative policy O-A, O-B, I-A, I-B trong `m56/response.py`.

**Luật cũ (v8, giữ để báo cáo):** `v ∈ {6, 15/2, 75/8}` (EGO); `v ∈ {5, 13/2, 67/8}` (NPC loại I). Kết quả của mọi cảnh I/O có
k ∉ {1, 2, 3} sẽ được báo theo cả hai luật. Theo luật cũ, các cảnh đó luôn bị chặn lúc admission.

## 4. Code và kiểm

- Nhánh mới `feat/m56-v9`, tách từ `feat/m56-v8` `8761970`. Chỉ đổi `m56/response.py` và thêm `tests/m56/test_v9_io_nominal.py`.
- Test bắt buộc:
  - chuỗi tạo đúng 4,8 / 3,84 / 3,072 / 11,71875;
  - k ∈ {1, 2, 3} cho đúng tập cũ;
  - giá trị lệch một chút (ví dụ 4,81) bị từ chối;
  - NPC = vE − 1.
- Chạy lại bộ test bị ảnh hưởng: I/O, lateral contract, response, evidence, metrics.

## 5. Phạm vi sau v9

- Chỉ chuẩn bị (prep / compile / self-check / replay) O04, O05, O07 theo recipe io-v1.2 + v9.
- Mỗi cảnh có một prereg recipe riêng (dời site, run-in, cận lateral), commit **trước** A/B của cảnh đó, rồi chạy đúng một A/B
  (P5).
- Các cảnh I cần tooling phía I trước, kèm prereg riêng.
