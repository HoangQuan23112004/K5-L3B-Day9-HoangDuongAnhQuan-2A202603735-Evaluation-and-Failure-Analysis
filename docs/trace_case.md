# Trace case — C-014: trừ tiền hai lần

| Trường | Nội dung |
|---|---|
| Trial | m1_pre_deducted C-014@11; run ID R-m1_pre_deducted-C-014-s11; dữ liệu đầy đủ ở src/data/eval/m1_trace_evidence.json |
| Triệu chứng | Quote 150000, đã hoàn trước 30000; ledger mới phải là 120000 nhưng thực tế chỉ 90000. Reply lại nói đã hoàn 120000. |
| Bước sai đầu tiên | Event 5, kind=proposal, payload={"amount_vnd":120000}. Agent tự khấu trừ 30000 trước khi gửi host. |
| Vì sao là bước đầu tiên | Event 1 handoff đúng C-014; event 2 lookup đúng O-515; event 3 quote lấy max(30000,150000)=150000 đúng; event 4 history 30000 đúng. Sai xuất hiện khi thay proposal, không phải khi đọc history. |
| Failure mode | FM-05 pre_deducted là nguyên nhân đầu tiên; FM-08 là hậu quả bổ sung vì reply 120000 khác ledger 90000. |
| Đối chứng | fixed C-014@11 giữ proposal 150000; host khấu trừ một lần, ledger 120000; reply nói 120000. |
| Regression test | tests/test_lab9_regressions.py::test_trace_regression_and_fixed_control[C-014-pre_deducted-RefundAmountCorrect]: grader trả False trên biến thể lỗi, True trên fixed. C-008/C-014-misreport-ReplyAmountCorrect kiểm FM-08 riêng. |
| Chưa chắc chắn | Trace không có event riêng cho mọi hành động bên trong host. Kết luận trừ hai lần dùng cả trace, snapshot ledger và đối chứng; không suy ra ý định của model từ lời văn. |

## Tái lập

Từ src/:

```powershell
..\.venv\Scripts\python.exe -m lab9.m1_evidence
..\.venv\Scripts\python.exe -m pytest -q tests/test_lab9_regressions.py -m student -o addopts= -k trace_regression
```

Script đăng ký shape lỗi bằng công tắc có sẵn trong Lab 9, dùng DB tạm cho mỗi trial;
không sửa Lab 8 và không dùng trace orchestrator từ bài Day 8 làm baseline Day 9.
Năm regression case có đối chứng fixed: ticket_trust C-002, pre_deducted C-014,
pre_deducted C-013 (proposal sai dù ledger vẫn 0), misreport C-008 và C-014. Không sửa labels để làm test xanh.
