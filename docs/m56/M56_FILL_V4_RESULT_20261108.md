# M56 fill v4 (A-SEL2): kết quả chọn cảnh (08/11/2026)

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.
Selector: `CLAUDE_PREREG_ALGORITHM_NOT_INDEPENDENT`.

## Hai lần chạy

| Lần | Prereg | Generator | Output | Kết quả |
|---|---|---|---|---|
| 1 | `03fb2ca` | `90c1be5` | `outputs/m56_fill_v4_20261108.json` (sha256 `3c750762…`) | 28/30; M05 và M07 rỗng do first-fit tham lam (`LADDER`, `TOWN_CAP`) |
| 2 | addendum A `ddce811` | `cd6f575` | `outputs/m56_fill_v4a_20261108.json` (sha256 `824748f5…`) | **30/30** |

**Output dùng cho đợt chạy là lần 2.** Output lần 1 được giữ nguyên.

Còn một lần chạy dở ở commit `0707e9a`, bị dừng tay vì tìm kiếm của bước nhìn trước quá chậm, và không ghi ra file nào. Bản
`cd6f575` chỉ đổi cách gom nhóm trong bước nhìn trước: gom theo đúng các tham số so của loại thay vì cả bộ tham số. Kết quả tìm
không đổi. Đây là sửa hiệu năng, không phải đổi luật.

## Gán (lần 2)

| Slot | Town | Site | Tham số so | Hàng thay |
|---|---|---|---|---|
| C02 | Town12 | J9640 | G 19.50, LrefN 16.00, vN 3.75 | 30 |
| C03 | Town12 | J11697 | G 26.00, LrefN 36.84, vN 4.69 | 30 |
| C04 | Town12 | J18583 | G 15.50, LrefN 16.07, vN 5.86 | 30 |
| C06 | Town13 | J18550 | G 13.50, LrefN 20.56, vN 9.16 | 30 |
| C07 | Town13 | J6471 | G 11.50, LrefN 15.69, vN 11.44 | 30 |
| L02 | Town12 | J4766 | G 8.50, LrefN 15.50, vN 3.75 | 30 |
| L03 | Town13 | J13398 | G 8.50, LrefN 21.51, vN 4.69 | 30 |
| L05 | Town12 | J14694 | G 6.50, LrefN 21.00, vN 7.32 | 30 |
| L06 | Town13 | J2342 | G 5.50, LrefN 16.45, vN 9.16 | 30 |
| L07 | Town13 | J12491 | G 6.00, LrefN 31.18, vN 11.44 | 30 |
| L08 | Town12 | J5719 | G 5.00, LrefN 24.13, vN 14.31 | 30 |
| M01 | Town13 | J6331 | G 19.50, LrefN 12.25, vN 3.00 | 30 |
| M02 | Town13 | J10072 | G 83.00, LrefN 135.08, vN 3.75 | 30 |
| M03 | Town13 | J1621 | G 64.50, LrefN 127.53, vN 4.69 | 18 |
| M04 | Town11 | J2879 | G 15.00, LrefN 14.71, vN 5.86 | 30 |
| M05 | Town12 | J13895 | G 25.00, LrefN 57.69, vN 7.32 | 30 |
| M06 | Town12 | J13615 | G 36.00, LrefN 28.44, vN 2.40 | 30 |
| M07 | Town11 | J1038 | G 12.00, LrefN 13.82, vN 9.16 | 30 |
| M08 | Town12 | J15619 | G 45.00, LrefN 30.24, vN 1.92 | 30 |
| I01 | Town12 | R656,657,658 | gap 6.00, vE 6.00 | 30 |
| I02 | Town10HD | R18,19,20… | gap 7.80, vE 7.50 | 30 |
| I05 | Town12 | R390 | gap 4.62, vE 4.80 | 30 |
| I06 | Town12 | R390 | gap 2.73, vE 3.07 | 30 |
| I07 | Town13 | R779 | gap 3.55, vE 3.84 | 30 |
| I08 | Town13 | R228,241,345… | gap 22.28, vE 18.31 | 30 |
| O04 | Town13 | R634,856,1349 | G 32.95, vE 11.72 | 30 |
| O05 | Town12 | R143 | G 11.54, vE 4.80 | 30 |
| O06 | Town12 | R388 | G 6.83, vE 3.07 | 30 |
| O07 | Town12 | R143 | G 8.88, vE 3.84 | 30 |
| O08 | Town13 | R1432,1433 | G 55.69, vE 18.31 | 21 |

counts {'C/Town04': 1, 'C/Town05': 1, 'C/Town06': 1, 'C/Town12': 3, 'C/Town13': 2, 'I/Town06': 2, 'I/Town10HD': 1, 'I/Town12': 3, 'I/Town13': 2, 'L/Town04': 1, 'L/Town05': 1, 'L/Town12': 3, 'L/Town13': 3, 'M/Town11': 2, 'M/Town12': 3, 'M/Town13': 3, 'O/Town04': 1, 'O/Town05': 1, 'O/Town06': 1, 'O/Town12': 3, 'O/Town13': 2}

## Ghi chú

- 24 junction site cho C/L/M: 5 cảnh giữ lại và 19 cảnh mới. Cổng 23 junction chỉ cho phép hỏng tối đa 1 cảnh C/L/M mà không
  có cảnh thay; các cảnh thay lấy từ hàng (§5.4).
- Cảnh mới dồn về Town11, Town12 và Town13, vì luật chạy đà NPC 150 m trên một road chỉ thỏa ở các map lớn này.
- Map lớn cần spectator đặt tại cảnh (`M56_SPECTATOR=1`; smoke test Town12/13 ngày 08/11).
- I05, I06, I07 và O06, O07 có vE thấp (3,07–4,8 m/s). Các cảnh I ở vE thấp trước đây hỏng vì va chạm (I05, I07; lề TRIGGER).
  Tham số của slot giữ như đã đăng ký, nên rủi ro này vẫn còn.
