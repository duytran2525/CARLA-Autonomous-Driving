# M56 A-SEL2 addendum M: io-i-v1.3 a, đặt NPC của cảnh I theo arc (16/11/2026)

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** người dùng phiên này [chat] 15/11/2026 chọn "Hạ I04, làm successor", tức là sửa cách đặt NPC rồi chạy lại I04.
Lời này nối tiếp yêu cầu "tiếp tục sửa các cảnh còn lại".

**Tính chất:** luật **sau khi thấy số** (nguyên tắc 6). Viết sau khi addendum L tìm ra lỗi kẹp NPC, trước mọi bước native dùng
luật này.

## 1. Luật

- Chỉ áp cho cảnh loại I. Cảnh O giữ luật cũ: lệch ≤ 0,42 m, không bị kẹp.
- **Cũ** (`native-io-prepare.py` dòng 379): NPC probe 2 xuất phát ở hàng đầu tiên **trên road site R** có road-s ≥ s_n.
- **Mới** (`native-io-prepare-i13.py`): NPC xuất phát ở hàng đầu tiên của route NPC probe 1 có arc ≥ arc(k0) + shift. shift vốn đã
  là mét theo arc tính từ k0, nên đây là cùng đại lượng, chỉ bỏ phần kẹp.
- Nếu route không đủ dài phía sau (arc(k0) + shift < arc của hàng đầu): `BLOCKED_FIXTURE` `NPC_RUNIN_SHORT`.
- Mọi phần khác giữ nguyên: io-v1.5, io-v1.6, io-i-v1.2 G2 và addendum J. Không sửa file nào, `_prepare_o` được biên dịch lại từ
  chính byte của nó.
- Cổng L (|gap thực − gap| ≤ 0,5 m) vẫn chạy sau prepare và là cổng quyết định.

## 2. Tự kiểm offline (route probe 1 đã seal)

| Cảnh | shift (m) | NPC lùi theo luật mới (m) | Road xuất phát mới |
|---|---|---|---|
| I04 | −33,60 | 33,4 | 1149 (đoạn nối) |
| I02-S2 | −19,63 | 19,6 | 11603 |
| I05-S1 | −6,69 | 6,6 | 2364 |
| I01-S1 | −15,40 | 15,2 | 12088 |

- I06 không bị kẹp (shift dương), nên luật mới không đổi gì.
- Đã biết rủi ro: NPC sẽ xuất phát trên road trước road site, có khi là đoạn nối trong nút giao. Builder revision đã từng chặn
  `CATALOG_ROUTE_NOT_ON_SITE_LANE` ở một trường hợp khác.

## 3. Lần dùng native đầu tiên

- `run-asel2-i13-prep.sh`: **chỉ prepare** I01-S1 (Town12), sau hàng đợi O. Sau đó chạy cổng L và dựng revision offline với prep đó
  (`asel2i13dry`) để xem builder có nhận không.
- Không compile, không A/B, P5 chưa tốn. HOLD vẫn áp dụng.
- Kết quả quyết định luật có dùng được cho I04, I02, I05 successor hay không. Thời điểm đổi làn của B (G3) vẫn là một phần riêng,
  chưa viết.
