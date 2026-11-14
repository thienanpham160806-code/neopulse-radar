"""Bảng điều khiển NeoPulse Radar.  Chạy:  streamlit run src/neopulse/app/dashboard.py

Lớp giao diện CHỈ đọc SQLite và gọi `build_view`; không tự tính chỉ báo, không gọi NEO API trực tiếp
(việc đó thuộc bộ ghi). Nhờ vậy mất kết nối API không làm treo giao diện - chỉ làm dữ liệu "cũ đi".
"""
from __future__ import annotations

import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from neopulse.analytics import alerts as alerting
from neopulse.analytics import validation
from neopulse.analytics.briefing import render_briefing
from neopulse.analytics.explain import llm_summary, template_summary
from neopulse.analytics.view import SessionView, build_view, fmt_money
from neopulse.config import load_settings
from neopulse.data.storage import Storage
from neopulse.finance.microstructure import add_book_metrics, make_bars, walk_book
from neopulse.finance.pulse import COMPONENT_NAMES, WEIGHTS

st.set_page_config(page_title="NeoPulse Radar", page_icon="📡", layout="wide")
SOURCE_LABEL = {"neo": "NEO API (dữ liệu thật)", "sim": "Mô phỏng"}
UP, DOWN, NEUTRAL = "#15803d", "#b91c1c", "#64748b"
LUNCH_BREAK = [dict(bounds=[11.5, 13], pattern="hour")]  # ẩn giờ nghỉ trưa trên trục thời gian


@st.cache_resource
def get_storage(path: str) -> Storage:
    return Storage(path)


@st.cache_data(ttl=20, show_spinner=False)
def cached_view(path: str, source: str, day: str | None, index_code: str, symbols: tuple[str, ...],
                freq: str, order_value: float, _stamp: str) -> SessionView:
    return build_view(get_storage(path), source, day, index_code, symbols=list(symbols) or None,
                      bar_freq=freq, order_value=order_value)


@st.cache_data(ttl=300, show_spinner="Đang tính kiểm chứng…")
def cached_validation(path: str, source: str, freq: str, _stamp: str):
    db = get_storage(path)
    bars = make_bars(db.quotes(source=source), freq)
    res = validation.validate_signals(bars)
    per = validation.per_session_ic(bars)
    al = alerting.detect(bars, source=source)
    truth = alerting.evaluate_against_truth(al, db.table("sim_truth")) if source == "sim" else None
    return res, per, truth, validation.data_quality_report(db, source)


def gauge(score: float, label: str) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score, number={"suffix": " /100", "font": {"size": 34}},
        title={"text": label, "font": {"size": 16}},
        gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#0f172a", "thickness": 0.25},
               "steps": [{"range": [0, 35], "color": "#fecaca"}, {"range": [35, 45], "color": "#fee2e2"},
                         {"range": [45, 55], "color": "#e2e8f0"}, {"range": [55, 65], "color": "#dcfce7"},
                         {"range": [65, 100], "color": "#bbf7d0"}]}))
    fig.update_layout(height=230, margin=dict(l=20, r=20, t=50, b=10))
    return fig


def header(v: SessionView, settings) -> None:
    left, right = st.columns([3, 2])
    with left:
        st.title("📡 NeoPulse Radar")
        st.caption("**Mục tiêu:** trả lời nhanh *thị trường đang ở trạng thái nào, áp lực mua/bán nằm ở đâu và có gì bất "
                   "thường* từ dữ liệu NEO API (VPBankS). **Người dùng:** nhà đầu tư cá nhân và chuyên viên phân tích "
                   "cần theo dõi nội phiên. Công cụ phân tích học thuật — không phải khuyến nghị đầu tư.")
    with right:
        icon = {"ok": "🟢", "stale": "🟠", "no_data": "🔴"}[v.status]
        upd = v.last_update.strftime("%H:%M:%S · %d/%m/%Y") if v.last_update is not None else "—"
        st.markdown(f"**Nguồn:** {SOURCE_LABEL.get(v.source, v.source)}  \n"
                    f"**Cập nhật gần nhất:** {upd} (giờ VN)  \n**Trạng thái:** {icon} {v.status_message}")
    if v.is_simulated:
        st.warning("**DỮ LIỆU MÔ PHỎNG.** Mọi con số trên trang này do bộ giả lập sinh ra để trình diễn sản phẩm; "
                   "không phản ánh thị trường thật. Chuyển sang nguồn *NEO API* ở thanh bên khi đã có dữ liệu ghi thật.",
                   icon="⚠️")
    elif v.status == "stale":
        st.error(v.status_message + " Các chỉ số bên dưới phản ánh thời điểm cập nhật gần nhất, không phải hiện tại.", icon="🟠")


def tab_overview(v: SessionView, settings) -> None:
    r, p = v.index_row or {}, v.pulse
    c = st.columns(5)
    c[0].metric("Điểm nhịp", "—" if math.isnan(p.score) else f"{p.score:.1f}", p.label, delta_color="off", delta_arrow="off")
    c[1].metric(v.index_code, f"{r.get('value', float('nan')):,.2f}", f"{r.get('pct_change', 0):+.2f}%")
    c[2].metric("Tăng / Giảm", f"{r.get('advances', 0):.0f} / {r.get('declines', 0):.0f}",
                f"A/D = {r.get('ad_ratio', float('nan')):+.2f}", delta_color="off", delta_arrow="off")
    c[3].metric("Giá trị giao dịch", fmt_money(r.get("total_value")),
                f"trần {r.get('n_ceiling', 0):.0f} · sàn {r.get('n_floor', 0):.0f}", delta_color="off", delta_arrow="off")
    fs = v.foreign_summary
    c[4].metric("Khối ngoại ròng (rổ)", fmt_money(fs.get("net_val")),
                f"{fs.get('n_net_buy', 0)} mua · {fs.get('n_net_sell', 0)} bán", delta_color="off", delta_arrow="off")

    g, s = st.columns([1, 2])
    with g:
        if math.isnan(p.score):
            st.info("Chưa đủ thành phần để tính điểm nhịp (cần dữ liệu cho ít nhất một nửa trọng số).")
        else:
            st.plotly_chart(gauge(p.score, p.label), width="stretch")
        comp = pd.DataFrame({"Thành phần": [COMPONENT_NAMES[k] for k in WEIGHTS],
                             "Giá trị": [p.components.get(k) for k in WEIGHTS],
                             "Trọng số": [WEIGHTS[k] for k in WEIGHTS]})
        fig = px.bar(comp, x="Giá trị", y="Thành phần", orientation="h", range_x=[-1, 1],
                     color="Giá trị", color_continuous_scale=["#b91c1c", "#e2e8f0", "#15803d"], range_color=[-1, 1],
                     hover_data=["Trọng số"])
        fig.update_layout(height=230, margin=dict(l=0, r=0, t=10, b=0), coloraxis_showscale=False, yaxis_title=None)
        st.plotly_chart(fig, width="stretch")
        if p.missing:
            st.caption("Thiếu dữ liệu: " + ", ".join(COMPONENT_NAMES[m] for m in p.missing)
                       + (". *Thanh khoản* cần ≥ 3 phiên trước để có mức so sánh." if "liquidity" in p.missing else "."))
        if v.sensitivity and not math.isnan(v.sensitivity.get("base", float("nan"))):
            st.caption(f"Độ nhạy trọng số (±50%): điểm dao động {v.sensitivity['p05']:.1f}–{v.sensitivity['p95']:.1f}; "
                       f"nhãn giữ nguyên trong {v.sensitivity['label_stability'] * 100:.0f}% số lần thử.")
    with s:
        st.subheader("Nhận định từ số liệu")
        use_llm = bool(settings.llm_api_key and settings.llm_model) and st.toggle(
            "Diễn giải bằng mô hình ngôn ngữ (có kiểm tra số liệu)", value=False)
        if use_llm:
            out = llm_summary(v, settings)
            st.write(out["text"])
            st.caption(f"Nguồn diễn giải: {out['engine']}" + (f" · đã loại đầu ra mô hình: {out['rejected_reason']}" if out["rejected_reason"] else "")
                       + " · Văn bản do mô hình tạo, đã đối chiếu số với dữ liệu nhưng không phải nhận định đã kiểm chứng.")
        else:
            for line in template_summary(v):
                st.markdown("- " + line)
        if v.divergence:
            st.warning(v.divergence, icon="🔀")
        if len(v.pulse_series):
            ps = v.pulse_series
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ps["bar"], y=ps["index_value"], name=v.index_code, line=dict(color="#1d4ed8")))
            fig.add_trace(go.Scatter(x=ps["bar"], y=ps["score"], name="Điểm nhịp", yaxis="y2", line=dict(color="#7c3aed", dash="dot")))
            fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=1.12),
                              yaxis=dict(title=v.index_code), xaxis=dict(rangebreaks=LUNCH_BREAK),
                              yaxis2=dict(title="Điểm nhịp", overlaying="y", side="right", range=[0, 100], showgrid=False))
            st.plotly_chart(fig, width="stretch")
            st.caption("Điểm nhịp nội phiên không gồm thành phần thanh khoản. Trục phải cố định 0–100.")


def tab_book(v: SessionView, order_value: float) -> None:
    if v.liquidity.empty:
        st.info("Chưa có dữ liệu sổ lệnh cho bộ lọc hiện tại.")
        return
    st.subheader("Bản đồ áp lực sổ lệnh")
    lt = add_book_metrics(v.latest).dropna(subset=["obi3"])
    if len(lt):
        fig = px.treemap(lt, path=["symbol"], values="total_value", color="obi3", range_color=[-1, 1],
                         color_continuous_scale=["#b91c1c", "#f1f5f9", "#15803d"],
                         hover_data={"obi3": ":.2f", "spread_bps": ":.1f", "pct_change": ":+.2f", "total_value": ":,.0f"})
        fig.update_traces(root_color="white")
        fig.update_layout(height=360, margin=dict(l=0, r=0, t=10, b=0), coloraxis_colorbar=dict(title="OBI₃"))
        st.plotly_chart(fig, width="stretch")
        st.caption("Diện tích = giá trị khớp trong phiên; màu = OBI₃ (xanh: bên mua dày hơn, đỏ: bên bán dày hơn) trên 3 mức giá tốt nhất.")
    st.subheader("Bảng thanh khoản")
    show = v.liquidity.round(2).rename_axis("Mã").rename(columns={
        "last": "Giá", "spread_bps": "Spread (bps)", "depth_value": "Độ sâu 3 mức (đ)", "total_value": "GT khớp (đ)",
        "obi3": "OBI₃", "pressure": "Bán/Mua", "slippage_bps": "Trượt giá (bps)", "fill_ratio": "Tỷ lệ khớp",
        "amihud": "Amihud (bps/tỷ)", "liq_score": "Điểm thanh khoản"})
    st.dataframe(show, width="stretch", height=330, column_config={
        "Điểm thanh khoản": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
        "Tỷ lệ khớp": st.column_config.NumberColumn(format="percent"),
        "Độ sâu 3 mức (đ)": st.column_config.NumberColumn(format="compact"),
        "GT khớp (đ)": st.column_config.NumberColumn(format="compact")})
    st.caption(f"Trượt giá: chi phí ước lượng (so với giá giữa) khi MUA ngay lệnh {fmt_money(order_value)} bằng cách đi qua 3 mức "
               "giá bán — là cận dưới vì giả định sổ lệnh đứng yên. Tỷ lệ khớp < 100% nghĩa là 3 mức không đủ hấp thụ.")

    st.subheader("Soi một mã")
    sym = st.selectbox("Mã", sorted(v.latest["symbol"]), key="book_sym")
    row = add_book_metrics(v.latest[v.latest["symbol"] == sym]).iloc[0]
    a, b = st.columns([1, 2])
    with a:
        ladder = pd.DataFrame({
            "KL mua": [row.get(f"bid_vol{i}") for i in (1, 2, 3)], "Giá mua": [row.get(f"bid{i}") for i in (1, 2, 3)],
            "Giá bán": [row.get(f"ask{i}") for i in (1, 2, 3)], "KL bán": [row.get(f"ask_vol{i}") for i in (1, 2, 3)]})
        st.dataframe(ladder, hide_index=True, width="stretch")
        if row.get("auction_flag"):
            st.caption(f"Đang trong phiên định kỳ ({row['auction_flag']}): giá mức 1 không phải giá giới hạn.")
        st.metric("OBI₃", f"{row['obi3']:+.2f}" if pd.notna(row["obi3"]) else "—",
                  f"microprice lệch {row['micro_dev_bps']:+.1f} bps" if pd.notna(row["micro_dev_bps"]) else None, delta_color="off", delta_arrow="off")
        qty = st.number_input("Khối lượng lệnh giả định (cp)", min_value=100, value=10_000, step=100)
        side = st.radio("Chiều", ["buy", "sell"], format_func=lambda x: "Mua" if x == "buy" else "Bán", horizontal=True)
        w = walk_book(row, qty, side)
        if math.isnan(w["slippage_bps"]):
            st.info("Không ước lượng được: thiếu một phía sổ lệnh.")
        else:
            st.write(f"Khớp được **{w['filled']:,.0f}** cp ({w['fill_ratio'] * 100:.0f}%) ở giá bình quân "
                     f"**{w['avg_price']:,.1f}**, trượt **{w['slippage_bps']:.1f} bps** so với giá giữa."
                     + (f" Còn **{w['unfilled']:,.0f}** cp vượt quá 3 mức giá." if w["unfilled"] > 0 else ""))
    with b:
        bs = v.bars[v.bars["symbol"] == sym]
        if len(bs):
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=bs["bar"], y=bs["mid"], name="Giá giữa", line=dict(color="#0f172a")))
            fig.add_trace(go.Bar(x=bs["bar"], y=bs["obi3"], name="OBI₃", yaxis="y2", opacity=0.45,
                                 marker_color=[UP if x >= 0 else DOWN for x in bs["obi3"].fillna(0)]))
            fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=1.1),
                              yaxis=dict(title="Giá giữa"), xaxis=dict(rangebreaks=LUNCH_BREAK),
                              yaxis2=dict(title="OBI₃", overlaying="y", side="right", range=[-1, 1], showgrid=False))
            st.plotly_chart(fig, width="stretch")


def tab_foreign(v: SessionView) -> None:
    if v.foreign.empty:
        st.info("Chưa có dữ liệu khối ngoại.")
        return
    f = v.foreign.reset_index()
    top = pd.concat([f.head(8), f.tail(8)]).drop_duplicates("symbol").sort_values("net_val")
    fig = px.bar(top, x="net_val", y="symbol", orientation="h", color=top["net_val"] > 0,
                 color_discrete_map={True: UP, False: DOWN}, labels={"net_val": "Giá trị ròng (đồng)", "symbol": ""})
    fig.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
    a, b = st.columns(2)
    a.subheader("Mua/bán ròng theo mã")
    a.plotly_chart(fig, width="stretch")
    b.subheader("Chiều và quy mô")
    sc = px.scatter(f.dropna(subset=["net_ratio", "participation"]), x="participation", y="net_ratio", size="total_value",
                    text="symbol", labels={"participation": "Tỷ trọng NN trong giao dịch", "net_ratio": "Ròng / (mua + bán)"})
    sc.update_traces(textposition="top center", marker_color="#1d4ed8")
    sc.add_hline(y=0, line_dash="dot", line_color=NEUTRAL)
    sc.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0), xaxis_tickformat=".0%", yaxis_range=[-1.05, 1.05])
    b.plotly_chart(sc, width="stretch")
    b.caption("Góc trên-phải: NN mua một chiều VÀ chiếm tỷ trọng lớn — tín hiệu có trọng lượng. Mã sát trục dọc: NN gần như không tham gia.")
    st.dataframe(v.foreign.round(3).rename_axis("Mã").rename(columns={
        "f_buy_val": "NN mua (đ)", "f_sell_val": "NN bán (đ)", "net_val": "Ròng (đ)", "net_ratio": "Ròng/tổng",
        "participation": "Tỷ trọng NN", "room_used": "Room đã dùng", "total_value": "GT khớp (đ)"}),
        width="stretch", height=300, column_config={
            "Tỷ trọng NN": st.column_config.NumberColumn(format="percent"),
            "Room đã dùng": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent"),
            **{c: st.column_config.NumberColumn(format="compact") for c in ("NN mua (đ)", "NN bán (đ)", "Ròng (đ)", "GT khớp (đ)")}})


def tab_derivatives(v: SessionView) -> None:
    if v.basis.empty:
        st.info("Chưa có dữ liệu hợp đồng tương lai khớp được với chỉ số VN30 trong phiên này. "
                "Basis chỉ tính khi chọn chỉ số VN30 và bộ ghi có nhận dữ liệu HĐTL.")
        return
    bs = v.basis_state
    c = st.columns(4)
    c[0].metric(bs["symbol"], f"{v.basis['future'].iloc[-1]:,.1f}", f"cơ sở {v.basis['spot'].iloc[-1]:,.2f}", delta_color="off", delta_arrow="off")
    c[1].metric("Basis", f"{bs['basis']:+.2f} điểm", f"{bs['basis_pct']:+.2f}%")
    c[2].metric("Ngày tới đáo hạn", f"{bs['dtm']:.0f}", bs["label"], delta_color="off", delta_arrow="off")
    c[3].metric("Lệch so với giá trị hợp lý", f"{bs['mispricing']:+.2f} điểm",
                f"z nội phiên = {bs['z']:+.1f}" if not math.isnan(bs["z"]) else "chưa đủ dữ liệu cho z", delta_color="off", delta_arrow="off")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=v.basis["ts"], y=v.basis["basis"], name="Basis (điểm)", fill="tozeroy", line=dict(color="#b45309")))
    fig.add_hline(y=0, line_dash="dot", line_color=NEUTRAL)
    fig.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="F − S (điểm)", xaxis=dict(rangebreaks=LUNCH_BREAK))
    st.plotly_chart(fig, width="stretch")
    st.caption("Basis phải hội tụ về 0 khi đáo hạn. Giá trị hợp lý dùng mô hình chi phí lưu giữ với lãi suất giả định 4,5%/năm, "
               "không cổ tức. Basis âm không tự động là cơ hội arbitrage vì bán khống cơ sở bị hạn chế.")


def tab_alerts(v: SessionView) -> None:
    if v.alerts.empty:
        st.success("Không có cảnh báo nào trong phiên với bộ lọc hiện tại.")
        return
    c = st.columns(3)
    sev = c[0].multiselect("Mức ưu tiên", ["CAO", "TRUNG BÌNH", "THẤP"], default=["CAO", "TRUNG BÌNH"])
    rules = c[1].multiselect("Loại", list(alerting.RULE_NAMES), format_func=alerting.RULE_NAMES.get)
    syms = c[2].multiselect("Mã", sorted(v.alerts["symbol"].unique()))
    a = v.alerts[v.alerts["severity"].isin(sev)]
    if rules:
        a = a[a["rule"].isin(rules)]
    if syms:
        a = a[a["symbol"].isin(syms)]
    st.caption(f"{len(a)} / {len(v.alerts)} cảnh báo. Cảnh báo là tín hiệu *đáng xem*, không phải khuyến nghị mua/bán.")
    tl = a.assign(Loại=a["rule"].map(alerting.RULE_NAMES))
    if len(tl):
        fig = px.scatter(tl, x="ts", y="symbol", color="severity", symbol="Loại", hover_data=["message"],
                         color_discrete_map={"CAO": DOWN, "TRUNG BÌNH": "#d97706", "THẤP": NEUTRAL})
        fig.update_traces(marker_size=11)
        fig.update_layout(height=max(260, 22 * tl["symbol"].nunique() + 120), margin=dict(l=0, r=0, t=10, b=0),
                          yaxis_title=None, xaxis_title=None, legend_title=None)
        st.plotly_chart(fig, width="stretch")
    st.dataframe(a.assign(Giờ=a["ts"].dt.strftime("%H:%M"), Loại=a["rule"].map(alerting.RULE_NAMES))
                 [["Giờ", "symbol", "severity", "Loại", "message", "value", "threshold"]]
                 .rename(columns={"symbol": "Mã", "severity": "Mức", "message": "Nội dung", "value": "Giá trị", "threshold": "Ngưỡng"}),
                 hide_index=True, width="stretch", height=360)


def tab_ranking(v: SessionView) -> None:
    if v.ranking.empty:
        st.info("Chưa có dữ liệu để xếp hạng.")
        return
    st.caption("Điểm = tổng có trọng số của z-score mặt cắt ngang (động lượng 30%, sổ lệnh 25%, khối ngoại 20%, thanh khoản 15%, "
               "chi phí 10%). Chỉ có nghĩa tương đối trong rổ, tại thời điểm tính.")
    zc = [c for c in v.ranking.columns if c.startswith("z_")]
    hm = v.ranking[zc].rename(columns=lambda c: {"z_momentum": "Động lượng", "z_flow": "Sổ lệnh", "z_foreign": "Khối ngoại",
                                                  "z_liquidity": "Thanh khoản", "z_cost": "Chi phí"}[c])
    fig = px.imshow(hm.T, color_continuous_scale=["#b91c1c", "#f8fafc", "#15803d"], zmin=-3, zmax=3, aspect="auto",
                    labels=dict(color="z"))
    fig.update_layout(height=260, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, width="stretch")
    st.dataframe(v.ranking.round(2).rename_axis("Mã")[["rank", "score", "last", "pct_change", "obi3", "net_ratio", "spread_bps", "total_value", "n_factors"]]
                 .rename(columns={"rank": "Hạng", "score": "Điểm", "last": "Giá", "pct_change": "% thay đổi", "obi3": "OBI₃",
                                  "net_ratio": "NN ròng/tổng", "spread_bps": "Spread (bps)", "total_value": "GT khớp (đ)",
                                  "n_factors": "Số yếu tố có dữ liệu"}),
                 width="stretch", height=380,
                 column_config={"GT khớp (đ)": st.column_config.NumberColumn(format="compact")})


def tab_validation(path: str, v: SessionView, freq: str, stamp: str) -> None:
    res, per, truth, dq = cached_validation(path, v.source, freq, stamp)
    if v.is_simulated:
        st.warning("Trên dữ liệu mô phỏng, tín hiệu sổ lệnh được **cài sẵn** vào cơ chế sinh giá. Kết quả dưới đây chỉ xác nhận "
                   "đường ống tính toán chạy đúng — **không** phải bằng chứng về thị trường thật.", icon="⚠️")
    st.subheader("Tín hiệu sổ lệnh có đi trước biến động giá?")
    st.caption(f"Tách theo thời gian — trong mẫu: {', '.join(res['train']) or '—'} · ngoài mẫu: {', '.join(res['test']) or '—'}")
    if res["note"]:
        st.info(res["note"])
    if len(res["table"]):
        st.dataframe(res["table"].rename(columns={"n_bars": "số thanh", "n_obs": "số quan sát", "ic_mean": "IC trung bình",
                                                  "ic_tstat": "t-stat", "hit_rate": "tỷ lệ đúng chiều", "spread_bps": "Q5−Q1 (bps)"}),
                     hide_index=True, width="stretch",
                     column_config={"tỷ lệ đúng chiều": st.column_config.NumberColumn(format="percent"),
                                    "IC trung bình": st.column_config.NumberColumn(format="%.4f")})
        st.caption("IC: tương quan hạng Spearman giữa tín hiệu cuối thanh *t* và lợi suất giá giữa *t→t+h*, tính theo mặt cắt ngang từng "
                   "thanh rồi lấy trung bình. t-stat chưa hiệu chỉnh tự tương quan nên bị thổi phồng phần nào. Q5−Q1: chênh lệch lợi suất "
                   "kế tiếp giữa nhóm 20% tín hiệu cao nhất và thấp nhất — chưa trừ spread và phí, nên không phải lợi nhuận khả thi.")
    if len(per):
        fig = px.bar(per, x="trading_date", y="ic_mean", labels={"trading_date": "Phiên", "ic_mean": "IC (OBI₃, 1 thanh)"})
        fig.update_layout(height=240, margin=dict(l=0, r=0, t=10, b=0), xaxis_type="category")
        st.plotly_chart(fig, width="stretch")
    if truth:
        st.subheader("Bộ cảnh báo so với sự kiện cài sẵn (chỉ có ở dữ liệu mô phỏng)")
        c = st.columns(3)
        c[0].metric("Số sự kiện cài", truth["n_events"])
        c[1].metric("Độ thu hồi (recall)", f"{truth['recall'] * 100:.0f}%")
        c[2].metric("Độ chính xác (precision)", f"{truth['precision'] * 100:.0f}%" if not math.isnan(truth["precision"]) else "—")
        st.dataframe(pd.DataFrame(truth["by_kind"]).T, width="stretch")
    st.subheader("Chất lượng dữ liệu")
    c = st.columns(4)
    c[0].metric("Ảnh chụp đã lưu", f"{dq['n_quotes']:,}")
    c[1].metric("Số phiên", dq["n_sessions"], "≥ 5 theo đề" if dq["n_sessions"] >= 5 else "chưa đủ 5 phiên", delta_color="off", delta_arrow="off")
    c[2].metric("Số mã", dq["n_symbols"])
    c[3].metric("Khoảng trống bất thường", len(dq["gaps"]))
    a, b = st.columns(2)
    a.markdown("**Vấn đề đã ghi nhận theo loại**")
    a.dataframe(dq["issues"].rename("số lần").to_frame() if len(dq["issues"]) else pd.DataFrame({"số lần": []}), width="stretch")
    b.markdown("**Các lần chạy bộ ghi**")
    b.dataframe(dq["runs"].drop(columns=["run_id"], errors="ignore").tail(10), hide_index=True, width="stretch")


def tab_method() -> None:
    st.markdown("""
### Chuỗi xử lý
`NEO API (REST + WebSocket)` → `chuẩn hóa & kiểm tra chất lượng` → `SQLite` → `chỉ báo tài chính` → `cảnh báo / xếp hạng / kiểm chứng` → `giao diện này`

### Công thức chính
| Chỉ báo | Công thức | Ý nghĩa |
|---|---|---|
| Spread | (bán₁ − mua₁) / giá giữa × 10⁴ (bps) | chi phí khứ hồi tức thời |
| OBI₃ | (ΣKL mua − ΣKL bán) / (ΣKL mua + ΣKL bán), 3 mức | > 0: bên mua dày hơn |
| Microprice | (bán₁·KLmua₁ + mua₁·KLbán₁) / (KLmua₁ + KLbán₁) | giá giữa có trọng số độ sâu |
| A/D | (tăng − giảm) / (tăng + giảm) | độ lan tỏa |
| NN ròng/tổng | (mua − bán) / (mua + bán) | mức độ một chiều của khối ngoại |
| Basis | F − S; quy năm (F/S − 1)·365/ngày còn lại | định giá HĐTL so với cơ sở |
| z bền vững | 0,6745·(x − median) / MAD, cửa sổ 60 thanh trước đó | bất thường khi \\|z\\| ≥ 3,5 |
| Điểm nhịp | 50 + 50·Σwᵢcᵢ; w = 30/25/20/15/10% | trạng thái tổng hợp 0–100 |

### Giới hạn cần biết khi đọc số
- **Chỉ 3 mức giá tốt nhất**: OBI và độ sâu bỏ sót lệnh ở xa và lệnh ẩn; trượt giá là cận dưới.
- **Không có dấu thời gian sự kiện cho cổ phiếu**: dùng thời điểm nhận → độ trễ mạng lẫn vào chuỗi thời gian.
- **Rổ theo dõi hữu hạn** (mặc định VN30): khối ngoại và sổ lệnh là của rổ, không phải toàn thị trường; độ rộng lấy từ số của sàn.
- **Trọng số điểm nhịp là lựa chọn thiết kế**, không phải ước lượng; xem độ nhạy ở tab Tổng quan.
- **Điểm nhịp mô tả hiện trạng, không dự báo.** Kiểm chứng IC cho biết mức liên hệ thống kê trong dữ liệu đã thu, chưa trừ chi phí giao dịch.
- **Phiên định kỳ (ATO/ATC)**: giá mức 1 không phải giá giới hạn → chỉ báo sổ lệnh để trống.
- Sản phẩm **không đặt lệnh**; các endpoint giao dịch của NEO API bị chặn trong mã nguồn.

**Đây là công cụ phân tích học thuật, không phải khuyến nghị đầu tư.** Chi tiết và tài liệu tham khảo: `docs/methodology.md`.
""")


def main() -> None:
    try:
        settings = load_settings()
    except ValueError as e:
        st.error(f"Cấu hình không hợp lệ: {e}")
        st.stop()
    try:
        db = get_storage(settings.db_path)
        sources = db.sources()
    except Exception as e:  # noqa: BLE001 - lỗi CSDL phải hiện rõ thay vì trang trắng
        st.error(f"Không mở được cơ sở dữ liệu `{settings.db_path}`: {e}")
        st.stop()

    with st.sidebar:
        st.header("Bộ lọc")
        if not sources:
            st.info("Chưa có dữ liệu.")
            if st.button("Tạo dữ liệu mô phỏng (6 phiên)", type="primary"):
                from neopulse.neo_api.sim import simulate_sessions
                with st.spinner("Đang sinh dữ liệu mô phỏng…"):
                    simulate_sessions(db, 6)
                st.cache_data.clear()
                st.rerun()
            st.caption("Hoặc chạy bộ ghi dữ liệu thật: `neopulse record`")
            st.title("📡 NeoPulse Radar")
            st.stop()
        default = "neo" if "neo" in sources and settings.is_live else sources[-1] if "neo" not in sources else sources[0]
        source = st.radio("Nguồn dữ liệu", sources, index=sources.index(default), format_func=lambda s: SOURCE_LABEL.get(s, s))
        dates = db.trading_dates(source)
        day = st.selectbox("Phiên giao dịch", dates[::-1])
        idx_codes = sorted(db.index_ticks(day, None, source)["index_code"].unique()) or ["VN30"]
        index_code = st.selectbox("Chỉ số", idx_codes, index=idx_codes.index("VN30") if "VN30" in idx_codes else 0)
        symbols = st.multiselect("Giới hạn mã (để trống = cả rổ)", db.symbols("stock", source))
        freq = st.select_slider("Độ dài thanh", ["1min", "2min", "5min"], value="1min")
        order_value = st.number_input("Lệnh giả định để đo trượt giá (triệu đồng)", 50, 20_000, 500, 50) * 1e6
        auto = st.toggle("Tự làm mới mỗi 20 giây", value=(source == "neo"))
        if st.button("Làm mới ngay"):
            st.cache_data.clear()
        st.divider()
        st.caption(f"CSDL: `{settings.db_path}` · chế độ cấu hình: `{settings.mode}`")

    @st.fragment(run_every=20 if auto else None)
    def body() -> None:
        stamp = str(db.last_update(source))
        try:
            v = cached_view(settings.db_path, source, day, index_code, tuple(symbols), freq, order_value, stamp)
        except Exception as e:  # noqa: BLE001
            st.error(f"Lỗi khi tính toán chỉ báo: {type(e).__name__}: {e}")
            return
        header(v, settings)
        if v.status == "no_data":
            st.info(v.status_message)
            return
        tabs = st.tabs(["Tổng quan", "Sổ lệnh & thanh khoản", "Khối ngoại", "Phái sinh", "Cảnh báo", "Xếp hạng",
                        "Kiểm chứng & dữ liệu", "Phương pháp & giới hạn"])
        with tabs[0]:
            tab_overview(v, settings)
            st.download_button("Tải bản tin phiên (HTML)", render_briefing(v), file_name=f"neopulse_{v.source}_{v.trading_date}.html",
                               mime="text/html")
        with tabs[1]:
            tab_book(v, order_value)
        with tabs[2]:
            tab_foreign(v)
        with tabs[3]:
            tab_derivatives(v)
        with tabs[4]:
            tab_alerts(v)
        with tabs[5]:
            tab_ranking(v)
        with tabs[6]:
            tab_validation(settings.db_path, v, freq, stamp)
        with tabs[7]:
            tab_method()

    body()


main()
