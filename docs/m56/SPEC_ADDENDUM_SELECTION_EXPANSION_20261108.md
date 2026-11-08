# M56 spec addendum A-SEL2: mở rộng chọn cảnh tới 46 cảnh và 23 junction (08/11/2026)

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.
Selector: `CLAUDE_PREREG_ALGORITHM_NOT_INDEPENDENT`.

**Thẩm quyền:** [chat] ngày 08/11/2026, người dùng phiên này (đã tự xưng Duy ngày 07/11/2026, trưởng dự án) trả lời
từng câu hỏi Claude đặt ra:

| Câu hỏi | Nguyên văn trả lời |
|---|---|
| Mục tiêu | "tôi muốn phải có đủ 46 cảnh và 23 junction hợp lệ có được không tôi muốn làm tiếp" |
| Town | "trừ town03 ra còn lại các town khác đều được làm spec v-mới mở rộng chọn cảnh" |
| Tải thêm map | "tải thêm town11-15 cho tôi tự động cập nhật thêm đi" |
| Trần số lần thay | chọn "150 (Recommended)" |
| Loại F | chọn "Claude soạn recipe F" (Claude soạn chương trình NPC cho F01–F06 theo §8; F04 được thay bằng một cơ chế không cần cửa xe, do Claude đề xuất và ghi công khai) |
| Phép so | chọn "Claude soạn, trước A/B" (Claude soạn bộ mô tả phép so từ §6.4 và commit trước các A/B mới; cặp nào đã có số thì ghi là đặt sau khi thấy số) |

**Quan hệ với spec:** spec gốc `docs/superpowers/specs/2026-10-07-m56-catalog-and-validation-design.md` (sha256 `8e1e2ba3…`) và
các addendum A-C0P, G4G5 **không đổi byte nào**. Addendum này là một version mới, đọc kèm spec.

**ĐÂY LÀ THAY ĐỔI ĐẶT SAU KHI THẤY SỐ.** Nó được quyết sau khi đã biết 10/39 cảnh hợp lệ, và sau khi Claude đã chứng minh rằng dưới
spec cũ không thể đạt 46/23 (trần thay cảnh 9, Town04–07, nguồn ứng viên đã hết). Hệ quả:
- Kết quả của spec cũ là `M56_RELEASE_PARTIAL_COUNTS_20261108.md` (RELEASE_BLOCKED, 10 cặp). Kết quả đó **giữ nguyên** và là
  kết quả chính thức theo spec cũ.
- Mọi báo cáo về sau phải ghi theo cả hai: spec cũ và A-SEL2.
- Catalog A-SEL2 do Claude chọn, và cảnh được thay cho tới khi chạy được trong phạm vi trần. Phải ghi rõ đây là chọn cảnh có
  điều kiện theo kết quả (selection conditioned on runnability). Catalog này không được trình bày như một mẫu độc lập.

## 1. Những gì đổi

1. **Town:** Town01, Town02, Town04, Town05, Town06, Town07, Town10HD, Town11, Town12, Town13, Town15. **Không có Town03.**
   Không còn giới hạn "Town04–07", nhưng vẫn đòi ≥ 3 town.

   Map đã pin (sha256 của XODR, đo ngày 08/11/2026). Gói `AdditionalMaps_0.9.16.zip` (7.250.055.782 byte, tải ngày 08/11)
   trùng CRC với 22.592/22.592 file đã cài, nên không file nào bị ghi đè.

   | Town | sha256 XODR |
   |---|---|
   | Town01 | `97a7f6ac67812567e5c8ee0599cd823b23f80f30f3f97c502212e38b72e2b709` |
   | Town02 | `953c05f17def231239ffcadba3307628a82d0d335b67b4e29c3098f7aed1dd7d` |
   | Town04 | `4dddd1560ab7812b0e89cd4a523d8b6f2b93947eafb496d9eeb83cc772116c85` |
   | Town05 | `7edc53b0be840e177598da7a4ed9571146d7b2595ce280d154c90f92e8a48851` |
   | Town06 | `a90b613175fa837fdc128ddfaf5ddad25797b128fdbd8cd945974bc21a60496e` |
   | Town07 | `be730652769e993e27f748ba5793dba9e49d299205146a7a8db0bcd17af877bf` |
   | Town10HD | `5d883b799f634030af92be1e9d79d107845540ba04338e8c60e095be1aef7be7` |
   | Town11 | `52ffa8412425b87394afa6a37bf0b688c0584a24df6ae88fea53866acb91e222` |
   | Town12 | `26fa53d4902ac3397d35f948969f0c77c1bf023755ede2c67edf00bef817151f` |
   | Town13 | `5354326f2fe4d26f0dcb5c82acf462257e638278363ab7adecb97ec3aa1f426f` |
   | Town15 | `8e9c69cfb3e750ace3e5d6b057e46786952a073c3924f319bbabb1a166dc2c17` |

   Town nào không load hay tick được trên laptop thì bị loại, kèm bằng chứng `native-town-load-test.py` và lý do
   `BLOCKED_CAPABILITY`.

2. **Trần thay cảnh: 150** (spec cũ: 9). Cách đếm giữ như spec §4:
   - mỗi successor được admit tiêu 1 lần, kể cả khi nó hỏng;
   - thay lại cùng một slot thì tiêu thêm;
   - lấp một slot trống (I06, I08, O06, O08, F02, F05, F06) cũng tiêu 1.

   Lần thứ 151 thì dừng, không reset và không nâng trần. Trần này được đặt **một lần**, trước A/B mới đầu tiên.

3. **Chọn cảnh:**
   - Claude chọn bằng thuật toán prereg (fill v4). Prereg phải commit trước khi chạy bộ sinh.
   - Thứ tự ứng viên được xáo bằng seed đã đăng ký và gán first-fit. Không chọn tay.
   - Tiêu chí của fill v4 phải giữ nguyên trong suốt đợt, kể cả khi một town cho ít cảnh hơn dự kiến.
   - Claude ký các review `SITE_IDENTITY` và `SITE_QUALIFIED` (`CLAUDE_REVIEW_UNDER_DUY_DELEGATION`, not independent).

4. **F:**
   - Claude soạn recipe NPC cho các cơ chế F theo mô tả §8, thay cho phần PROVISIONAL.
   - F04 (cửa xe) được thay bằng một cơ chế F khác, do Claude đề xuất trong prereg F. Cơ chế mới phải khác 5 cơ chế còn lại
     theo định nghĩa §2 (trigger event, cấu trúc quyết định của EGO).
   - Mọi recipe F phải commit trước A/B đầu tiên của cảnh F tương ứng.

5. **Phép so:**
   - Claude soạn `descriptor_specs` (tham số, đơn vị, event, cửa sổ, nguồn) cho phép so trong cùng loại, theo §6.4.
   - Bộ mô tả phải commit trước A/B mới đầu tiên của đợt A-SEL2.
   - Với các cặp đã có số trước ngày đó (10 cặp hiện có), phép so được ghi là đặt sau khi thấy số.

## 2. Những gì KHÔNG đổi

- Mọi ngưỡng đo, mọi luật consumer (v6–v9) và mọi proof của witness.
- Mục tiêu 46 cảnh và đủ số theo loại (C, L, M, I, O mỗi loại 8; F 6), ≥ 23 junction qualified, đủ 155 phép so.
- ≤ 3 cảnh cho mỗi cặp (loại, town); cap 2 trên site; danh tính site.
- P5: mỗi cảnh một A/B cho mỗi version.
- Không push, không merge remote.
- Các lỗi đã ghi (C02, C06, C07, M01, …) không được chạy lại dưới version hiện có. Thay chúng thì dùng trần thay cảnh.

## 3. Thứ tự làm

1. Commit addendum này, rồi ghi vào sổ.
2. Test load các town trên laptop.
3. Prereg fill v4 (C/L/M/I/O), prereg F, rồi `descriptor_specs`; commit từng cái trước khi dùng.
4. Product v10, diff tối thiểu: tập town ở `catalog.py:95`, trần thay cảnh, hash map, quy tắc cho reviewer của site. Kèm test
   có mục tiêu; full suite để cuối.
5. Mỗi town lần lượt: chuẩn bị, revision, mỗi cảnh một A/B, rồi pair. Commit tài liệu trước mỗi lượt chạy.
6. Release: gọi `export_catalog` chỉ khi `_release_deficits` rỗng. Hết trần mà chưa đủ thì báo số thật theo §11.

## 4. Bổ sung 1 (08/11/2026): tham số so thứ ba LrefN cho C và L

**Census offline** (`asel2-census.py`, `outputs/m56_asel2_census_20261108c.json`; `asel2-ladder3.py`):
- G tính đúng bằng `derive_g` của product, trên mọi site của 11 town.
- Với cặp tham số (vN, G) của §6.4:
  - M: có lời giải (G từ 9,5 tới 52,5 m);
  - C: **không có lời giải** với mọi phương án giữ hay bỏ cảnh. G khả dĩ chỉ trải 10,5 → 41 m (3,9 lần), mà 8 cảnh cần 1,25⁷ ≈ 4,77 lần;
  - L: **không có lời giải** (khoảng G của từng slot quá hẹp).
- Thêm LrefN thì C và L đều có lời giải.

**Quyết định:** [chat] Duy, ngày 08/11/2026, chọn "Thêm LrefN cho C/L (Recommended)". Với C và L, bộ mô tả phép so là (vN, G,
LrefN). Một cặp đạt (về mặt khai báo) khi ≥ 2 trong 3 tham số lệch ≥ 20%, cộng với review D09. M, I, O, F giữ bộ hai tham số
của loại mình.

**Đặt sau khi thấy số; phải ghi kèm mọi báo cáo:**
- G = vE²/3 + vE/2 + vE·(LrefN + 5)/(2·vN) + 1/2 là hàm của LrefN và vN, nên LrefN không độc lập với G. Reviewer có thể coi đây
  là đếm trùng một chiều khác biệt.
- Mọi phép so C/L phải báo theo cả hai quy tắc: (vN, G) theo §6.4, và (vN, G, LrefN) theo bổ sung này.
