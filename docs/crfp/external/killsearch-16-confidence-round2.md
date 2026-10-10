# KILL-SEARCH 16 — ROUND 2: Đào sâu thêm paper ngoài đợt 1

**Ngày:** 08/10/2026
**Mục tiêu:** Tìm paper MỚI ngoài 8 paper đợt 1 (Retrieve-then-Steer, DRO-EDL-MPC, PU-RRT, RUDC-T, Nitsch, Farid, CBR-LLM, DiLu). Đặc biệt tìm: (a) paper nào ĐO CALIBRATION cho confidence trong driving? (b) paper nào kết hợp "experience similarity + confidence + driving" mà đợt 1 sót? (c) baseline uncertainty nào cho driving mà CRFP bắt buộc phải so?

**Verdict đợt 1:** WEAKEN (Retrieve-then-Steer là overlap mạnh nhất nhưng thiếu calibration + không phải driving)

---

## 1. Paper MỚI đã đọc sâu

### 1.1 CARIL — Confidence-Aware Regression in Imitation Learning (arXiv:2503.00783) ⭐ ĐỌC FULL

**Tác giả:** Delavari, Khalil, Kwon (Univ. of Michigan-Dearborn). **Venue:** Submitted to IEEE. **Năm:** 2025.

**Nội dung:** Dual-head architecture cho imitation learning lái xe: regression head dự đoán steering liên tục, classification head ước lượng confidence qua phân phối xác suất trên các steering bin rời rạc. Ba yếu tố đánh giá độ tin cậy: max probability, entropy, và regression-classification alignment. Khi confidence thấp → cơ chế correction điều chỉnh action. Đánh giá closed-loop trong CARLA (Town04), giảm lane deviation tới 50%.

**Kiểm tra 2 câu hỏi then chốt:**
- Confidence từ experience similarity? **KHÔNG.** Confidence từ softmax của classification head — là model output uncertainty, không phải so sánh với kinh nghiệm quá khứ.
- Đo calibration (ECE/reliability)? **KHÔNG.** Metrics: classification accuracy/precision/recall/F1, Fréchet distance, DTW, ABC, curve length. Không có reliability diagram hay ECE.

**Đánh giá:** Liên quan (confidence trong driving IL, closed-loop CARLA) nhưng KHÔNG đe dọa claim cốt lõi của CRFP. Thực ra CỦNG CỐ gap: chứng minh confidence hữu ích trong driving nhưng không ai làm experience-based confidence hay calibration — đúng 2 điểm CRFP tuyên bố làm.

### 1.2 KEPT — Knowledge-Enhanced Prediction of Trajectories (arXiv:2509.02966)

**Tác giả:** Wang et al. (Tongji Univ. + UT Austin + Tsinghua). **Năm:** 2025. Preprint under review.

**Nội dung:** Retrieval-augmented VLM cho trajectory prediction. TFSF video encoder (self-supervised) + k-means/HNSW retrieval stack lấy scene exemplars, nhúng vào CoT prompts. SOTA trên nuScenes open-loop (0.70m L2, 0.21% collision).

**Kiểm tra:** Có tính confidence từ similarity? **KHÔNG.** Retrieval chỉ dùng để cung cấp exemplars cho prompt, không có confidence score nào được tính từ độ tương đồng. Không calibration.

**Đánh giá:** Retrieval cho driving nhưng không có confidence. Không đe dọa.

### 1.3 LiLoDriver — Lifelong Learning for Closed-loop Motion Planning (arXiv:2505.17209)

**Tác giả:** Yao et al. (Horizon Robotics). **Năm:** 2025.

**Nội dung:** Memory bank lưu long-tail scenario clusters + few-shot planner experiences. LLM chọn behavior planner dựa trên retrieved experiences. Đánh giá closed-loop trên nuPlan (Test14-Hard).

**Kiểm tra:** Có confidence? **KHÔNG.** Có calibration? **KHÔNG.** Memory dùng để chọn planner, không để tính độ tự tin.

**Đánh giá:** Memory-based driving nhưng không có confidence. Không đe dọa.

### 1.4 DriveVLA-M0 — Failure-Aware Memory Augmentation (arXiv:2608.10413)

**Nội dung:** Retrieval-augmented VLA với latent memory pool lưu failure cases. Retrieve Model tách static/dynamic để retrieval có cấu trúc.

**Kiểm tra:** Có confidence từ similarity? **KHÔNG** (theo abstract và summary). Không calibration.

**Đánh giá:** Không đe dọa.

### 1.5 VLADriver-RAG (arXiv:2605.08133) & AD-Memo (arXiv:2609.38641)

Cả hai đều là retrieval-augmented VLA cho driving. Không paper nào đề cập confidence từ similarity hay calibration (theo abstract và tài liệu tìm được).

**Đánh giá:** Không đe dọa.

### 1.6 Yao et al. — Confidence-Aware Decision-Making with LLM (arXiv:2605.25393)

**Tác giả:** Yao et al. (HKUST Guangzhou). **Năm:** 2026.

**Nội dung:** Multi-agent workflow sinh demonstrations có gắn confidence, distill vào lightweight dual-head LM (decision probability + rationale), kết hợp RAG. Đánh giá closed-loop trên nuPlan.

**Kiểm tra:** Confidence từ đâu? Từ **LLM agents tự đánh giá** (confidence assessment agent), KHÔNG phải từ experience similarity. Có calibration? **KHÔNG** thấy đề cập.

**Đánh giá:** Liên quan đến mục 17 (distillation) hơn là mục 16. Không đe dọa claim experience-based confidence.

### 1.7 Các paper Evidential Deep Learning cho trajectory prediction

- **Marvi et al. (arXiv:2503.05274):** Evidential Uncertainty Estimation for Multi-Modal Trajectory Prediction. Dùng Normal-Inverse-Gamma cho positional uncertainty + Dirichlet cho mode uncertainty. Single forward pass. Đánh giá trên Argoverse 1/2.
- **Itkina & Kochenderfer (arXiv:2211.08701, CoRL 2022):** Interpretable Self-Aware Neural Networks. Evidential DL cho epistemic uncertainty trong trajectory prediction.

**Đánh giá:** Đây là **model uncertainty** (epistemic/aleatoric từ network), KHÔNG phải experience-based confidence. Chúng là các **BASELINE mà CRFP bắt buộc phải so sánh**, không phải threat. CRFP cần chứng minh confidence từ kinh nghiệm tốt hơn (hoặc bổ sung cho) các phương pháp này.

### 1.8 Các paper Conformal Prediction cho driving

- **Localized Conformal Safety Monitoring (arXiv:2610.02765):** CP cho VLM-based driving scene QA.
- **Ensembles + Conformal cho control (arXiv:2511.07899):** Safety clearance certification.

**Đánh giá:** Conformal prediction cho coverage guarantee — paradigm khác với calibration (ECE). Liên quan nhưng không overlap trực tiếp. Có thể đề cập như hướng thay thế trong related work.

### 1.9 UWDT — Uncertainty-Weighted Decision Transformer

Dùng uncertainty để điều kiện hóa action selection trong roundabout driving. Uncertainty là model-based (epistemic), không phải experience-based.

**Đánh giá:** Liên quan nhưng không đe dọa.

---

## 2. Có paper nào nguy hiểm hơn Retrieve-then-Steer không?

**KHÔNG.** Sau khi đào sâu 10+ paper mới:

- Làn sóng retrieval-augmented driving đang mạnh lên (KEPT, LiLoDriver, DriveVLA-M0, VLADriver-RAG, AD-Memo — tất cả 2025-2026), nhưng **KHÔNG paper nào** tính confidence từ experience similarity.
- CARIL là paper gần nhất với "confidence trong driving" nhưng confidence từ classification head, không phải experience; và không đo calibration.
- Yao et al. (2605.25393) có cả confidence + RAG + driving nhưng confidence từ LLM self-assessment, không phải similarity.

**Retrieve-then-Steer (đợt 1) vẫn là overlap mạnh nhất** — là paper duy nhất có vòng lặp "retrieval → confidence → điều chỉnh hành vi" với công thức tường minh.

---

## 3. Baseline uncertainty nào CRFP bắt buộc phải so?

Từ round 2, danh sách baseline mở rộng:

| Baseline | Paper | Loại uncertainty |
|---|---|---|
| Evidential DL | Marvi et al. 2503.05274 | Model (NIG + Dirichlet) |
| Evidential interpretable | Itkina 2211.08701 | Model (epistemic) |
| Deep Ensembles | (chuẩn, nhiều paper) | Model |
| MC Dropout (UAIL) | Đã biết từ CARIL related work | Model |
| Conformal Prediction | 2610.02765, 2511.07899 | Coverage guarantee |

CRFP cần chứng minh: confidence từ kinh nghiệm (a) được calibrate tốt (ECE thấp, reliability diagram đẹp), và (b) vượt hoặc bổ sung cho các baseline model-uncertainty trên.

---

## 4. Verdict cập nhật: GIỮ WEAKEN

**Lý do giữ (không nâng KILL):**
- Không tìm được paper nào làm đủ bộ ba "confidence từ experience similarity + calibration + driving".
- Làn sóng retrieval-augmented driving mới (5+ paper 2025-2026) đều KHÔNG tính confidence từ similarity — chúng dùng retrieval để cung cấp context/examples, không để định lượng độ tự tin.

**Lý do không hạ ALIVE:**
- Retrieve-then-Steer vẫn đứng đó với vòng lặp cốt lõi trùng CRFP.
- CARIL chứng minh "confidence trong driving IL" đã có người làm (dù bằng cách khác).
- Mật độ paper retrieval+driving tăng nhanh — nguy cơ bị "scoop" nếu chậm.

**Điểm phòng thủ được CỦNG CỐ bởi round 2:**
1. **Calibration là hào phòng thủ chính.** Không một paper nào trong số 18+ paper đã đọc (2 đợt) đo ECE/reliability cho confidence trong driving. Nếu CRFP làm calibration nghiêm túc, đây là đóng góp rõ ràng.
2. **So sánh với model-uncertainty baselines.** Round 2 xác định được các baseline cụ thể (evidential, ensembles, MC dropout, conformal) mà CRFP cần vượt qua.
3. **Domain driving + experience similarity + calibration** — tổ hợp 3 yếu tố vẫn chưa ai làm.

**Hành động bắt buộc:**
1. Cite-and-distinguish: Retrieve-then-Steer (đợt 1), CARIL (round 2), KEPT (round 2, đại diện cho làn sóng retrieval-augmented driving).
2. Trong paper, phải có: reliability diagram + ECE cho confidence của CRFP, và bảng so sánh với ít nhất 2 model-uncertainty baselines (evidential, ensembles).
3. Nếu không làm calibration → sẽ bị coi là phiên bản driving của Retrieve-then-Steer (như đã cảnh báo ở đợt 1).

---

## 5. Blind spots còn lại

- Paper proceedings (CoRL/ICRA/ITSC/IROS) chưa lên arXiv.
- Paper tiếng Trung (làn sóng retrieval-augmented driving có nhiều nhóm Trung Quốc).
- Các paper mới nhất (Q4/2026) chưa được index đầy đủ.
