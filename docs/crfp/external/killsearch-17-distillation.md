# KILL-SEARCH 17 — Thầy-trò chưng cất lý do (rationale distillation & step-by-step distillation)

Ngày: 08/10/2026. Người thực hiện: Muse (subagent).
Câu hỏi kill: literature về rationale distillation / step-by-step distillation đã làm điều CRFP đề xuất chưa —
thầy = script sinh (lý do + nhãn ý định), trò học theo thứ tự nhân quả
p(lý do|obs,goal) → p(ý định|lý do,obs,goal), áp dụng cho driving decision-making?

## 1. Paper đã đọc sâu

### 1.1 Hsieh et al. 2023 — "Distilling Step-by-Step! Outperforming Larger Language Models with Less Training Data and Smaller Model Sizes"
- arXiv:2305.02301 (v2 revised 05/07/2023). Google Cloud AI Research / UW.
- Đọc: full §1–§3 (method), §4 setup thí nghiệm.
- Nội dung: teacher = 540B PaLM sinh (rationale, label) bằng few-shot CoT prompting (§3.1).
  Student = T5 (220M–11B) huấn luyện multi-task: Task 1 dự đoán label, Task 2 sinh rationale,
  dùng task prefix ([label]/[rationale]), loss L = L_label + λ·L_rationale (Eq. 3–4, §3.2).
- Task: NLI (e-SNLI, ANLI), commonsense QA (CQA), math word problem (SVAMP). KHÔNG phải driving.
- **Điểm then chốt (§3.2):** paper xem xét và LOẠI BỎ chính thiết kế f(x,r)→y (Eq. 2 —
  label được điều kiện trên rationale), với lý do: "this design requires an LLM to first
  generate a rationale before f can make a prediction. The LLM is still necessary during
  deployment, limited its deployability." Họ chọn multi-task song song thay thế.

### 1.2 DriveCoT — Wang et al. 2024 — "DriveCoT: Integrating Chain-of-Thought Reasoning with End-to-End Driving"
- arXiv:2403.16996. HKU / Huawei Noah's Ark Lab.
- Đọc sâu: abstract, §1 intro, §2 related work (đặc biệt Table 1 so sánh dataset), §3 dataset
  + expert policy (§3.2), §4.1 kiến trúc DriveCoT-Agent, §4.2 CoT process (Fig. 8), §5.1–5.2 thí nghiệm + ablation Table 2.
- Nội dung: rule-based expert policy (script, truy cập ground-truth CARLA) vừa điều khiển xe
  vừa sinh chain-of-thought labels cho các khía cạnh (va chạm, đèn đỏ, biển stop, xe phía trước…).
  Dataset: 1058 scenario, 36K sample @2Hz, CARLA 0.9.14, leaderboard 2.0 scenarios.
  DriveCoT-Agent: các CoT aspect được dự đoán qua các head ĐỘC LẬP SONG SONG (learnable queries
  riêng), quyết định tốc độ cuối được SUY RA bằng quy trình cố định viết tay (Fig. 8:
  kiểm hazard → đánh giá xe trước → quyết định), rồi đưa vào PID.
- Ablation Table 2: biến thể "direct decision" (dự đoán thẳng quyết định cuối) thua
  DriveCoT-Agent trên mọi mặt — chứng minh CoT supervision có ích.
- **Không dùng framing distillation** (từ "distill" không xuất hiện trong paper):
  đây là supervised multi-task learning trên label của expert, không phải teacher-student transfer.
- Thứ tự nhân quả: CoT được dự đoán trước, quyết định suy ra sau — NHƯNG bằng luật cố định
  viết tay, KHÔNG phải điều kiện xác suất p(intent|rationale).

### 1.3 Yao et al. 2026 — "Decision-Making with Lightweight Confidence-Aware Language Model for Autonomous Driving"
- arXiv:2605.25393. HKUST (Guangzhou).
- Đọc: abstract, §I intro, §II.C (knowledge distillation), Fig. 1 + mô tả dual-head.
- Nội dung: teacher = LLM qua multi-agent workflow (action voting → confidence assessment →
  summarization) sinh demonstration kèm CoT. Student = Qwen3-1.7B với kiến trúc DUAL-HEAD:
  "joint prediction of decision probabilities and the generation of textual rationales."
- **Hai head song song (joint), không phải tuần tự rationale→decision.** Teacher = LLM, không phải script.

### 1.4 Afsharrad et al. 2026 — "On-Policy Distillation of Language Models for Autonomous Vehicle Motion Planning"
- arXiv:2604.07944. Stanford.
- Đọc: abstract + tóm tắt method. Dựa trên GPT-Driver (scene → language prompt, sinh waypoint
  kèm CoT reasoning). So sánh on-policy GKD vs RL baseline trên nuScenes; GKD gần bằng teacher
  dù nhỏ hơn 5×.
- Teacher = LLM lớn. Distill token-level feedback (logits), không tách riêng rationale thành
  bước nhân quả độc lập.

### 1.5 CoT-Drive — Liao et al. 2025 (arXiv:2503.07234)
- Đọc abstract. Teacher-student: chuyển khả năng hiểu scene của LLM sang lightweight LM cho
  motion forecasting, dùng CoT prompting sinh semantic annotation. Teacher = LLM.

### 1.6 TeLL-Drive — arXiv:2502.01387 (2025)
- Đọc abstract + method sketch. Teacher LLM (CoT reasoning) hướng dẫn student DRL qua
  self-attention fusion + distillation loss trên action. Teacher = LLM, distill policy chứ
  không distill reasoning chain theo thứ tự nhân quả.

### 1.7 Zhang et al. 2023 — "Coaching a Teachable Student" (arXiv:2306.10014, CVPR 2023 Highlight)
- Đọc abstract. Privileged teacher (BEV) → sensorimotor student trong CARLA qua
  feature alignment + coaching. Distillation ở mức representation, không liên quan rationale.

## 2. Trả lời 4 câu hỏi trọng tâm

### (a) Rationale distillation gốc là paper nào, làm gì, cho task gì?
Hsieh et al. 2023 (arXiv:2305.02301). Teacher LLM sinh rationale + label; student multi-task
học cả hai song song. Task: NLI / QA / math — thuần NLP, không driving, không sequential decision.

### (b) Step-by-step distillation có ai áp dụng cho driving chưa?
KHÔNG. Tìm kiếm trực tiếp "\"distilling step-by-step\" autonomous driving applied" không trả về
paper nào áp dụng recipe của Hsieh cho driving. Các paper driving dùng CoT + distillation
(Yao, Afsharrad, CoT-Drive, TeLL-Drive) đều dùng teacher LLM và kiến trúc khác (dual-head
song song, token-level KD, hoặc distill policy).

### (c) Có ai distill reasoning chain cho driving decision-making chưa?
Có, nhưng theo các cách khác với CRFP:
- DriveCoT: script teacher + CoT labels + driving — NHƯNG không phải distillation framing;
  các CoT aspect dự đoán song song; quyết định suy ra bằng luật viết tay.
- Yao et al.: distillation + CoT + driving — NHƯNG teacher LLM, hai head song song.
- Afsharrad / CoT-Drive / TeLL-Drive: distillation + reasoning + driving — NHƯNG teacher LLM,
  không tách rationale thành bước nhân quả riêng.
- KHÔNG ai làm: teacher script + distill theo thứ tự tuần tự p(rationale)→p(intent|rationale)
  cho quyết định lái xe.

### (d) Thứ tự p(rationale)→p(label) đã có ai làm chưa, hay thường post-hoc?
Trong distillation training, mẫu hình áp đảo là SONG SONG (multi-task / dual-head), không phải
tuần tự:
- Hsieh et al. §3.2 đã xem xét f(x,r)→y và LOẠI — vì cần LLM sinh rationale lúc deploy.
- DriveCoT: CoT trước, quyết định sau — nhưng qua luật cố định, không qua điều kiện xác suất.
- Yao et al.: joint prediction (song song).
- Ghi nhận độc lập (Sarkar, 2026): rationale-first khiến label bị điều kiện trên chính lập luận
  của model ("it usually comes out close to 1.0… it stops being comparable") — tức cộng đồng
  đã biết thứ tự này làm thay đổi ngữ nghĩa của xác suất label, nhưng chưa ai biến nó thành
  thiết kế distillation có chủ đích cho driving.
- Post-hoc (label trước, giải thích sau) phổ biến trong explainability, KHÔNG phải trong
  distillation training.

## 3. Overlap mạnh nhất

**DriveCoT (Wang et al., arXiv:2403.16996)** — trùng 3/5 thành phần:
1. Teacher = script rule-based (không phải LLM) ✓
2. Sinh CoT labels cho driving decisions trong CARLA ✓
3. CoT đứng trước quyết định cuối ở lúc inference ✓

Khác ở 2 điểm quyết định:
1. **Không phải distillation:** không có teacher-student transfer; là supervised multi-task
   trên label của expert (từ "distill" không xuất hiện trong paper).
2. **Không có điều kiện xác suất:** các CoT aspect dự đoán bằng head độc lập song song;
   quyết định cuối suy ra bằng quy trình viết tay (Fig. 8), không phải p(intent|rationale)
   được học. Trò không bao giờ "đọc" rationale do chính nó sinh ra rồi mới quyết định.

## 4. Đánh giá theo khung "vấn đề gì mà các cách trước chưa làm được?"

Các cách trước chưa làm được:
1. **Hsieh et al.:** muốn rationale điều kiện label (Eq. 2) nhưng bỏ vì sợ cần LLM lúc deploy.
   → CRFP giải quyết bằng cách để CHÍNH STUDENT sinh rationale lúc test (không cần teacher),
   nên thứ tự nhân quả trở nên khả thi mà không vi phạm deployability.
2. **DriveCoT:** có CoT của script teacher cho driving, nhưng "lý do" chỉ là các head phụ
   song song + luật viết tay suy ra quyết định — không học được phân phối có điều kiện
   p(intent|rationale), nên không can thiệp được vào rationale để đo Δresponse (đây chính là
   lõi (b) của CRFP: contrastive trên chênh lệch response khi đổi rationale).
3. **Yao/Afsharrad/CoT-Drive/TeLL-Drive:** distill reasoning cho driving nhưng teacher là LLM
   (tốn kém, không kiểm soát được tính đúng đắn của rationale); CRFP dùng teacher = script
   nên rationale đúng theo định nghĩa (ground-truth từ simulator), loại được vấn đề
   hallucination của LLM teacher.

## 5. Verdict: ALIVE (với một điểm WEAKEN)

**ALIVE** cho claim cốt lõi: chưa ai thực hiện distillation thầy-trò trong đó
thầy = script, trò học theo thứ tự nhân quả p(lý do|obs,goal) → p(ý định|lý do,obs,goal),
áp dụng cho driving decision-making. Tổ hợp ba yếu tố (script teacher + sequential
conditioning + driving intents) là mới; đặc biệt thứ tự nhân quả chính là thiết kế mà
Hsieh et al. đã xem xét và loại bỏ (§3.2, Eq. 2) — CRFP là bên đầu tiên biến nó thành
hiện thực bằng cách để student tự sinh rationale.

**WEAKEN** cho claim phụ "chưa ai distill reasoning cho driving": đã có nhiều paper
(DriveCoT, Yao et al., Afsharrad et al., CoT-Drive, TeLL-Drive) làm điều này ở mức ý tưởng
lớn. Tính mới của CRFP nằm ở CÁCH distill (thứ tự nhân quả + script teacher), không nằm ở
VIỆC distill reasoning cho driving nói chung. Khi viết paper phải cite-and-distinguish
đầy đủ 5 paper trên, đặc biệt DriveCoT là overlap nguy hiểm nhất.

## 6. Cite-and-distinguish bắt buộc

| Paper | arXiv | Điểm trùng | Điểm khác (distinguish) |
|---|---|---|---|
| Hsieh et al. 2023 | 2305.02301 | rationale distillation gốc | NLP task; LLM teacher; multi-task song song; đã loại bỏ f(x,r)→y |
| DriveCoT 2024 | 2403.16996 | script teacher + CoT + CARLA driving | không phải distillation; head song song; quyết định bằng luật viết tay |
| Yao et al. 2026 | 2605.25393 | distill CoT demonstrations cho driving decisions | LLM teacher; dual-head joint (song song) |
| Afsharrad et al. 2026 | 2604.07944 | distill CoT reasoning cho motion planning | LLM teacher (GPT-Driver); token-level KD |
| CoT-Drive 2025 | 2503.07234 | teacher-student CoT cho driving | LLM teacher; motion forecasting không phải decision |
| TeLL-Drive 2025 | 2502.01387 | LLM teacher + student cho driving | distill policy/action, không distill reasoning chain có thứ tự |
