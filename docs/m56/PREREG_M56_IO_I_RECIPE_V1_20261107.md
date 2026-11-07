# M56 recipe phía I io-i-v1 (cảnh cut-in), đăng ký trước, 07/11/2026

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** ủy quyền toàn quyền của Duy (tự xưng, 07/11/2026). Bản này do **Claude quyết dưới ủy quyền đó**.

**Trạng thái lúc đăng ký:** chưa có lần chuẩn bị, compile hay episode nào của cảnh I. Số liệu duy nhất đã dùng là catalog đóng
băng, spec và hình học tĩnh.

## 1. Phạm vi

- **Pilot I03** (Town06 R40, thẳng). Sau đó I07 (R38), I04 (R37), I05 (R39), dùng hình học fill của io-v1.3 và route đi qua
  connector.
- I01 và I02 nằm trên R45 và R37 của Town04/05, nơi cửa sổ spec đè lên đoạn cong (như O01/O02). Hai cảnh này cần dời site và một
  prereg riêng, nên ngoài phạm vi bản này.
- **Nền:**
  - consumer v9 (`1db746f`);
  - recipe io-v1 + v1.1 + io-v1.2: RUNIN = ⌈100·vE/9,375⌉; hộp làn neo ở trung điểm; section phủ hai làn trên toàn route; đuôi
    route EGO = X + gap + 2 thân xe + 20 m;
  - io-v1.3: hình học fill, route đi qua connector với mọi điểm lệch ≤ 1°;
  - cận lateral theo điểm (`M56_IO_KAPPA=pointwise`), báo cả hai cận.

## 2. Vai trò làn (spec §7.3 và §7.4; catalog đóng băng)

| | Cảnh có bảng spec (I03) | Cảnh fill (I04, I05, I07) |
|---|---|---|
| Làn EGO (EGO_INITIAL) | `E<l>` trong alias | `lanes[0]` |
| Làn nguồn (NPC lúc đầu; EGO B đổi sang đây) | `N<a>→<b>`: a | `lanes[1]` |
| Làn đích của NPC | b (bằng làn EGO) | `lanes[0]` |
| front_t0 / X | road-s trong bảng spec | front_t0 = điểm bắt đầu đoạn đổi làn đã đóng băng của EGO B − 4·vE; X = điểm bắt đầu + Dlc + 3,75 (spec: front_t0 → X = 4·vE + Dlc + 3,75) |

## 3. Các lựa chọn của Claude (đặt trước khi có số)

| # | Mục | Luật |
|---|---|---|
| a | Response NPC (phụ lục, không bao giờ vào catalog) | Chương trình: SETTLE → NOMINAL tại CAPTURE_START (delay RELEASE như phụ lục v5) → NPC_TARGET tại `NPC_TARGET_LANE_CONFIRMED`, cần `REFERENCE_MARKER:NPC:NPC_TARGET`. Target NOMINAL = NPC_TARGET = vN |
| b | Profile ngang của NPC | Một đoạn quintic, offset 0 → separation của NPC (tâm làn nguồn → tâm làn EGO), độ dài **3·vN** (spec "I NPC 3 s scale"; consumer đòi 3·nominal) |
| c | Switch của NPC | Event `NPC_TARGET_LANE_CONFIRMED`, cause NPC_TARGET; marker = cuối đoạn; route = làn EGO trên cùng khung arc với route NPC (chiếu lên route NPC, giống EGO_TARGET); profile 0 |
| d | Vị trí dọc của NPC | Như O, bước 3: NPC được dời dọc làn nguồn sao cho lúc t0 (mũi EGO tới front_t0) **đuôi NPC cách mũi EGO đúng gap**, đo bằng probe chạy thẳng |
| e | Thời điểm cắt vào | Điểm bắt đầu đoạn = station của NPC lúc t0 (probe 2) − u_i·3·vN. u_i là nghiệm của q(u_i) = (w_nguồn/2 − nửa bề ngang thân NPC)/\|separation\|, tức là lúc mép thân NPC chạm ranh giới làn khi NPC ở tâm làn. Đây là ước lượng; TRIGGER thật là lúc NPC thực sự xâm nhập ranh giới (consumer) |
| f | Vùng | EGO_INITIAL = hộp làn EGO; EGO_TARGET = hộp làn nguồn = `source_region`; `npc_regions` = {NPC_INITIAL: hộp làn nguồn, NPC_TARGET: hộp làn EGO}; neo hộp ở trung điểm như io-v1.2 |
| g | Section | `I_SOURCE_BOUNDARY` = mặt phẳng ở cạnh chung của hai hộp, trải theo chiều chạy trên toàn route, pháp tuyến hướng từ làn nguồn vào làn EGO. X và DESTINATION như O |
| h | Domain | Hộp [front_t0, X] × hai làn, như O |
| i | Probe | Probe 1 và 2 chạy EGO theo chương trình A (chỉ NOMINAL, vì probe không có TRIGGER) và NPC chạy thẳng (phụ lục, profile 0) để đo plateau, t0, gap và vị trí. Không có probe cắt vào |
| j | Kiểm trước A/B | `PREPARED` → `FROZEN` + `ADMITTED` (v9) → ước tính thời gian online < 270 s. Self-check và replay của O chưa có bản cho I. Thay vào đó, admission (hợp đồng response của consumer cho EGO A/B và NPC) là cổng offline |

## 4. Luật dừng

- **Mỗi cảnh một A/B (P5).** `M56_IO_PREREG_APPROVED=<commit của file này>`, `M56_IO_KAPPA=pointwise`. Pair theo v9 và theo v8.
- **Không chỉnh tham số sau khi thấy số.** Cảnh không qua được cổng thì BLOCKED, có ghi lý do.
- **Lỗi code của tooling** (lỗi khiến chương trình dừng hoặc tính sai, không phải kết quả của cảnh) được sửa trước kết quả, mỗi
  lần bằng một addendum có ghi rõ, giống io-v1.3.
- Nếu một lỗi chỉ lộ ra sau khi A/B đã chạy, việc chạy lại theo P5 cần chứng minh offline trên dữ liệu đã seal.

## Addendum A (07/11/2026): thứ tự làn của cảnh I trong catalog fill (lỗi đọc catalog)

**Phát hiện:** lần chuẩn bị đầu (`outputs/m56_prep_I_v1_20261107.*`, tooling `8fd07bd`):
- I03: PREPARED.
- I04 và I07 dừng trước probe với `CATALOG_ROUTE_NOT_ON_SITE_LANE (37, −7)` / `(38, −4)`.
- Nguyên nhân: route EGO của catalog nằm trên `lanes[1]`, không phải `lanes[0]`. Bảng §2 viết sai thứ tự làn cho cảnh I fill.

**Sửa:** làn EGO là làn mà route EGO đã đóng băng trong catalog nằm trên; làn còn lại là làn nguồn. Kiểm ở bước compile
(`end_offset` của đoạn đổi làn đã đóng băng của EGO B phải bằng separation đo được) bảo đảm hai vai không bị đảo.
