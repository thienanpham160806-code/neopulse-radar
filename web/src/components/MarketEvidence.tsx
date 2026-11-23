import { dmyTime, isNum, priceTone, TONE_CLASS, TONE_MARK } from "@/lib/fmt";
import { num, signed } from "@/lib/format";
import { componentMeaning } from "@/lib/plain";
import { GLOSSARY } from "@/lib/glossary";
import type { Payload, PulseComponent } from "@/lib/types";
import { Term } from "./Glossary";
import { CenterBar } from "./ui";

const QUESTIONS: Record<string, string> = {
  breadth: "Đa số cổ phiếu đang tăng hay giảm?",
  momentum: "Chỉ số đang chuyển động mạnh đến đâu?",
  book: "Lệnh chờ đang nghiêng về phía nào?",
  foreign: "Khối ngoại đang mua hay bán ròng?",
  liquidity: "Giao dịch sôi động hơn thường lệ không?",
};

export function MarketEvidence({ comps, onNavigate }: { comps: PulseComponent[]; onNavigate: (tab: string) => void }) {
  return (
    <section aria-labelledby="evidence-title" className="mt-6">
      <p className="text-xs font-semibold uppercase tracking-widest text-accent">Từ nhận định đến bằng chứng</p>
      <h2 id="evidence-title" className="mt-1 text-lg font-bold">Năm góc nhìn, mỗi góc trả lời một câu hỏi</h2>
      <p className="mt-1.5 max-w-3xl text-xs leading-relaxed text-muted">
        Các số dưới đây là thành phần chuẩn hóa từ −1 đến +1 để ghép vào điểm nhịp, không phải % tăng giá hay điểm đóng góp. Trọng số gốc là lựa chọn thiết kế; phần thiếu được bỏ qua và phần còn lại được chuẩn hóa lại.
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {comps.map((c) => {
          const tone = priceTone(c.value);
          return (
            <article key={c.key} className="card-elev flex min-w-0 flex-col rounded-2xl border border-line bg-surface p-3.5">
              <div className="flex items-center justify-between gap-1">
                <h3 className="text-sm font-semibold"><Term k={c.key}>{c.name}</Term></h3>
                <span className="tnum text-xs text-muted">{num(c.weight * 100, 0)}%</span>
              </div>
              <p className="mt-1.5 text-xs leading-relaxed text-muted">{QUESTIONS[c.key]}</p>
              <p className={`tnum mt-3 text-xl font-bold ${isNum(c.value) ? TONE_CLASS[tone] : "text-muted"}`}>
                <span aria-hidden>{isNum(c.value) ? `${TONE_MARK[tone]} ` : ""}</span>
                {signed(c.value)}
              </p>
              <div className="mt-1.5"><CenterBar value={c.value} /></div>
              <p className="mt-1.5 text-[11px] text-muted">Thành phần chuẩn hóa −1…+1 · trọng số gốc {num(c.weight * 100, 0)}%</p>
              <p className="mb-3 mt-2 text-xs leading-relaxed">{componentMeaning(c.key, c.value)}</p>
              <button
                type="button"
                onClick={() => onNavigate(GLOSSARY[c.key]?.tab ?? "tong-quan")}
                className="ui-transition mt-auto min-h-9 rounded-lg bg-surface2 px-2.5 text-left text-xs font-semibold text-accent hover:bg-accent hover:text-on-accent"
              >
                {c.key === "breadth" ? "Mở ngành & độ rộng →" : c.key === "momentum" ? "Xem diễn biến giá ↓" : "Mở bảng bằng chứng →"}
              </button>
            </article>
          );
        })}
      </div>
    </section>
  );
}

export function ValidationSummary({ p, onNavigate }: { p: Payload; onNavigate: (tab: string) => void }) {
  const v = p.validation;
  return (
    <section aria-labelledby="validation-summary" className="card-elev mt-6 rounded-2xl border border-line bg-surface p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-accent">Mức độ bằng chứng</p>
          <h2 id="validation-summary" className="mt-0.5 text-lg font-bold">Đã kiểm tra gì, còn thiếu gì?</h2>
        </div>
        <button
          type="button"
          onClick={() => onNavigate("kiem-chung")}
          className="ui-transition min-h-10 rounded-xl bg-surface2 px-3.5 text-xs font-semibold text-accent hover:bg-accent hover:text-on-accent sm:text-sm"
        >
          Xem kiểm chứng & dữ liệu →
        </button>
      </div>
      {v ? (
        <>
          <dl className="mt-3.5 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-xl bg-surface2/60 p-3"><dt className="text-xs text-muted">Phiên đã ghi</dt><dd className="tnum mt-0.5 text-xl font-bold">{num(v.data_quality.n_sessions, 0)}</dd></div>
            <div className="rounded-xl bg-surface2/60 p-3"><dt className="text-xs text-muted">Mã đã có dữ liệu</dt><dd className="tnum mt-0.5 text-xl font-bold">{num(v.data_quality.n_symbols, 0)}</dd></div>
            <div className="rounded-xl bg-surface2/60 p-3"><dt className="text-xs text-muted">Ảnh chụp sổ lệnh</dt><dd className="tnum mt-0.5 text-xl font-bold">{num(v.data_quality.n_quotes, 0)}</dd></div>
            <div className="rounded-xl bg-surface2/60 p-3"><dt className="text-xs text-muted">Khoảng trống bất thường</dt><dd className="tnum mt-0.5 text-xl font-bold">{num(v.data_quality.n_gaps, 0)}</dd></div>
          </dl>
          <p className="mt-3.5 text-sm leading-relaxed">
            Kiểm chứng đặt câu hỏi: <Term k="ic">tín hiệu sổ lệnh có liên hệ với thay đổi giá sau đó không?</Term> So sánh theo thứ tự phiên, tách <Term k="sample">trong mẫu và ngoài mẫu</Term>.
          </p>
          <p className="mt-1.5 text-xs leading-relaxed text-muted">
            {v.data_quality.n_sessions < 5
              ? "Chưa đủ 5 phiên tối thiểu của đồ án; kết quả mới có tính minh họa. "
              : "Đã đạt mốc 5 phiên tối thiểu của đồ án; vẫn cần nhiều phiên hơn để đánh giá tính ổn định. "}
            IC hoặc tỷ lệ cùng chiều chưa chứng minh lợi nhuận sau phí.
          </p>
          {v.generated_at ? (
            <p className="mt-2 text-xs text-muted">
              Kiểm chứng tính lúc {dmyTime(v.generated_at)}{v.data_until ? ` · Dữ liệu đến ${dmyTime(v.data_until)}` : ""}. Thống kê trên tập phiên đã dùng để kiểm chứng, không chỉ riêng bộ lọc đang xem.
            </p>
          ) : null}
        </>
      ) : (
        <p className="mt-3 text-sm leading-relaxed text-muted">
          Bản dữ liệu này chưa có kết quả kiểm chứng. Số liệu quan sát và điểm tổng hợp hiện có chưa đủ để kết luận tín hiệu dự báo tốt. Mở mục kiểm chứng để xem kết quả khi bộ xử lý công bố.
        </p>
      )}
      {p.meta.is_simulated || v?.simulated_signals_are_planted ? (
        <p className="mt-3 rounded-xl bg-surface2 p-3 text-xs font-semibold leading-relaxed text-sim">
          Dữ liệu mô phỏng: tín hiệu được cài sẵn, chỉ kiểm tra được đường tính toán; không phải bằng chứng về thị trường thật.
        </p>
      ) : null}
    </section>
  );
}

export function ComponentCoverage({ comps }: { comps: PulseComponent[] }) {
  return (
    <p className="mt-1.5 text-center text-xs leading-relaxed text-muted">
      Đang dùng <b className="tnum text-fg">{comps.filter((c) => isNum(c.value)).length}/{comps.length}</b> nhóm tín hiệu có số liệu. Số nhóm có dữ liệu không phải độ chính xác dự báo.
    </p>
  );
}
