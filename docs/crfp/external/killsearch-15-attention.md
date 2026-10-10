# KILL-SEARCH 15 — Attention theo ý định vs. literature top-down / task-driven attention

Ngày: 2026-10-08. Người thực hiện: Muse (subagent).
Câu hỏi kill: CRFP dùng **ý định hiện tại của xe ego** (discrete intent đang thực thi, vd. "đang vượt") để **điều khiển attention** — quyết định chú ý vào vùng/vật thể nào trong cảnh. Literature về top-down attention và task-driven attention đã làm điều này chưa?

Phương pháp: search 6 góc truy vấn, đọc full 2 paper qua ar5iv (SCOUT, Cultrera-attention), đọc abstract + section liên quan của 4 paper nữa, đối chiếu arXiv ID/venue/năm từ nguồn chính.

---

## 1. Paper đã đọc sâu

### 1.1. arXiv:2310.09275 — SCOUT (đọc FULL qua ar5iv)
- **Tác giả:** Iuliia Kotseruba, John K. Tsotsos (York University).
- **Venue/năm:** arXiv preprint cs.CV, Oct 2023. Không thấy journal/conference ref trên trang arXiv.
- **Nội dung liên quan:** Đề xuất mô hình SCOUT "modulates drivers' gaze prediction with explicit action and context information". Kiến trúc (Sec V-A, Fig 3): hai encoder (visual = Video Swin Transformer; task/context = text labels + numeric features), các khối multi-head attention (MHA) modulation, rồi decoder. Task labels gồm lateral actions (drive straight, turn right/left, lane change left/right) và longitudinal actions (maintain, accelerate, decelerate, stopped); context = loại giao lộ + quyền ưu tiên. Table V cho thấy thêm task info (CA = current action; GC/LC = global/local context) cải thiện KLD/NSS so với bản không task.
- **Liên quan đến kill-question:** CÓ cơ chế "action hiện tại điều biến attention". NHƯNG: (a) task ở đây là **dự đoán gaze của người lái** (human gaze prediction), không phải attention của hệ thống tự lái để ra quyết định; (b) action là nhãn quan sát được của tài xế người, không phải discrete intent do hệ thống tự chọn và thực thi; (c) không có ước lượng counterfactual response nào.

### 1.2. arXiv:2006.03347 — Cultrera et al., "Explaining Autonomous Driving by Learning End-to-End Visual Attention" (đọc FULL qua ar5iv)
- **Tác giả:** Luca Cultrera, Lorenzo Seidenari, Federico Becattini, Pietro Pala, Alberto Del Bimbo (Univ. of Florence).
- **Venue/năm:** arXiv preprint cs.CV, Jun 2020. Trang arXiv không ghi venue bình duyệt.
- **Nội dung liên quan (OVERLAP MẠNH NHẤT):** Sec 3.2 + Fig 2: mô hình conditional imitation learning với **separate attention layers trained for each high-level command** — mỗi command (Follow Lane, Go straight, Turn Left, Turn Right) có một attention head riêng học cách "focus on different regions" của ảnh; command chọn head nào xử lý. Sec 1: "each branch learns to perform a specialized attention, looking at what is relevant for the goal at hand."
- **Điểm khác với CRFP:** (a) "command" là **lệnh điều hướng mức route** (rẽ trái ở ngã tư sắp tới), không phải discrete intent đang thực thi (vd. "đang vượt"); (b) attention phục vụ **dự đoán góc lái + giải thích được** (explainability), không phục vụ ước lượng phản ứng counterfactual của môi trường; (c) cơ chế là **chọn nhánh cứng** theo command (kiểu CIL), không phải điều biến mềm một attention chung bằng intent hiện tại.

### 1.3. HammerDrive — Amadori, Fischer, Demiris, IEEE T-ITS vol. 23(6), 2022
- **Venue/năm:** IEEE Transactions on Intelligent Transportation Systems, 2022 (DOI 10.1109/TITS.2021.3055120).
- **Nội dung liên quan:** "Task-aware driving visual attention": mạng phân cấp gồm các cặp forward-inverse model **nhận diện maneuver** từ telemetry (>90% accuracy), rồi dùng maneuver đó để **gán trọng số cho các saliency predictor** được train riêng cho từng task. (Đọc qua TRID tóm tắt + mô tả trong Sec II của 2310.09275.)
- **Điểm khác:** vẫn là **dự đoán gaze người lái** (driver monitoring), không phải attention của AV; maneuver được *nhận diện* từ dữ liệu xe, không phải intent do hệ thống *chủ động thực thi*.

### 1.4. arXiv:2005.02545 — MHA-JAM (đọc abstract + Sec F)
- **Venue/năm:** bản "revised submission for RA-L" (IEEE Robotics and Automation Letters), 2020.
- **Nội dung liên quan:** multi-head attention trên joint agent-map representation; **mỗi head sinh một quỹ đạo tương lai** (mỗi mode = một intent), và "attention maps focus on specific surrounding agents and scene features depending on the future possible trajectory" (vd. head rẽ trái chú ý xe làn đối diện). Câu trong abstract: "The agent's intent also informs what part of the scene and agent configuration is relevant."
- **Điểm khác:** intent ở đây là **các mode tương lai của agent khác** (multi-modal prediction), không phải intent hiện tại của ego; mục đích là dự đoán quỹ đạo, không phải ước lượng response counterfactual theo action của ego.

### 1.5. arXiv:1710.02410 — Codevilla et al., Conditional Imitation Learning, ICRA 2018
- **Nội dung liên quan:** branched architecture — high-level command (navigational) chọn nhánh policy. Không có attention. Ghi nhận làm baseline khái niệm "condition theo command".

### 1.6. Literature counterfactual (đọc abstract/summary)
- NVIDIA IROS 2023 "Interpretable Trajectory Prediction via Counterfactual Responsibility": counterfactual reasoning cho prediction, không kết hợp intent-conditioned attention.
- Frontiers in Future Transportation 2026 (review): "interaction-conditioned ego-vehicle planning... central technical difficulty is counterfactual prediction: the planner must estimate how another vehicle would react to each candidate ego action." — xác nhận ước lượng P(response | ego action) là bài toán mở, **không paper nào trong review dùng intent-conditioned attention để giải nó**.

---

## 2. Overlap mạnh nhất

**arXiv:2006.03347, Sec 3.2 + Figure 2.** Đây là paper duy nhất trong tập đã đọc mà **attention weights phụ thuộc vào command/intent**: mỗi high-level command có attention layer riêng, command chọn head nào "nhìn" vào vùng nào của ảnh.

Trích ý (paraphrase, Sec 3.2): các attention layer riêng được train cho từng high-level command để tập trung vào các vùng khác nhau và cho ra góc lái phù hợp.

**Vì sao chưa KILL được CRFP:**
1. **"Intent" khác loại:** command của họ là lệnh điều hướng tĩnh theo route (sắp rẽ trái ở ngã tư), còn intent của CRFP là maneuver rời rạc **đang được thực thi ngay lúc đó** (đang vượt / đang nhường) — biến can thiệp (intervention variable) cho ước lượng counterfactual, không phải chỉ dẫn đường.
2. **Mục đích khác:** attention của họ phục vụ **điều khiển + giải thích** (steering angle, interpretability). Attention của CRFP phục vụ **ước lượng P(phản ứng môi trường | hành động ego)** — không paper nào làm.
3. **Cơ chế khác:** họ là hard branch selection (mỗi command một head riêng, kiểu CIL); CRFP là intent hiện tại điều biến attention chung.
4. **Đối tượng attention khác:** họ attend trên RoI ảnh để lái; CRFP attend trên các thực thể/vùng cảnh để suy phản ứng của agent khác.

Các paper gaze (SCOUT, HammerDrive) còn xa hơn: chúng dự đoán **mắt người nhìn đâu**, không phải attention của máy để ra quyết định.

---

## 3. Trả lời 3 câu hỏi trọng tâm

**(a) Có paper nào dùng intent/maneuver để điều khiển attention weights không?**
Có — 2006.03347 (per-command attention heads), SCOUT (action-modulated gaze), HammerDrive (maneuver-weighted saliency), MHA-JAM (per-intent attention heads cho prediction). Nhưng **không paper nào** dùng intent hiện tại của ego để điều khiển attention **nhằm ước lượng counterfactual response**.

**(b) Top-down attention trong driving khác gì "attention theo ý định" của CRFP?**
Top-down attention trong literature driving = mô hình **gaze người lái** bị điều biến bởi task (SCOUT, HammerDrive, MEDIRL). Nó trả lời "tài xế nhìn đâu khi đang làm gì". CRFP là attention của **hệ thống máy** trên các thực thể cảnh, có điều kiện trên intent mà chính nó đang thực thi, để trả lời "môi trường sẽ phản ứng thế nào nếu tôi làm X". Khác task, khác chủ thể, khác output.

**(c) Task-driven attention có bao gồm driving intent không?**
Có ở mức từ ngữ ("task" = maneuver đang thực hiện trong SCOUT/HammerDrive), nhưng "task-driven" đó dừng ở **dự đoán gaze**. Chưa ai đưa driving intent vào attention của **pipeline ra quyết định / ước lượng response**.

---

## 4. Khung đánh giá: vấn đề gì mà các cách trước chưa làm được?

Các cách trước dùng intent/command-conditioned attention để:
- (i) dự đoán mắt người nhìn đâu (SCOUT, HammerDrive), hoặc
- (ii) lái xe + giải thích được (2006.03347), hoặc
- (iii) dự đoán đa mode quỹ đạo của agent khác (MHA-JAM).

**Chưa cách nào** dùng attention có điều kiện trên intent để **cấu trúc bài toán ước lượng counterfactual** — tức là, khi ego cân nhắc "nếu tôi vượt thì xe kia phản ứng ra sao", attention phải dồn vào đúng các thực thể/vùng mà intent "vượt" làm cho trở nên liên quan, và sự phân bổ attention đó phải thay đổi theo từng intent được xét. Literature hoặc cố định attention theo task hiện tại (gaze), hoặc chọn nhánh theo lệnh đường (CIL-style), chứ không có vòng "intent đang xét → attention → ước lượng response có điều kiện trên intent đó".

---

## 5. Verdict: **WEAKEN** (không KILL, không ALIVE)

**Lý do:** Cơ chế "attention phụ thuộc maneuver/command" **đã tồn tại** — mạnh nhất là 2006.03347 (Sec 3.2, Fig 2: separate attention layers per high-level command). Nếu CRFP phát biểu luận điểm ở mức "dùng intent để điều khiển attention" một cách chung chung, luận điểm đó **không mới** và reviewer sẽ chỉ ra paper này.

**Tuy nhiên chưa bị KILL vì:** chưa ai làm **intent-conditioned attention phục vụ ước lượng counterfactual response P(response | ego action)**. Mọi overlap đều lệch ở ít nhất một trong ba trục: loại intent (lệnh đường vs maneuver đang thực thi), mục đích (gaze/lái vs ước lượng response), cơ chế (chọn nhánh cứng vs điều biến).

**Hành động bắt buộc để giữ luận điểm:**
1. **Cite-and-distinguish 2006.03347** ngay trong related work — đây là paper reviewer khó tính sẽ nêu đầu tiên. Phải nói rõ: command của họ là navigational, attention của họ phục vụ steering/explainability; intent của CRFP là executable discrete maneuver, attention phục vụ response estimation.
2. Phát biểu luận điểm ở mức **kết hợp** (intent-conditioned attention *cho* counterfactual response modeling), không ở mức cơ chế attention đơn lẻ.
3. Cite SCOUT/HammerDrive ở mục "top-down attention trong driving là gaze prediction, khác task".

**Độ tin cậy của verdict:** đã đọc full 2 paper gần nhất (SCOUT, 2006.03347) qua ar5iv, kiểm arXiv ID/venue/năm từ trang arXiv chính; 4 paper còn lại đọc abstract + section liên quan. Không search lướt.
