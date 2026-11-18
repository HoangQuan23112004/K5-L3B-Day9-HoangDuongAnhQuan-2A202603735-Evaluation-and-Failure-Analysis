"""Render technical Markdown reports from generated evidence, without editing JSON.

Run from src/: python -m bonus.write_reports
Personal details, self-assessments and submission commit remain for the owner.
"""

import json
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out = root.parent / "report" / "team"
    bench = json.loads((root / "reports/benchmark.json").read_text(encoding="utf-8"))
    crash = json.loads((root / "reports/crash.json").read_text(encoding="utf-8"))
    ablation = json.loads((root / "reports/research_ablation.json").read_text(encoding="utf-8"))
    stats = bench["by_shape"]
    workflow = stats["workflow"]
    draft = ablation["by_shape"]["workflow_draft"]
    baseline = ablation["by_shape"]["workflow"]
    delta = draft["cost_per_success_vnd"] - baseline["cost_per_success_vnd"]
    run_id = next(row["run_id"] for row in bench["trials"] if row["shape"] == "workflow")
    table = [
        "| Shape | Pass | Pass^5 | Seed min–max | Variance | Cost/success (VND) | Steps mean / p95 |",
        "| --- | ---: | ---: | --- | ---: | ---: | --- |",
    ]
    for shape, s in stats.items():
        table.append(
            f"| {shape} | {s['pass_rate']:.6f} | {s['pass_5']:.6f} | "
            f"{s['seed_min']:.6f}–{s['seed_max']:.6f} | {s['seed_variance']:.9f} | "
            f"{s['cost_per_success_vnd']:.4f} | {s['mean_steps']:.4f} / {s['p95_steps']:.0f} |"
        )
    metrics_table = "\n".join(table)
    adr = f"""# Decision record

- Shape chọn: workflow
- Commit hash: 098fa7f3673112465f32262f1bfe12764600d24e (nhánh main).
- Run id dẫn chứng: {run_id} (src/reports/benchmark.json).
- Pass rate / pass^5 / seed min-max / variance: {workflow['pass_rate']:.6f} / {workflow['pass_5']:.6f} / {workflow['seed_min']:.6f}–{workflow['seed_max']:.6f} / {workflow['seed_variance']:.9f}.
- Cost per success (mô phỏng, VND): {workflow['cost_per_success_vnd']:.6f}.
- Crash safety: {crash['crash_safety']} (src/reports/crash.json); test_shape_safety.py kiểm thêm cả 3 cửa sổ crash trên từng shape mới.
- Secret leak / approval bypass: không ghi nhận lỗi trên public evaluator và test an toàn; chưa có kết quả hidden, không khẳng định cho dữ liệu chưa chạy.

## Vì sao shape này

So sánh cùng 14 claim, seed 11,22,33,44,55, MockLLM, bảng giá và host. Workflow,
single, orchestrator đều qua 70/70 trial, còn swarm qua 69/70. Workflow không gọi
model và có chi phí thấp nhất. Với nhiệm vụ chủ yếu đọc order → quote → host ghi
refund theo luật cố định, thêm tự chủ chưa đem lại lợi ích đo được trên public.

{metrics_table}

## Có đáng đổi lấy multi-agent không

Giữ workflow trong phạm vi lab. Các shape khác dùng số tool/model call và cách
ghi event khác nhau, nên bảng trên là so sánh cả triển khai; không thể quy mọi
chênh lệch chỉ cho topology. Ablation trong research_card chỉ thay một biến:
thêm draft call, pass không đổi và cost tăng {delta:.6f} VND/success.
Xem xét lại nếu task mới cần suy luận không thể biểu diễn bằng luật, có các nhánh
điều tra độc lập, hoặc khi đánh giá mù trên dữ liệu mới cho thấy cải thiện đủ bù chi phí.

## Trace và bằng chứng

Workflow ghi found, order view qua allowlist, quote, kết quả host và decision.
Không ghi ticket, principal_id, parent_secret, raw headers, SĐT, địa chỉ, tên hàng
hay internal note. Single chỉ ghi tên action và kết quả các tool đọc đã giới hạn
field. Orchestrator ghi handoff từ make_handoff với facts rỗng, tool read-only,
order view và số lượng policy. Không tóm tắt parent context bằng LLM để giả làm redaction.

Mỗi nhánh dùng finish để lấy ledger/audit thật và ghi trace. finally ghi trace và
đóng DB kể cả khi InjectedCrash lan ra ngoài. Quote đầy đủ được chuyển cho host;
host sở hữu approval, cap theo đơn và idempotency refund:claim_id. Các artifact
runtime nằm trong traces/ và bị gitignore; không tạo debug dump ở nơi khác.

## Giới hạn

MockLLM không phải model sản xuất; decide của single là adapter theo trạng thái
vì MockLLM chỉ trả text, không sinh tool call có cấu trúc. Latency là unavailable.
Steps là số event trace và không phải số vòng ReAct hay thời gian thực thi;
khác độ chi tiết logging làm so sánh steps giữa shape có giới hạn.
Benchmark public chạy DB mới cho mỗi trial; retry/crash là các test riêng.
Chưa nhận student_drop nên chưa thể kết luận đạt ngưỡng hidden.
Các số là dữ liệu sinh từ công cụ, không chỉnh JSON. Commit triển khai: 098fa7f.
"""
    card = f"""# Research card

## Phiếu của nhóm

| Field | Hướng dẫn | Nhóm điền |
| --- | --- | --- |
| CÂU | R1 / R2 / R3 / R4 | R4 — evaluation confounders; ablation bước draft. |
| SOURCE | Nguồn, năm, URL, loại bằng chứng | [docs/bonus_topics.md, B4](../../docs/bonus_topics.md), tài liệu lab 2026, nguồn thứ cấp nội bộ; [docs/metrics.md](../../docs/metrics.md). Không xác minh hoặc khẳng định số liệu của paper gốc được nhắc trong đề. |
| CLAIM | Kết luận trong phạm vi nguồn | Theo hướng dẫn B4, so sánh hiệu quả cần baseline đơn giản và ablation với model, tool, seed, corpus, giá, evaluator giữ cố định. |
| BOUNDARY | Giới hạn kết luận | Thử nghiệm này chỉ có LogiX-VN public 14 claim, MockLLM, 5 seed và giá mô phỏng; không suy rộng sang model thật. |
| HYPOTHESIS | Dự đoán đo được | Thêm đúng một draft call vào workflow giữ pass/pass^5, tool calls và refund không đổi, tăng cost/success trên 0 VND; không dự đoán cải thiện chất lượng ngôn ngữ. |
| METHOD | Biến cố định / biến thay đổi | Giữ chung _run_claim và toàn bộ đường xử lý; biến draft=False→True là thay đổi hành vi duy nhất. Tên shape/run_id riêng để cô lập artifact. Cùng MockLLM, tools, seeds 11,22,33,44,55, public corpus, pricing và evaluator; DB mới mỗi trial. |
| FAILURE / METRIC | Lỗi dự kiến và phép đo | Dự kiến không đổi business outcome; đo pass rate, pass^5, variance, cost/success, model/tool calls. test_draft_ablation_preserves_business_result đối chiếu effect, proposal và status. Không dùng pass để đo chất lượng câu trả lời. |

## Kết quả ablation

Lệnh đã chạy từ src/:

```powershell
.\\.venv\\Scripts\\python.exe -m lab8.benchmark --shapes workflow,workflow_draft --extra-shape workflow_draft=bonus.workflow_draft:run_claim --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/research_ablation.json
```

- File report: src/reports/research_ablation.json.
- Run id: R-workflow-C-001-s11 và R-workflow_draft-C-001-s11.
- Workflow: pass={baseline['pass_rate']:.6f}, pass^5={baseline['pass_5']:.6f}, variance={baseline['seed_variance']:.9f}, cost/success={baseline['cost_per_success_vnd']:.6f} VND.
- Workflow + draft: pass={draft['pass_rate']:.6f}, pass^5={draft['pass_5']:.6f}, variance={draft['seed_variance']:.9f}, cost/success={draft['cost_per_success_vnd']:.6f} VND.
- Chênh lệch cost/success: +{delta:.6f} VND; model calls trung bình {baseline['mean_model_calls']:.0f}→{draft['mean_model_calls']:.0f}; tool calls trung bình giữ {baseline['mean_tool_calls']:.6f}.
- Kết quả ủng hộ hypothesis trong phạm vi public: draft tăng chi phí và không thay đổi tính đúng nghiệp vụ do evaluator không chấm câu chữ.
- Giới hạn: đây không phải ablation topology, không chứng minh draft vô ích cho trải nghiệm khách hàng. MockLLM không phải model sản xuất, latency unavailable. Chưa chạy hidden.
"""
    group = f"""# Báo cáo nhóm — Lab 8 LogiX-VN

## 1. Thông tin nhóm

- Nhóm: Oneman, một thành viên.
- Thành viên: Hoàng Dương Anh Quân, MSSV 2A202603735, email 26ai.quanhda@vinuni.edu.vn, GitHub HoangQuan23112004.
- Báo cáo cá nhân: [2A202603735_HoangDuongAnhQuan.md](2A202603735_HoangDuongAnhQuan.md).
- Commit triển khai: 098fa7f3673112465f32262f1bfe12764600d24e (nhánh main).

## 2. Mục tiêu và cách tiếp cận

Xử lý claim đúng chính sách và bảo toàn ledger khi retry/crash. Hoàn thiện workflow
trước, sau đó single ReAct và orchestrator, đối chiếu swarm tham chiếu. Giữ nguyên
host, thước đo, config, fixture và swarm. Không dùng API key hoặc model thật.

## 3. Giải pháp

Workflow đọc claim qua get_claim_view, kiểm order trong scope của principal, quote
từ order/policy hiện hành bằng compute_compensation, rồi gọi issue_refund. Không
trích order_id, số ngày trễ, điều khoản hay số tiền từ ticket.

Single dùng run_react(max_steps=8, worker=True). Adapter decide gọi MockLLM và
chọn tuần tự tool đọc theo observation: order, policy, lịch sử refund, quote. Vì
MockLLM không sinh function call, đây là mô phỏng ReAct bằng adapter trạng thái.
Sau vòng lặp, code lấy quote từ tool; model không được gọi tool ghi hoặc chọn tiền.

Orchestrator dựng make_handoff với facts rỗng và tool đọc, chạy investigator qua
run_readonly_investigators, nhận order view/quote rồi tự gọi host. Chỉ handoff đã
sanitize được ghi trace; parent context và raw ticket không được chuyển qua handoff.

Cả ba xử lý riêng claim không tồn tại, thiếu order, đơn ngoài scope, quote bằng 0,
host từ chối và amount conflict. Quote đầy đủ được đưa cho host để tránh trừ phần
đã hoàn hai lần. finish đọc ledger và audit thật thay vì điền số liệu giả. crash_at
được chuyển nguyên vẹn, InjectedCrash không bị nuốt. finally đóng connection và
ghi trace cả khi crash. Khóa refund:claim_id và transaction của host bảo vệ retry.

## 4. Kết quả

Nguồn: src/reports/benchmark.json. Bốn shape × 14 claim × 5 seed = 280 trial, cùng
MockLLM, seed 11,22,33,44,55, bảng giá mô phỏng, policy as_of 2026-11-15 và DB mới
cho từng trial.

{metrics_table}

Swarm sai C-002 tại seed 55: tin số ngày trễ trong ticket thay cho order. Đây là
điểm yếu cố ý của bản tham chiếu; không sửa để giữ đối chứng. Ba shape mới đều
đạt 70/70. Workflow được chọn vì đạt cùng độ đúng với mức tự chủ và chi phí thấp.

Crash suite: {crash['crash_safety']} từ src/reports/crash.json. Suite này chủ yếu kiểm
host và swarm; test bổ sung kiểm cả 3 cửa sổ crash/resume cho từng shape mới.
Public evaluator cùng các test approval/injection không ghi nhận lỗi an toàn.
Chưa nhận student_drop hoặc hidden labels, nên chưa có kết quả hidden.

Ablation draft: pass giữ 1.0, cost/success tăng từ {baseline['cost_per_success_vnd']:.6f}
lên {draft['cost_per_success_vnd']:.6f} VND. Xem decision_adr.md và research_card.md.

## 5. Khó khăn và cách xử lý

Tên trace dựa trên shape/claim/seed nên cần chạy các lệnh kiểm chứng tuần tự để không ghi đè artifact của nhau. Steps đếm event, không đại diện latency hay số tool call. Chi phí chỉ là chi phí mô phỏng theo công thức của host hiện tại.

## 6. Tổng hợp đóng góp

Nhóm có một thành viên, Hoàng Dương Anh Quân, thực hiện toàn bộ: thiết kế, triển khai
ba shape, kiểm thử, benchmark, ablation và báo cáo. Bảng đóng góp nằm ở TEAM.md,
báo cáo cá nhân ở 2A202603735_HoangDuongAnhQuan.md.

## 7. Hạn chế và hướng cải thiện

MockLLM không phải model sản xuất; latency unavailable. Public chỉ có 14 claim.
Benchmark fresh DB không thay thế test retry/crash. Các shape có số lần đọc tool
và độ chi tiết trace khác nhau nên so sánh tổng thể không cô lập topology.
Ablation draft mới cô lập một thay đổi hành vi; evaluator không chấm câu trả lời.
Đánh giá lại quyết định khi có tập mù mới, model thật hoặc nhánh điều tra độc lập.

## 8. Tài liệu tham khảo

- docs/business_rules.md: nguồn dữ kiện và luật hoàn tiền.
- docs/contracts.md: RunResult, trace, nhánh status và ranh giới dữ liệu.
- docs/architecture.md, docs/metrics.md: kiến trúc và công thức đánh giá.
- docs/bonus_topics.md, B4: hướng dẫn baseline và ablation của lab (nguồn thứ cấp).
- src/lab8/shapes/swarm_reference.py: đối chứng do đề bài cung cấp.

Số liệu trong báo cáo được tạo lại bằng python -m bonus.write_reports sau khi
chạy các lệnh benchmark/crash trong README; không sửa tay JSON bằng chứng.
"""
    for name, content in (
        ("decision_adr.md", adr), ("research_card.md", card), ("group_report.md", group),
    ):
        (out / name).write_text(content, encoding="utf-8", newline="\n")
        print(f"wrote {name}")


if __name__ == "__main__":
    main()
