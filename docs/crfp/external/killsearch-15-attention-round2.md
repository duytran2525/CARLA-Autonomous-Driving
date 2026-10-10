# KILL-SEARCH 15 — VÒNG 2 (bổ sung)

Ngày: 08/10/2026. Mục đích: đào sâu thêm các góc chưa khai thác kỹ ở vòng 1 để chắc không sót overlap nguy hiểm cho luận điểm "attention theo ý định".

## Paper MỚI đã đọc sâu

### 1. Makrigiorgos et al. 2020 — "Human Visual Attention Prediction Boosts Learning & Performance of Autonomous Driving Agents" (arXiv:1909.05003, IEEE RA-L + ICRA 2020) — ĐỌC FULL

**Phát hiện then chốt:** Paper này có mô hình **"Intention-Branched DR(eye)VE"** — đưa high-level command vào mạng dự đoán gaze với tư cách "the current intention of the driver at each frame" (§II-B). 4 command = đúng 4 lệnh CIL ("Follow Lane", "Turn Left", "Turn Right", "Go Straight"). Mỗi command có một nhánh saliency riêng; khi dự đoán thì chuyển nhánh theo command của expert demonstrator.

Kết quả (Table I): Intention-Branched DR(eye)VE đạt DKL 0.642/CC 0.763, nhỉnh hơn DR(eye)VE gốc (0.654/0.761) — tác giả kết luận thiết kế intention-branched được xác thực.

**Đánh giá overlap:** Đây là paper MỚI nguy hiểm nhất vòng 2 — trực diện hơn cả 2006.03347 ở đúng cụm từ "attention theo intention". Nhưng vẫn khác CRFP ở 4 điểm:
1. *Loại intent:* command điều hướng tĩnh theo route (rẽ trái/phải ở ngã tư) vs maneuver rời rạc đang thực thi (vượt, nhường).
2. *Cơ chế:* chuyển nhánh cứng (hard switch, kiểu CIL) vs điều biến attention chung bằng intent hiện tại.
3. *Mục đích:* bắt chước gaze người để mask ảnh huấn luyện agent — không liên quan counterfactual.
4. *Không có framing counterfactual:* không ước lượng P(response | ego action), không supervise Δresponse.

### 2. Li & Cui 2024 — "Does End-to-End Autonomous Driving Really Need Perception Tasks?" / SSR (arXiv:2409.18341) — ĐỌC FULL §1–§3

**Nội dung liên quan:** SSR dùng **navigation-guided Sparse Scene Representation**: encode navigation command bằng Squeeze-and-Excitation vào BEV feature → BEV "nhận biết navigation" (§3.2, Eq. 3) → TokenLearner trích 16 sparse token qua spatial attention (Eq. 4–5). Tác giả viết rõ "extracts scene queries guided by the navigation commands, akin to human attention mechanisms."

**Đánh giá overlap:** Cơ chế gần với "điều biến attention bằng intent" hơn hard-switching (SE layer là feature modulation theo command). Nhưng: (a) command vẫn là 3 lệnh điều hướng tĩnh; (b) mục đích là nén scene representation cho planning hiệu quả, không phải counterfactual; (c) không có khái niệm phản ứng của agent khác. Mức đe dọa: trung bình-thấp.

### 3. Porres et al. 2024 — "Guiding Attention in End-to-End Driving Models" (arXiv:2405.00242) — đọc abstract + §3

**Kết luận:** Không phải intent-conditioned attention. Paper này guide attention bằng saliency map ở training time (loss phụ); command chỉ là input token bình thường. Không overlap.

### 4. Các họ đã quét nhanh (không đọc full vì không liên quan trực tiếp)

- **Gated/GAT attention cho trajectory prediction** (GC-GAT 2504.11150, GIVA, Zeng et al.): attention mô hình tương tác xe–xe, không điều kiện trên intent. Không overlap.
- **BEV attention** (BEVFormer 2203.17270, FipTR, TBP-Former): kiến trúc perception, attention phục vụ fusion/detection — không có khái niệm intent điều khiển attention. Không overlap.
- **Object-centric attention** (CarFormer, Deep Object-Centric Policies 1811.05432): học object nào quan trọng cho policy nói chung, không điều kiện trên intent. Không overlap.
- **MIAT** (maneuver-intention-aware transformer): điều kiện hóa *dự đoán quỹ đạo* trên maneuver — không phải điều biến attention weights. Khác trục.
- **TransFuser/InterFuser:** attention cho sensor fusion, không điều kiện trên command/intent.

## Có paper nào nguy hiểm hơn vòng 1 không?

**Có — 1909.05003.** So với 2006.03347 (vòng 1), paper này trực diện hơn ở đúng cụm "attention theo intention của driver" và làm trên gaze/saliency (đúng bản chất attention hơn là attention-head cho driving). Tuy nhiên cả hai paper đều dùng command điều hướng tĩnh + hard branch switching, nên **không paper nào đơn lẻ vượt qua được 3 trục phân biệt của vòng 1** (loại intent / mục đích counterfactual / cơ chế modulation).

Điểm đáng lo thực sự: giờ có **HAI paper** (2006.03347 + 1909.05003) làm intent-conditioned attention, cộng thêm SSR làm navigation-guided attention. Claim "attention có điều kiện trên intent" ở mức cơ chế đơn lẻ ngày càng chật chội.

## Verdict cập nhật: giữ WEAKEN (nhưng siết chặt phòng thủ)

- **Không KILL:** vẫn chưa ai dùng intent-conditioned attention cho ước lượng counterfactual P(response | ego action); chưa ai dùng maneuver intent đang thực thi (vs command tĩnh); chưa ai điều biến attention chung (vs hard switch).
- **WEAKEN mạnh hơn vòng 1:** danh sách cite-and-distinguish bắt buộc giờ gồm **3 paper**: 2006.03347, **1909.05003** (mới), SSR 2409.18341 (mới, mức nhẹ).
- **Khuyến nghị phát biểu luận điểm:** không claim ở mức "attention theo intent" đơn lẻ nữa — phải claim ở mức **kết hợp**: intent-conditioned attention **phục vụ** counterfactual response modeling. Đó là vùng chưa ai đụng tới.

## Blind spots còn lại

- Có thể sót paper proceedings (CoRL/ICRA/ITSC) chưa lên arXiv.
- Chưa quét citation graph của 1909.05003 (paper nào trích nó và mở rộng ý tưởng intention-branched).
