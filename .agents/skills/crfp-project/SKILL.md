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

Skill này có hai bản: nguồn ở `.agents/skills/crfp-project/` trong repo, bản cài ở `~/.claude/skills/crfp-project/`. Sửa thì sửa bản nguồn rồi chép đè sang bản cài.

## Ba việc đầu tiên của một phiên

1. `ledger where` — in đường dẫn sổ, commit gần nhất của sổ, sổ có đang sửa dở không, và danh sách worktree. Nếu nó cảnh báo một bản khác chứa nội dung mà nơi gốc không có thì dừng và báo người dùng: sổ chỉ được có một nơi gốc.
2. `ledger brief` — in phần 1–3 của sổ (quy ước, bảng nhiệm vụ, điều kiện thắng SOTA), khoảng 27 KB. Đọc xong là biết dự án đang ở bước nào, việc gì đang chạy, việc gì đang chờ ai.
3. Biết mình đang nói chuyện với ai trước khi ghi tên ai vào sổ hoặc làm việc cần thẩm quyền của người đó (xem "Ai là ai"). Phiên chỉ đọc thì không cần hỏi, chỉ cần đừng giả định.

Đọc thêm file 8 nguyên tắc + 5 idea khi việc của phiên đụng tới hướng nghiên cứu, claim, ngưỡng hoặc cách diễn giải kết quả. Việc thuần vận hành (chạy CARLA, sửa bug) thì phần tóm tắt dưới đây là đủ. File nguyên tắc có thể chậm hơn sổ về trạng thái (ví dụ còn ghi "cần tạo M76"); về trạng thái thì sổ đúng.

**Sổ có thể chậm hơn repo.** Các phiên M21, M56 commit liên tục, còn sổ chỉ được cập nhật khi có người ghi. Trước khi trả lời "đang ở đâu" về một việc đang chạy, lấy đường dẫn worktree của nó từ `ledger where` rồi xem `git -C <worktree> log -3 --format="%h %ad %s"`. Thấy sổ cũ hơn: phiên chỉ đọc thì nói rõ điều đó trong câu trả lời; phiên được sửa sổ thì cập nhật hàng đó với nguồn `[repo]`.

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

Một file duy nhất: `docs/crfp/crfp-main-ledger.md` **ở checkout chính của repo, trên nhánh `main`** (dùng `ledger where` để lấy đường dẫn thật). Đi kèm trong cùng thư mục: `crfp-8-nguyen-tac-5-idea.md` và `details/<ID>.md` (chi tiết dài của từng hàng). Chuyển context sang phiên khác cần cả thư mục `docs/crfp/` cộng skill này.

Mỗi worktree có thể có một bản sổ được git checkout ra theo nhánh của nó. Các bản đó chỉ là ảnh chụp, thường cũ hơn; đừng đọc trạng thái từ chúng và đừng sửa chúng. Đọc và sửa luôn đi qua đường dẫn mà `ledger where` in ra, rồi commit trên `main` của checkout chính (`git -C <checkout chính> …`). Một file vật lý duy nhất thì không thể có hai bản lệch nhau.

Ngoài máy này (ví dụ workspace của Muse) không có repo: đặt biến môi trường `CRFP_LEDGER` trỏ tới file sổ rồi dùng script như bình thường (PowerShell: `$env:CRFP_LEDGER = '<đường dẫn>'`; bash: `export CRFP_LEDGER=<đường dẫn>`). Ở chế độ này script không kiểm được bản khác hay trạng thái git, nên người dùng phải tự bảo đảm đó là bản mới nhất.

| Phần | Nội dung | Loại |
|---|---|---|
| 1 | Quy ước và chú giải thuật ngữ (1a, 1b, các arm, boot, segment…) | luật của sổ |
| 2 | Bảng nhiệm vụ: đã xong / hiện tại / tương lai; mục Lịch theo tuần | view, cập nhật tay |
| 3 | Điều kiện cần để thắng SOTA | view, cập nhật tay |
| 4 | Bảng Main: mỗi câu hỏi hoặc việc là một hàng, ID dạng M<số> | **nơi gốc** |
| 5 | Phụ lục: A điểm dừng / rẽ · B checklist Tag-A · C các lần chạy thí nghiệm · D tài liệu ngoài sổ | nơi gốc cho M35a, M114, M52 |
| 6 | Sổ vận hành: nhật ký theo ngày | lịch sử |

Trạng thái chỉ có một nơi gốc là cột Trạng thái của bảng Main. Phần 2 và 3 lặp lại nó cho dễ đọc; khi lệch thì bảng Main đúng.

## Đọc sổ sao cho rẻ

File đã trên 130 KB và sẽ còn lớn; mỗi hàng là một dòng dài tới vài nghìn ký tự. Đọc cả file bằng công cụ đọc file sẽ tốn hàng chục nghìn token và có thể bị cắt giữa chừng mà bạn không biết. Thay vào đó:

| Cần gì | Lệnh |
|---|---|
| Toàn cảnh, việc đang chờ | `ledger brief` |
| Nội dung đầy đủ của vài hàng | `ledger row M21 M30`; nếu ô Trả lời ghi `details/<ID>.md` thì chi tiết nằm ở file đó |
| Checklist Tag-A, các lần chạy, tài liệu nào chưa có trong repo | `ledger section 5` |
| Lọc hàng | `ledger list --status "Mở" --pha 0` (thêm `--type Task`, `--text <từ khóa>`) |
| Việc gì bị chặn, bởi cái gì | `ledger list --status "Bị chặn" --wide` (in cả ô trạng thái đầy đủ, phụ thuộc, người quyết, hạn), cộng khối B3 trong `brief` |
| Mọi hàng nhắc tới một ID | `ledger list --text M30` |
| Chuyện gì vừa xảy ra | `ledger log 8` (thêm `--full` để không cắt) |
| Một quyết định cũ | tìm trong phần 6 theo ngày hoặc từ khóa bằng công cụ tìm kiếm, rồi đọc đúng dòng đó |

Hai điều cần biết khi tìm thứ đang bị chặn:

- `Mở` nghĩa là bắt đầu được ngay (kể cả khi chưa đóng được vì còn chờ một đáp án khác). Việc chưa bắt đầu được thì ghi `Bị chặn (bởi …)`.
- Cột Phụ thuộc vẫn có thể thiếu: một số phụ thuộc chỉ được viết bằng lời trong ô Trả lời. Trước khi quyết định hay đóng một hàng, chạy `ledger list --text <ID>` để thấy những hàng khác đang chờ nó hoặc nó đang chờ.

Tiêu chí đạt/rớt của một cổng nằm ở hàng định nghĩa metric và quy tắc (M22a, M31a, M35a) và ở spec của thí nghiệm trong worktree của nó, không nằm ở hàng của thí nghiệm. Khi ai đó nói "X đạt rồi", hỏi theo tiêu chí nào và file kết quả ở đâu.

Handoff và trí nhớ của phiên trước thường chậm hơn repo vài version; xem "Sổ có thể chậm hơn repo" ở trên.

## Sửa sổ

Làm theo thứ tự này; mỗi bước có lý do của nó.

1. **Sửa bảng Main trước, bằng script.** `ledger set <ID> <ô> "<nội dung>"` thay một ô; `ledger add <ID> <ô> "<nội dung>"` nối thêm vào cuối ô. Tên ô: `question source status answer evidence deps pha buoc owner han type`. Script tự escape dấu `|`, giữ nguyên kiểu xuống dòng của file và từ chối trạng thái sai từ khóa. Dùng script thay vì công cụ sửa file, vì mỗi hàng là một dòng dài vài nghìn ký tự và rất dễ sửa nhầm chỗ.
   - Ô Trạng thái luôn bắt đầu bằng một từ khóa, chi tiết viết sau trong ngoặc hoặc sau dấu —:

     | Từ khóa | Nghĩa |
     |---|---|
     | `Mở` | chưa có đáp án và bắt đầu được ngay |
     | `Đang làm` | đã có người nhận và đã bắt đầu; nếu mới giao mà chưa chạy thì ghi rõ trong ngoặc |
     | `Bị chặn (bởi …)` | chưa bắt đầu hoặc không làm tiếp được cho tới khi việc khác xong; ghi ID của việc đó trong ngoặc và trong ô `deps` |
     | `Đã trả lời chờ kiểm chứng` | có đáp án hoặc thiết kế, nhưng chưa có dữ liệu hay văn bản xác nhận |
     | `Đóng` | đã quyết bởi người có thẩm quyền, hoặc đã có kết quả đã được kiểm |
     | `Hoãn (điều kiện mở lại)` | chủ động để sau |
     | `Bỏ` | không làm nữa |

   - "Đạt" và "rớt" không phải trạng thái. Kết quả của một thí nghiệm ghi vào ô Trả lời (đúng con số, theo đúng tiêu chí đã đặt trước), nguồn vào ô Bằng chứng.
   - Ô `owner` ghi người quyết, thêm người làm nếu khác ("Duy; Claude chạy"). Ô `han` là mốc phải xong việc. Ngân sách, cấu hình và các chi tiết của một quyết định ghi vào ô Trả lời.
2. **Hàng mới** lấy số từ `ledger next-id`. Không bao giờ đánh số lại hay tái dùng ID: spec, commit và báo cáo ở các nhánh khác trích M-số. Hàng mới là một dòng đủ 12 ô thêm vào cuối bảng Main; ô nào chưa có thì để trống hoặc `—`.
3. **Ghi một mục vào sổ vận hành** cho mọi thay đổi có nghĩa: `ledger log-add "<ngày> — <ai quyết hoặc ai phát hiện>: <nội dung>. Nguồn: …"`. Ngày là ngày thật theo đồng hồ máy; nếu người dùng nêu một ngày khác thì ghi cả hai. Luôn nói rõ nguồn thuộc loại nào, vì sổ là thứ người khác dùng làm bằng chứng:
   - `[repo]`: bạn đọc trực tiếp từ code, log, output.
   - `[chat]`: người có tên nói trong chat ("Duy quyết trong chat"). Nếu là lời thuật lại của người thứ ba ("Duy thuật lại lời TS. Hằng") thì ghi đúng như vậy và nói bạn chưa thấy nguyên văn.
   - `[handoff]`: chỉ có trong tài liệu chuyển giao, chưa kiểm từ nguồn gốc.
   - "nhận định của Claude": suy luận của bạn.

   Một yêu cầu bị từ chối vì trái luật (ví dụ đề nghị nới ngưỡng sau khi thấy số) cũng đáng một mục: ai đề nghị, đề nghị gì, vì sao không làm.
4. **Đồng bộ view:** chạy `ledger sync-views` để chép Pha / Bước / Trạng thái sang phần 2. Sau đó tự xem lại bằng mắt những thứ script không làm được:
   - Khối của hàng trong phần 2 theo trạng thái mới: `Đóng`, `Đã trả lời chờ kiểm chứng` và `Bỏ` thuộc khối A; `Đang làm` thuộc B1; `Mở` thuộc B2; `Bị chặn` bởi một việc đang chạy thuộc B3; `Bị chặn` trên đường tới Gate 1 thuộc C theo Bước; `Hoãn` theo pha ở D. Đổi khối thì chuyển cả dòng. Hàng mới phải được đặt tay vào đúng khối.
   - Ghi chú một dòng của hàng, dòng "Vị trí hiện tại", mục Lịch, bảng phần 3 và các phụ lục nếu thay đổi chạm tới chúng. Hai phụ lục dễ bị quên: B (một mục của Tag-A đổi tình trạng) và C (có lần chạy CARLA mới, hoặc một lần chạy bị thay thế).
   - Ngày "cập nhật lần cuối" của view: chỉ sửa một vài dòng thì ghi kiểu "11/10/2026 (chỉ M37, M81; phần còn lại như 10/10)".
5. **Kiểm:** `ledger check` phải in `OK`. Nó bắt lệch cột, ID trùng, ID được nhắc mà chưa có hàng, view lệch với bảng Main, và báo kích thước từng phần. `OK` chỉ nói về cấu trúc; khối, ghi chú và ngày của view vẫn do bạn chịu trách nhiệm.
6. **Commit trên `main` của checkout chính:** `git -C <checkout chính> add -f docs/crfp/crfp-main-ledger.md` (cần `-f` vì `.gitignore` chặn `*.md`), rồi commit. Chỉ add đúng file sổ; checkout chính có nhiều file chưa theo dõi của người khác. Git là lịch sử của sổ: ai đổi đáp án, vì sao.

Những điều sổ không cho phép, kể cả khi người dùng phiên này nhờ:

- Đổi một ngưỡng hay tiêu chí sau khi đã thấy số liên quan tới nó. "Số liên quan" gồm cả kết quả của một thí nghiệm khác dùng cùng agent và cùng loại cảnh: thấy kết quả M21 rồi nới quy tắc của 1b vẫn là đổi sau khi thấy số. Cụ thể:
  - Ngưỡng đã vào Tag: không ai được đổi, kể cả Duy. Từ chối, nêu nguyên tắc 6.
  - Quy tắc đã duyệt nhưng chưa vào Tag (M22a, M31a hiện nay): sửa trước khi có số liên quan là việc soạn thảo bình thường. Sau khi có số, chỉ còn ngoại lệ của nguyên tắc 6: cổng thăm dò và ngưỡng cũ sai một cách khách quan (ví dụ dung sai 1 micromet cho một chiếc xe đang lắng). "Hơi chặt" không phải sai khách quan.
  - Nếu Duy (đã xác nhận danh tính) vẫn quyết đổi theo ngoại lệ đó: giữ nguyên văn quy tắc cũ trong ô, viết quy tắc mới bên cạnh kèm câu "đặt sau khi thấy số, ngày …, lý do …", ghi mục sổ vận hành, và từ đó báo cáo kết quả theo cả hai quy tắc. Không bao giờ sửa lặng lẽ.
- Làm một việc cần thẩm quyền của Duy (ngưỡng, hướng đi, chọn loại agent, phạm vi claim) khi chưa biết người đang chat là ai. Ghi "người dùng phiên này" chỉ dùng được cho việc không cần thẩm quyền.
- Ghi đáp án vào một hàng khi chưa có dữ liệu, hoặc nâng "đã thiết kế" thành "đã có kết quả". Đóng một hàng không phải là có kết quả khoa học.
- Viết "chưa ai làm" mà không kèm phạm vi "trong tập đã đọc".

## Giữ cho sổ không phình

- Ô Trả lời là tóm tắt vài câu. Chi tiết dài, bảng số, biên bản phân tích, nguyên văn bộ quy tắc thì ghi vào `docs/crfp/details/<ID>.md` (nối vào cuối file, kèm ngày và nguồn) và để con trỏ `details/<ID>.md` trong ô; script và báo cáo thì ghi đường dẫn vào ô Bằng chứng. Nhớ `git add -f` cả file chi tiết.
- Một hàng không gánh hai việc ở hai thời điểm (ví dụ "khóa giao thức trước thí nghiệm" và "chạy pilot sau thí nghiệm"): tách thành hai hàng, nếu không cột Phụ thuộc sẽ thành vòng. `ledger check` in năm ô dài nhất; nếu ô bạn vừa sửa lọt vào đó, hãy rút gọn.
- Nguyên văn các bộ quy tắc đăng ký trước (M56, M57, M22a, M52) nằm ở `details/`; khi Tag-A được tạo chúng thành tài liệu đóng băng. Sửa một quy tắc thì sửa ở file chi tiết VÀ sửa tóm tắt trong ô cho khớp.
- Phần 6 chỉ nối thêm, không sửa mục cũ (sai thì viết mục đính chính). Khi `ledger check` cảnh báo nhật ký vượt nửa file, đề xuất với Duy chuyển các mục cũ sang một file lưu trữ bên cạnh; không tự làm, vì đó là thay đổi cấu trúc của nơi gốc.
- Ghi chú trong phần 2 chỉ một dòng. Phần 1–3 phải luôn đủ nhỏ để `ledger brief` còn rẻ.

## Ranh giới với các phiên khác

Nhiều phiên chạy song song trên cùng máy, mỗi phiên một worktree (M21, M55, M56…).

- Chỉ đọc code, log và output của phiên khác; không ghi vào namespace output của họ (một người ghi cho mỗi namespace). Muốn họ làm gì thì nói với người dùng.
- Không đụng vào code, config, catalog, seed, ngưỡng đã đóng băng của một thí nghiệm nếu chưa có phê duyệt tạo version mới.
- Đọc `AGENTS.md` ở gốc checkout chính trước mọi việc liên quan tới HPC: các lát MIG hiện bị chặn cho CARLA và không được tự suy ra quyền.
- Khi bàn giao một việc cho agent hoặc người khác: chép nguyên văn quy tắc đang hiệu lực (ô trong sổ và `details/<ID>.md`) vào bản bàn giao, ghi commit của sổ lúc chép, và yêu cầu bên nhận liệt kê lại các yêu cầu họ hiểu; đối chiếu danh sách đó với quy tắc trước khi cho làm. Ở M56, điều khoản "lấy cảnh từ nguồn ngoài" đã rơi mất đúng ở khâu này và bốn ngày sau mới lộ ra.
- Hai phiên không sửa sổ cùng lúc. Trước khi sửa, xem `git log -3 -- docs/crfp/crfp-main-ledger.md` và `ledger where` để chắc bạn đang ở bản mới nhất.

## Hai bài học đã trả giá

- **So một điểm ước lượng với khoảng tin cậy của một lần đo khác là cái bẫy.** Kết luận "phiên 2 nhiễu hơn phiên 1 (26 cao / 1 thấp)" hóa ra là do khoảng tin cậy bị lệch; đổi vai hai phiên vẫn ra cùng hướng. Trước khi tin một khác biệt, thử phép so đối xứng và kiểm xem điểm ước lượng có nằm trong khoảng của chính nó không (hàng M74, mục E).
- **Một kết quả đẹp ở cổng thăm dò không phải bằng chứng cho bài.** M21 chỉ là go/no-go; số 1b cũ không được dùng để khóa giá trị. Khi báo cáo, nói rõ kết quả thuộc loại nào.
