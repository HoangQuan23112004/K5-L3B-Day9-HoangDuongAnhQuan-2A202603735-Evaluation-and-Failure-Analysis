# Judge audit

Calibration trên hai CSV public (100 dòng mỗi file), backend replay, không gọi LLM.
Human là nhãn đối chiếu; **FAIL là lớp dương** vì mục tiêu là tìm lỗi.

Chạy từ `src/`:

```powershell
..\.venv\Scripts\python.exe -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5
..\.venv\Scripts\python.exe -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 5
..\.venv\Scripts\python.exe -m pytest -q tests/test_lab9_stats.py tests/test_lab9_calibration_edges.py -m student -o addopts= -k "not paired_bootstrap"
```

Kiểm tra: 12 test PASS; 2 test bootstrap thuộc M4 không được chọn.
Tone trả exit 0; helpful trả exit 1 là kết quả calibration mong đợi, không phải lỗi chạy chương trình.

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có, đạt cả ba ngưỡng | Dùng cho tone trong phạm vi calibration này |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không, κ và recall dưới ngưỡng | Loại khỏi gate |

## Ma trận nhầm lẫn và hiệu chỉnh tỷ lệ lỗi

| Tiêu chí | TP (bắt đúng lỗi) | FP (báo nhầm) | FN (bỏ sót) | TN | Sensitivity | Specificity | Tỷ lệ FAIL quan sát | Rogan–Gladen |
|---|---|---|---|---|---|---|---|---|
| tone_ok | 24 | 4 | 6 | 66 | 24/30 = 0.800 | 66/70 ≈ 0.943 | 28/100 = 0.280 | 0.300 |
| helpful | 9 | 0 | 21 | 70 | 9/30 = 0.300 | 70/70 = 1.000 | 9/100 = 0.090 | 0.300 |

Precision = TP/(TP+FP); recall = TP/(TP+FN). Mẫu số bằng 0 thì trả 0 theo đề.
Kappa hiệu chỉnh đồng thuận ngẫu nhiên: (p_o − p_e)/(1 − p_e).
Tone có p_o=0.900, p_e=0.588 nên κ≈0.757; helpful có p_o=0.790,
p_e=0.664 nên κ=0.375. Kappa không xác định khi p_e=1 phải báo ValueError,
không được xem là calibration đạt. Judge hằng với nhãn người pha trộn có κ=0,
không nhất thiết là trường hợp không xác định.

Rogan–Gladen = (p_obs + specificity − 1)/(sensitivity + specificity − 1),
giới hạn kết quả vào [0,1]. Khi sensitivity + specificity = 1, không thể hiệu chỉnh
bằng công thức này. Các đầu vào phải là xác suất hữu hạn trong [0,1].
Hai kết quả 0.300 ở đây khớp tỷ lệ human FAIL vì dùng chính bộ calibration để
ước lượng sai số; đây không phải bằng chứng độc lập rằng hiệu chỉnh sẽ chính xác
trên dữ liệu mới. Hiệu chỉnh tỷ lệ tổng không sửa được nhãn sai của từng câu.

## ≥5 case audit thủ công
| # | Case | Judge nói | Người nói | Ai đúng? | Căn cứ và sửa rubric dự kiến |
|---|---|---|---|---|---|
| 1 | H-008 (FN) | PASS | FAIL | Human theo rubric của bộ dữ liệu | “Em ... nha ... check” được note xác định là quá suồng sã. Bổ sung ví dụ phân biệt thân thiện với suồng sã, quy định cách xưng hô theo đối tượng khách. |
| 2 | H-017 (FN) | PASS | FAIL | Human theo ngữ cảnh trong note | Note nêu khách lớn tuổi, cách gọi “bạn” và “nha” không phù hợp. Cung cấp ngữ cảnh khách cho judge hoặc dùng cách gọi anh/chị khi không biết; không cấm từ “bạn” trong mọi ngữ cảnh. |
| 3 | H-029 (FN) | PASS | FAIL | Human | “Không cần nhắn thêm” mang giọng ra lệnh dù mở đầu “Dạ, vui lòng”. Yêu cầu đánh giá toàn câu và không dùng từ lịch sự làm điều kiện đủ để PASS. |
| 4 | H-042 (FP) | FAIL | PASS | Human | Câu ngắn nhưng lịch sự, nêu số tiền và thời gian nhận; note cho biết judge phạt vì thiếu xin lỗi. Không bắt buộc lời xin lỗi ở mọi tình huống, không dùng độ dài làm đại diện cho tone. |
| 5 | H-051 (FP) | FAIL | PASS | Human theo quy định CS trong note | “Refund” là thuật ngữ được LogiX cho phép. Ghi danh sách thuật ngữ cho phép; không tự đánh FAIL chỉ vì có tiếng Anh. |
| 6 | HL-015 (FN) | PASS | FAIL | Human theo ledger trong note | Reply báo 55000, ledger 40000. Tách tính đúng tiền khỏi độ lịch sự; so reply với ledger bằng code. |
| 7 | HL-016 (FN) | PASS | FAIL | Human theo ledger trong note | Reply có nhiều lời xin lỗi nhưng báo 55000, ledger 35000. Quy định lời xin lỗi không bù được lỗi thông tin; factual correctness là điều kiện bắt buộc và tiền kiểm bằng code. |
| 8 | HL-020 (FN) | PASS | FAIL | Human theo ledger trong note | Reply báo 90000, ledger 120000. Kiểm tra cả báo thiếu tiền lẫn báo thừa; không chỉ tìm các câu hứa hoàn quá mức. |
| 9 | HL-028 (FN) | PASS | FAIL | Human theo ledger trong note | Reply lặp xin lỗi, báo 50000 thay vì ledger 35000. Bổ sung ví dụ câu lịch sự nhưng sai đáp án; tách tone khỏi tính đúng và hữu ích. |
| 10 | HL-035 (FN) | PASS | FAIL | Human theo ledger trong note | Reply dài, lịch sự, báo 50000 thay vì ledger 35000. Rubric yêu cầu bám kết quả giao dịch, không thưởng độ dài; dùng code xác minh tiền trước khi kết luận đạt. |

Các kết luận dựa vào reply, note và human_failure trong CSV. H-017 không thể suy ra
độ tuổi khách chỉ từ reply; các case helpful không thể xác minh số tiền từ lời văn
đơn độc mà phải có ledger. Audit này dùng ledger được mô tả trong note, không chạy
lại giao dịch gốc. Đề xuất rubric ở trên chưa được thử với judge mới; replay giữ
nguyên nhãn nên không được tuyên bố đã cải thiện điểm sau khi viết audit.

## Kết luận
- **Tone được dùng cho tone:** đạt cả ba floors, nhưng vẫn bỏ sót 6/30 lỗi và báo
  nhầm 4/70 câu đạt; không suy rộng thành judge đáng tin cho tiền hay approval.
- **Helpful bị loại khỏi gate:** TP=9, FN=21, FP=0, TN=70. Precision=1 chỉ nói
  rằng 9 lần báo lỗi đều đúng, không cho biết 21 lỗi bị bỏ qua. Recall=0.3 và
  κ=0.375 không đạt floors. Sai tiền vẫn bị cho PASS dù câu văn lịch sự là rủi ro
  phù hợp FM-08; phải kiểm tiền/approval bằng code với ledger/host.
- Rogan–Gladen đưa tỷ lệ lỗi helpful từ 0.09 lên 0.30 nhưng không làm judge đủ
  điều kiện gate: 21 nhãn bỏ sót vẫn còn nguyên.
- Rủi ro còn lại: chỉ kiểm replay công khai, chưa có held-out độc lập, chưa đo
  biến động theo model/prompt hay dữ liệu mới. Sau khi sửa rubric cần lấy nhãn
  người mới, chạy judge thật, calibration lại và kiểm trên held-out trước khi dùng.
