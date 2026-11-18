# Nộp bài (bài cá nhân, hạn nộp theo ca làm bài)
1. Commit các report sinh bằng script: trong `src/` chạy `git add -f reports/*.json` (`.gitignore` bỏ qua `src/reports/`, không có `-f` thì report không lên repo).
2. Mở PR `starter/d09` → `main` **trong bản fork của bạn**, không mở vào repo gốc. Dán output gate exit 1 của `seeded_regression` vào mô tả PR.
3. Job `eval-gate` xanh thì **merge PR vào `main`**. Giảng viên chấm nhánh `main` của bản fork; commit sau hạn của ca không tính.
4. Dán **link repo fork** (`K5-L3A-DAY09-HoVaTen-MSSV-EvaluationandFailureAnalysis`) lên LMS.

Làm thêm Advanced/Expert sau buổi: tiếp tục trên nhánh, mở PR mới rồi merge lại trước hạn.

## Core (nên xong trước 17:00)
- [x] `src/lab9/{stats,graders,evalset}.py` đã hoàn thành TODO M1–M4
- [x] `src/data/eval/eval_set_v1.jsonl` có `failure_modes`, `labels_v1.json` tách riêng
- [x] `docs/failure_taxonomy.md`, `docs/trace_case.md` (1 case + regression test), `docs/judge_audit.md`, `docs/eval_card.md`, `docs/PRD_v1.1.md`
- [x] Đã sinh local `src/reports/baseline_v1.json`, `eval_fixed.json`, `eval_seeded_regression.json`; chưa commit
- [x] `src/harness_map.yaml` có section `eval`
- [ ] Job `eval-gate` xanh; dán output gate exit 1 của `seeded_regression` vào mô tả PR

## Advanced / Expert (tới hạn nộp)
- [x] `src/config/fm_map.yaml`, `src/config/metric_spec_v2.yaml` (slices, `pass_hat_5`, metric FM-08), `stats.pass_at_k/pass_hat_k`, `gate.slice_check`, `gate.integrity_check`
- [x] `src/data/eval/eval_set_v2.jsonl` + `labels_v2.json` (sinh bằng `evalset --v2 --build`)
- [x] Đã sinh local `src/reports/baseline_v2.json`; chưa commit
- [ ] Job `eval-gate-v2` chạy và xanh trên GitHub
- [ ] Mô tả PR: output `lab9.mutation` (scorecard + `--aa`) và 4 dòng `exit 1` của các trap
- [x] `docs/eval_card.md` có mục v2: ngưỡng chọn từ A/A, slice nào bắt lỗi nào, và giới hạn cỡ mẫu

## Tái lập toàn bộ kết quả local

Từ thư mục repo, dùng PowerShell:

```powershell
cd src
..\.venv\Scripts\python.exe -m lab9.smoke
..\.venv\Scripts\python.exe -m lab9.evalset --build --check
..\.venv\Scripts\python.exe -m lab9.evalset --v2 --build
..\.venv\Scripts\python.exe -m pytest -q -m student -o addopts= -k lab9
..\.venv\Scripts\python.exe -m lab9.verify
..\.venv\Scripts\python.exe -m lab9.write_docs
```

`verify` sinh report và trả exit 0 khi gate Core, scorecard v2, detection và cả bốn trap
đều đạt yêu cầu. `write_docs` cập nhật eval card/PRD/mô tả PR từ report.
`.gitignore` đã cho phép report JSON và snapshot spec được đưa vào git; trap fixtures
và trace runtime vẫn bỏ qua. Baseline lấy từ harness, không sửa tay report.

Chưa push/commit/merge hoặc nộp LMS trong phiên local này. Sau khi review thay đổi,
tạo nhánh `starter/d09`, commit và push, mở PR về main **trong bản fork**.
Dùng nội dung `docs/submission_pr.md` cho mô tả PR. Chờ cả hai job xanh rồi merge.
Các mục CI/PR ở trên chỉ đánh dấu khi GitHub xác nhận; key anchor chấm ẩn không có trong repo.
