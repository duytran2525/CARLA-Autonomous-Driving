# KILL-SEARCH 16 — Độ tự tin từ kinh nghiệm: uncertainty-aware planning, OOD detection, case-based reasoning

Ngày: 2026-10-08. Người đọc: Muse (subagent). Phương pháp: search nhiều góc → đọc abstract → đọc full paper các paper liên quan chặt (tìm từ khóa confidence/calibrat/uncertainty trong toàn văn).

Câu hỏi kill: literature đã làm "confidence from past experience" kèm đo calibration so với baseline uncertainty chưa?

---

## 1. Paper đã đọc sâu

### 1.1 Retrieve-then-Steer: Online Success Memory for Test-Time Adaptation of Generative VLAs
- **arXiv:2605.10094** (2026). Domain: robotic manipulation (VLA), KHÔNG phải driving.
- Đọc: abstract + §1 + §2 + §4 (methodology) toàn văn; tìm "calibrat"/"driving" trong toàn văn.
- Nội dung: robot lưu các đoạn observation-action thành công vào online memory. Khi inference, retrieve các action chunk liên quan, lọc bằng trajectory consistency, gộp thành elite prior. Định nghĩa **retrieval confidence** `c = α·s̃ − β·σ_DTW` (s̃ = độ tương đồng retrieval, σ_DTW = độ phân tán DTW giữa các ứng viên). Confidence này ánh xạ thành guidance strength `t0` cho flow-matching sampler: confidence cao → prior dẫn mạnh; confidence thấp → rớt về sampler gốc.
- Điểm then chốt: **"calibrat" trong paper chỉ xuất hiện ở nghĩa "progress-calibrated memory" (chọn đoạn trajectory để lưu) và "camera calibration errors" — KHÔNG có calibration của confidence theo nghĩa reliability/ECE.** "driving": 0 lần xuất hiện.
- Đánh giá: đây là overlap mạnh nhất về *cơ chế* (retrieval → confidence → điều chỉnh hành vi), nhưng khác domain, không calibration, không so sánh với baseline uncertainty.

### 1.2 CBR-LLM: Case-based Reasoning Augmented LLM for Driving Decision Making
- **arXiv:2506.20531v1** (2025). Domain: driving (safety-critical scenarios, dashcam).
- Đọc: toàn văn PDF (1824 dòng); tìm "confidence" (1 kết quả), "calibrat" (0), "uncertainty" (0).
- Nội dung: retrieve các case lái xe quá khứ bằng vector similarity (risk type + scene caption), dùng làm few-shot prompt cho LLM để ra quyết định evasive maneuver. Đánh giá: decision accuracy, justification quality, alignment với human expert.
- Điểm then chốt: từ "confidence" chỉ xuất hiện 1 lần ở nghĩa "overconfidence của LLM là một concern". **Không tính confidence từ experience, không calibration, không điều chỉnh hành vi theo confidence.**
- Đánh giá: gần CRFP ở "dùng kinh nghiệm quá khứ cho driving", nhưng thiếu toàn bộ vòng confidence → calibration → behavior modulation.

### 1.3 DiLu: A Knowledge-Driven Approach to Autonomous Driving with LLMs
- **arXiv:2309.16292**, ICLR 2024.
- Đọc: abstract + §1 + §3 (methodology) toàn văn qua ar5iv; tìm "confidence" (0), "calibrat" (0).
- Nội dung: framework 4 module (Environment, Reasoning, Reflection, Memory). Memory lưu experiences (scene description + reasoning process). Reasoning module retrieve experience tương tự để ra quyết định; Reflection module đánh giá safe/unsafe rồi cập nhật memory. Với 40 memory items đạt hiệu năng tương đương RL 600k episodes.
- Điểm then chốt: **không có khái niệm confidence nào được tính toán; không calibration; hành vi không điều chỉnh theo mức tự tin.**
- Đánh giá: cùng họ "experience-based driving" với CRFP nhưng dừng ở retrieval → decision, không có confidence layer.

### 1.4 DRO-EDL-MPC: Evidential Deep Learning-Based Distributionally Robust MPC
- **arXiv:2507.05710** (2025). Domain: driving (CARLA validation).
- Đọc: abstract.
- Nội dung: dùng evidential deep learning để tách aleatoric + epistemic uncertainty của perception; xây ambiguity set cho distributionally robust optimization; điều chỉnh độ conservative của MPC theo perception confidence. High confidence → hiệu quả; low confidence → ràng buộc conservative.
- Điểm then chốt: confidence ở đây là **model uncertainty** (từ EDL), KHÔNG phải từ kinh nghiệm quá khứ. Không calibration của confidence theo nghĩa so với baseline.
- Đánh giá: đại diện cho trường phái "uncertainty-aware planning" — tất cả đều dùng model uncertainty, không ai dùng experience similarity.

### 1.5 Ding et al.: Capture Uncertainties in DNNs + PU-RRT
- **arXiv:2108.05118** (2021). Domain: driving (CARLA).
- Đọc: abstract.
- Nội dung: Bayesian DNN phát hiện object 3D kèm aleatoric + epistemic uncertainty; thuật toán PU-RRT (uncertainty-aware RRT) lập kế hoạch tính đến uncertainty của perception và motion của ego.
- Đánh giá: model uncertainty → planning. Không experience, không calibration.

### 1.6 RUDC-T: Risk-Sensitive Uncertainty-Aware Decision-Making and Control
- **arXiv:2609.09650** (2026). Domain: driving.
- Đọc: abstract + §6 (case study).
- Nội dung: đo total uncertainty của RL policy; dùng uncertainty-embedded TTCBF để nới/lỏng ràng buộc an toàn theo confidence của policy. Khi uncertainty cao → can thiệp mạnh; khi thấp → giữ linh hoạt của RL.
- Đánh giá: confidence → behavior modulation, nhưng confidence là **policy/model uncertainty**, không phải experience. Không calibration.

### 1.7 Nitsch et al.: Out-of-Distribution Detection for Automotive Perception
- **arXiv:2011.01413**, ITSC 2021. Domain: automotive perception.
- Đọc: abstract.
- Nội dung: phát hiện OOD mà không cần OOD data khi train, không tăng chi phí inference. Mục đích: trigger safe fallback mode.
- Đánh giá: OOD → fallback nhị phân (an toàn/không), không phải graded confidence, không experience-based.

### 1.8 Farid et al.: Task-Driven OOD Detection with Statistical Guarantees
- **arXiv:2106.13703** (2021, v6 2023). Domain: robot learning (grasping, drone).
- Đọc: abstract.
- Nội dung: dùng PAC-Bayes bound; vi phạm bound → bằng chứng OOD. Có statistical guarantees, task-driven (chỉ nhạy với shift ảnh hưởng performance).
- Đánh giá: OOD detection với guarantees, nhưng là detection, không phải confidence-graded behavior; không experience-based.

### 1.9 Uncertainty-Aware Expert Advice in RL for Autonomous Driving
- **arXiv:2605.30576** (2026). Domain: driving (RL).
- Đọc: các phương trình then chốt (§3).
- Nội dung: tính epistemic uncertainty qua variance của CVaR estimates trên ensemble heads; aleatoric qua return distribution spread. Uncertainty dùng để quyết định khi nào cần expert intervention.
- Đánh giá: model (ensemble) uncertainty → trigger. Không experience, không calibration.

---

## 2. Overlap mạnh nhất ở điểm nào

**Retrieve-then-Steer (arXiv:2605.10094)** là overlap mạnh nhất, ở đúng vòng lặp cốt lõi của CRFP:

- Paper định nghĩa retrieval confidence từ độ tương đồng với kinh nghiệm thành công quá khứ: `c = α·s̃ − β·σ_DTW` (§4, Eq. 8).
- Confidence này điều chỉnh trực tiếp hành vi: ánh xạ thành thời điểm bắt đầu sampling `t0 = t_min + (1 − t_min)·σ(−γc)` (Eq. 9) — confidence cao thì prior dẫn mạnh, thấp thì rớt về sampler gốc (§4).
- Abstract nêu rõ: "adjusts the guidance strength based on retrieval confidence."

Trích ý chính (paraphrase, §1): hệ thống lưu các trial thành công trong online memory và tái dùng chúng để ổn định các lần chạy sau mà không cập nhật policy — "retrieve-then-steer".

**Nhưng 3 điểm khác biệt then chốt:**
1. **Domain**: robotic manipulation (LIBERO, SimplerEnv, bimanual real robot) — 0 lần nhắc "driving" trong toàn văn.
2. **Không calibration**: không có reliability diagram, ECE, hay bất kỳ đo lường nào về việc confidence có khớp xác suất thành công thực tế không; cũng không so sánh với baseline model-uncertainty.
3. **Confidence là heuristic một bước**: công thức tuyến tính trên similarity và DTW dispersion, không được học hay hiệu chỉnh từ dữ liệu.

Các paper còn lại hoặc thiếu confidence (CBR-LLM, DiLu), hoặc confidence là model uncertainty chứ không phải experience (DRO-EDL-MPC, PU-RRT, RUDC-T, 2605.30576), hoặc chỉ là OOD detection nhị phân (Nitsch, Farid).

---

## 3. Khung đánh giá: vấn đề gì mà các cách trước chưa làm được?

| Trường phái | Cái đã làm | Cái chưa làm (khoảng trống của CRFP) |
|---|---|---|
| Uncertainty-aware planning (DRO-EDL-MPC, PU-RRT, RUDC-T, EQN/RDMF, UADMF) | Model uncertainty (ensemble/BNN/EDL) → điều chỉnh conservativeness | Uncertainty đắt (cần ensemble/BNN); không tận dụng việc "đã gặp tình huống này trước đây"; không calibration |
| OOD detection (Nitsch, Farid) | Phát hiện OOD → fallback nhị phân | Không có graded confidence; không experience-based; fallback thô (dừng/đỗ) thay vì điều chỉnh liên tục |
| Experience-based driving (CBR-LLM, DiLu) | Retrieve kinh nghiệm quá khứ → ra quyết định tốt hơn | Không lượng hóa confidence từ retrieval; không calibration; không điều chỉnh hành vi theo mức tự tin |
| Retrieve-then-Steer | Retrieval confidence → điều chỉnh guidance strength | Không driving; không calibration; không so sánh với baseline uncertainty; confidence là heuristic cố định |

**Vấn đề chưa ai giải quyết:** một hệ thống lái xe (a) tính độ tự tin từ độ tương đồng với kinh nghiệm thành công quá khứ, (b) **hiệu chỉnh (calibrate)** độ tự tin đó — tức chứng minh bằng số liệu rằng confidence cao thực sự tương ứng với thành công cao hơn, so sánh trực tiếp với baseline model-uncertainty — và (c) dùng confidence đã hiệu chỉnh để điều chỉnh hành vi một cách graded (thận trọng dần theo mức tự tin, không phải fallback nhị phân).

---

## 4. Verdict: WEAKEN

**Lý do:**

1. **Không KILL**: không paper nào trong tập đã đọc làm đủ bộ ba "confidence từ kinh nghiệm + calibration so với baseline uncertainty + áp dụng cho driving". Retrieve-then-Steer gần nhất nhưng thiếu calibration, thiếu baseline comparison, và khác domain.

2. **WEAKEN ở điểm**: vòng lặp cốt lõi "retrieval → confidence → điều chỉnh hành vi" đã được Retrieve-then-Steer công bố (2026) với công thức tường minh và validation trên simulation + real robot. Nghĩa là ý tưởng "độ tự tin từ kinh nghiệm quá khứ" *per se* không còn hoàn toàn mới — novelty thu hẹp lại vào (a) calibration, (b) so sánh với model-uncertainty baselines, (c) domain driving. Bài báo CRFP **bắt buộc phải cite-and-distinguish** paper này.

3. **Hướng phòng thủ**: điểm mạnh nhất của CRFP so với Retrieve-then-Steer là calibration — paper kia không hề đo xem confidence có khớp thực tế không. Nếu CRFP chứng minh được confidence từ experience được calibrate tốt (reliability diagram, ECE thấp) VÀ vượt baseline uncertainty (ensemble/BNN) về mặt chi phí hoặc độ chính xác, thì claim đứng vững. Nếu không làm được calibration, claim sẽ bị coi là phiên bản driving của Retrieve-then-Steer.

**Blind spots đã nêu rõ**: search tập trung vào arXiv + web; có thể sót paper trong proceedings (CoRL, ICRA, ITSC) chưa lên arXiv; các paper tiếng Trung về chủ đề này chưa được quét.

---

## Phụ lục: arXiv ID tổng hợp

- 2605.10094 — Retrieve-then-Steer (overlap mạnh nhất)
- 2506.20531v1 — CBR-LLM
- 2309.16292 — DiLu (ICLR 2024)
- 2507.05710 — DRO-EDL-MPC
- 2108.05118 — Ding et al. PU-RRT
- 2609.09650 — RUDC-T
- 2011.01413 — Nitsch et al. OOD automotive (ITSC 2021)
- 2106.13703 — Farid et al. task-driven OOD
- 2605.30576 — Uncertainty-aware expert advice RL driving
