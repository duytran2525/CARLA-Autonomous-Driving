---
name: crfp-project
description: Bối cảnh, tầm nhìn và sổ quyết định (bảng Main) của dự án nghiên cứu CRFP — lái xe tự hành trong CARLA, NCKH UIT, nhắm ICCV 2027. Dùng skill này ngay đầu MỌI phiên làm việc trong repo CARLA-Funny-Moments hoặc bất kỳ worktree nào của nó, và mỗi khi câu chuyện chạm tới - các mục đánh số M (M21, M55, M56, M74…), Gate 1 / Gate 2, Tag-A/B/C/D, "bảng main", "sổ main", "ledger", "khung 3-4", 8 nguyên tắc / 5 idea, lõi (a) / lõi (b), ngưỡng, đăng ký trước, benchmark, backbone, venue, kill-search; câu hỏi kiểu "dự án đang ở đâu", "việc gì đang chờ", "đã quyết gì"; chuyển context / handoff sang phiên khác; và TRƯỚC KHI đọc, sửa hay ghi bất cứ điều gì vào docs/crfp/crfp-main-ledger.md. Cũng dùng khi sắp ghi lại một quyết định hay kết quả thí nghiệm của dự án, kể cả khi người dùng không nhắc tới sổ.
---

# Dự án CRFP: bối cảnh và sổ Main

Skill này cho bạn ba thứ: dự án đang nhắm tới đâu, cách lấy trạng thái hiện tại mà không tốn context, và cách sửa sổ mà không làm hỏng nó. Skill chỉ chứa những thứ ít đổi. **Trạng thái hiện tại không nằm ở đây mà nằm trong sổ** — đừng trả lời "dự án đang ở đâu" từ trí nhớ hay từ skill này.

Script trợ giúp nằm ở `scripts/ledger.py` trong thư mục của skill này (chỉ dùng thư viện chuẩn). Mọi lệnh bên dưới viết tắt là `ledger <lệnh>`, nghĩa là:

```bash
python -I -X utf8 <thư mục skill>/scripts/ledger.py <lệnh>
```

## Ba việc đầu tiên của một phiên

1. `ledger where` — in đường dẫn sổ và file 8 nguyên tắc. Nếu nó cảnh báo có hai bản sổ khác nội dung thì dừng và báo người dùng: sổ chỉ được có một nơi gốc.
2. `ledger brief` — in phần 1–3 của sổ (quy ước, bảng nhiệm vụ, điều kiện thắng SOTA), khoảng 230 dòng. Đọc xong là biết dự án đang ở bước nào, việc gì đang chạy, việc gì đang chờ ai.
3. Biết mình đang nói chuyện với ai trước khi ghi tên ai vào sổ (xem "Ai là ai").

Đọc thêm file 8 nguyên tắc + 5 idea khi việc của phiên đụng tới hướng nghiên cứu, claim, ngưỡng hoặc cách diễn giải kết quả. Việc thuần vận hành (chạy CARLA, sửa bug) thì phần tóm tắt dưới đây là đủ.

## Dự án này là gì

- **Đề tài:** hệ lái xe tự hành thế hệ mới, NCKH tại UIT, GVHD TS. Dương Việt Hằng.
- **Tầm nhìn (M76):** end-to-end từ cảm biến (camera/LiDAR) đến hành động lái, VLM sinh ý định, nhắm main track hội nghị hạng A* (ICCV 2027, M77). Mọi phần chưa làm là *hoãn*, không phải bỏ.
- **Đang ở Phase 1:** chứng minh hai lõi ý tưởng trên trạng thái đặc quyền trong CARLA, vì đó là cách rẻ nhất để biết ý tưởng có đứng được không trước khi dựng hệ cảm biến.
- **Lõi (a), idea 1:** ý định rời rạc có cấu trúc (dọc × ngang × macro), điều kiện theo mục tiêu = (đích, deadline), giữ qua nhiều bước. Phép so quyết định là D (ý định có cấu trúc) với C (núm vô hướng), cả hai cùng nhìn trước.
- **Lõi (b), idea 2 — CRFP:** học P(phản ứng của xe khác | ý định của ego) bằng can thiệp theo cặp (cùng cảnh, chỉ đổi ý định), xe khác có phản ứng thật, giám sát trực tiếp trên Δresponse.
- **Idea 3, 4, 5** (VLM sinh ý định; thiết kế teacher script → teacher VLM → student; confidence học từ sai số của chính model) là định hướng Phase 2, chưa có thí nghiệm.
- **Các cổng:** Gate 1 (M62) đọc hai lõi; Gate 1.5 (M68) kiểm việc giám sát Δresponse; Gate 2 (M116) so hệ hoàn chỉnh với SOTA. Trước mỗi đợt thí nghiệm có một lần đóng băng luật chơi: Tag-A (M52/M47), Tag-B (M63), Tag-C (M66), Tag-D (M117).
- **Ràng buộc tài nguyên (M78):** train trên UIT HPC H200, mỗi job tối đa 72 giờ, chỉ có lát MIG; CARLA chỉ chạy được trên một laptop RTX 3050 4 GB. Số liệu cụ thể xem hàng M78 vì có thể đổi.

## Tám nguyên tắc (bản rút gọn; bản đầy đủ là file nguyên tắc)

Đây là điểm đối chiếu cho mọi quyết định. Vi phạm chúng là loại lỗi dự án sợ nhất, vì nó làm kết quả mất giá trị trước reviewer.

1. Tầm nhìn là e2e từ cảm biến. Được bàn phương án lùi, không được tuyên bố bỏ.
2. Chỉ 5 idea là đóng góp khoa học; quyết định kỹ thuật (5 arm, cách làm M55…) không phải idea. Idea chưa có thí nghiệm thì chưa được ghi là đóng góp.
3. "Chưa ai làm" chỉ nghĩa là "chưa thấy trong tập đã đọc". Viết đúng phạm vi đó.
4. Giả thuyết khác tiền đề. "Idea mạnh hơn SOTA" là giả thuyết cho đến khi có số.
5. Hai AI đồng ý không phải bằng chứng. Bằng chứng chỉ đến từ dữ liệu, paper đã đọc, code đã kiểm. Điều này áp dụng cho cả nhận định của bạn: ghi nó là nhận định.
6. Không đổi ngưỡng sau khi thấy số. Ngoại lệ duy nhất là cổng thăm dò kiểu M21, và phải công khai là đặt sau khi thấy số. Ngưỡng đã vào Tag thì không có ngoại lệ.
7. Script được dùng trạng thái đặc quyền để sinh nhãn; teacher VLM, student và khâu đánh giá thì không. Thứ tự sinh bắt buộc: lý do trước, ý định sau.
8. Gate 1 chỉ trả lời đúng hai câu của M62. "Sống" nghĩa là tiền đề đứng được, không phải đã chứng minh xong.

## Ai là ai

- **Duy (Trần Đình Duy):** trưởng dự án. Quyết hướng đi, spec, ngưỡng, tiêu chí.
- **Dũng:** vận hành CARLA trên máy của mình, có quyền tự chủ vận hành do Duy cấp; không quyết ngưỡng hay hướng paper.
- **TS. Hằng:** GVHD; cùng Duy chốt venue, hướng paper.
- **Muse:** một AI khác, giữ sổ trước ngày 10/10/2026; nay đồng bộ từ bản trong repo.
- **Claude:** từ 10/10/2026 là đồng phụ trách cùng Duy và đồng giữ sổ.

Cả Duy và Dũng đều dùng máy này. Tài khoản git của máy là của Dũng, nên **không suy ra người đang chat từ git hay email**: một phiên từng ghi cả ngày quyết định của Duy dưới tên Dũng và phải sửa lại toàn bộ. Sổ gắn thẩm quyền theo tên, nên ghi sai tên là ghi sai việc quyết định có hợp lệ hay không. Chưa biết thì hỏi một lần, hoặc ghi "người dùng phiên này".

## Sổ nằm ở đâu, gồm những gì

Một file duy nhất: `docs/crfp/crfp-main-ledger.md` (dùng `ledger where` để lấy đường dẫn thật). File đi kèm: `docs/crfp/crfp-8-nguyen-tac-5-idea.md`. Chuyển context sang phiên khác chỉ cần hai file này cộng skill này.

| Phần | Nội dung | Loại |
|---|---|---|
| 1 | Quy ước | luật của sổ |
| 2 | Bảng nhiệm vụ: đã xong / hiện tại / tương lai | view, cập nhật tay |
| 3 | Điều kiện cần để thắng SOTA | view, cập nhật tay |
| 4 | Bảng Main: mỗi câu hỏi hoặc việc là một hàng, ID dạng M<số> | **nơi gốc** |
| 5 | Phụ lục A: điểm dừng / rẽ | nơi gốc cho M35a, M114 |
| 6 | Sổ vận hành: nhật ký theo ngày | lịch sử |

Trạng thái chỉ có một nơi gốc là cột Trạng thái của bảng Main. Phần 2 và 3 lặp lại nó cho dễ đọc; khi lệch thì bảng Main đúng.

## Đọc sổ sao cho rẻ

File đã trên 130 KB và sẽ còn lớn; mỗi hàng là một dòng dài tới vài nghìn ký tự. Đọc cả file bằng công cụ đọc file sẽ tốn hàng chục nghìn token và có thể bị cắt giữa chừng mà bạn không biết. Thay vào đó:

| Cần gì | Lệnh |
|---|---|
| Toàn cảnh, việc đang chờ | `ledger brief` |
| Nội dung đầy đủ của vài hàng | `ledger row M21 M30` |
| Lọc hàng | `ledger list --status "Mở" --pha 0` (thêm `--type Task`, `--text <từ khóa>`) |
| Chuyện gì vừa xảy ra | `ledger log 8` (thêm `--full` để không cắt) |
| Một quyết định cũ | tìm trong phần 6 theo ngày hoặc từ khóa bằng công cụ tìm kiếm, rồi đọc đúng dòng đó |

Handoff và trí nhớ của phiên trước thường chậm hơn repo vài version. Trước khi tin một câu "trạng thái hiện tại", đối chiếu với worktree thật (ví dụ log và commit của nhánh M21).

## Sửa sổ

Làm theo thứ tự này; mỗi bước có lý do của nó.

1. **Sửa bảng Main trước.** Tìm hàng bằng ID, sửa đúng ô cần sửa. Ô Trạng thái luôn bắt đầu bằng một trong: `Mở`, `Đang làm`, `Bị chặn`, `Đã trả lời chờ kiểm chứng`, `Đóng`, `Hoãn`, `Bỏ`; chi tiết viết sau, trong ngoặc hoặc sau dấu —. Script và bảng nhiệm vụ dựa vào từ khóa đầu ô này.
2. **Hàng mới** lấy số từ `ledger next-id`. Không bao giờ đánh số lại hay tái dùng ID: spec, commit và báo cáo ở các nhánh khác trích M-số. Đủ 12 ô; ô nào chưa có thì để trống hoặc `—`. Dấu `|` trong ô phải viết `\|`.
3. **Ghi một mục vào cuối phần 6** cho mọi thay đổi có nghĩa: ngày, ai quyết hoặc ai phát hiện, nội dung, và nguồn. Đánh dấu nguồn: `[repo]` nếu bạn đọc trực tiếp từ code/log/output; `[handoff]` nếu chỉ nghe từ tài liệu chuyển giao; ghi rõ "nhận định của Claude" nếu đó là suy luận. Sổ là thứ người khác sẽ dùng làm bằng chứng, nên người đọc phải phân biệt được ba loại này.
4. **Đồng bộ view:** chạy `ledger sync-views` để chép Pha / Bước / Trạng thái sang phần 2. Sau đó tự xem lại bằng mắt những thứ script không làm được: ghi chú và vị trí khối của hàng trong phần 2, ngày "cập nhật lần cuối", dòng "Vị trí hiện tại", bảng phần 3 và phụ lục A nếu thay đổi chạm tới chúng. Hàng mới phải được đặt tay vào đúng khối của phần 2.
5. **Kiểm:** `ledger check` phải in `OK`. Nó bắt lệch cột, ID trùng, ID được nhắc mà chưa có hàng, view lệch với bảng Main, và báo kích thước từng phần.
6. **Commit:** `git add -f docs/crfp/crfp-main-ledger.md` (cần `-f` vì `.gitignore` chặn `*.md`), rồi commit. Git là lịch sử của sổ: ai đổi đáp án, vì sao.

Những điều sổ không cho phép, kể cả khi người dùng phiên này nhờ:

- Đổi một ngưỡng hay tiêu chí đã khóa (M22a, M31a, mọi thứ đã vào Tag) sau khi đã thấy số. Việc được làm là ghi lại quyết định của Duy và công khai rằng nó đặt sau khi thấy số.
- Ghi đáp án vào một hàng khi chưa có dữ liệu, hoặc nâng "đã thiết kế" thành "đã có kết quả". Đóng một hàng không phải là có kết quả khoa học.
- Viết "chưa ai làm" mà không kèm phạm vi "trong tập đã đọc".

## Giữ cho sổ không phình

- Ô Trả lời dài 1–3 câu. Chi tiết dài, bảng số, biên bản phân tích thì để ở báo cáo hoặc script trong repo và ghi con trỏ (đường dẫn, commit) vào ô Bằng chứng. `ledger check` in năm ô dài nhất; nếu ô bạn vừa sửa lọt vào đó, hãy rút gọn.
- Các bộ quy tắc đăng ký trước đang nằm tạm trong ô (M56, M57, M22a, M52) sẽ chuyển sang tài liệu đóng băng khi Tag-A được tạo; đừng thêm quy tắc dài mới vào ô.
- Phần 6 chỉ nối thêm, không sửa mục cũ (sai thì viết mục đính chính). Khi `ledger check` cảnh báo nhật ký vượt nửa file, đề xuất với Duy chuyển các mục cũ sang một file lưu trữ bên cạnh; không tự làm, vì đó là thay đổi cấu trúc của nơi gốc.
- Ghi chú trong phần 2 chỉ một dòng. Phần 1–3 phải luôn đủ nhỏ để `ledger brief` còn rẻ.

## Ranh giới với các phiên khác

Nhiều phiên chạy song song trên cùng máy, mỗi phiên một worktree (M21, M55, M56…).

- Chỉ đọc code, log và output của phiên khác; không ghi vào namespace output của họ (một người ghi cho mỗi namespace). Muốn họ làm gì thì nói với người dùng.
- Không đụng vào code, config, catalog, seed, ngưỡng đã đóng băng của một thí nghiệm nếu chưa có phê duyệt tạo version mới.
- Đọc `AGENTS.md` ở gốc checkout chính trước mọi việc liên quan tới HPC: các lát MIG hiện bị chặn cho CARLA và không được tự suy ra quyền.
- Hai phiên không sửa sổ cùng lúc. Trước khi sửa, xem `git log -3 -- docs/crfp/crfp-main-ledger.md` và `ledger where` để chắc bạn đang ở bản mới nhất.

## Hai bài học đã trả giá

- **So một điểm ước lượng với khoảng tin cậy của một lần đo khác là cái bẫy.** Kết luận "phiên 2 nhiễu hơn phiên 1 (26 cao / 1 thấp)" hóa ra là do khoảng tin cậy bị lệch; đổi vai hai phiên vẫn ra cùng hướng. Trước khi tin một khác biệt, thử phép so đối xứng và kiểm xem điểm ước lượng có nằm trong khoảng của chính nó không (hàng M74, mục E).
- **Một kết quả đẹp ở cổng thăm dò không phải bằng chứng cho bài.** M21 chỉ là go/no-go; số 1b cũ không được dùng để khóa giá trị. Khi báo cáo, nói rõ kết quả thuộc loại nào.
