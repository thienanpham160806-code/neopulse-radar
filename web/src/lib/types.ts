/** Hợp đồng dữ liệu (schema_version = 1) do `neopulse export-web` sinh ra. Web chỉ hiển thị, không tính chỉ báo. */
export type DataState = "fresh" | "stale" | "error" | "closed";
export type Phase = "pre" | "open" | "lunch" | "closed";
export type Severity = "CAO" | "TRUNG BÌNH" | "THẤP";
export type Num = number | null;

export interface DataStatus {
  state: DataState;
  reason: string;
  phase: Phase;
  age_seconds: Num;
  stale_after_seconds: number;
}

export interface Meta {
  schema_version: number;
  source: string;
  source_label: string;
  is_simulated: boolean;
  generated_at: string;
  last_update: string | null;
  trading_date: string | null;
  index_code: string;
  data_status: DataStatus;
  n_symbols_computed: number;
  n_symbols_excluded: number;
  excluded_reason: string | null;
  n_sessions: number;
  n_history_sessions: number;
  available_dates: string[];
  order_value_vnd: Num;
  disclaimer: string;
  /** chỉ có ở chế độ web tĩnh (`neopulse publish-static`): dữ liệu KHÔNG phải thời gian thực */
  snapshot_at?: string;
  snapshot_kind?: "end_of_session" | "intraday";
  snapshot_label?: string;
  snapshot_realtime?: boolean;
}

export interface PulseComponent {
  key: string;
  name: string;
  weight: number;
  value: Num;
}
export interface Sensitivity {
  base: Num;
  p05: Num;
  p95: Num;
  label_stability: Num;
}
export interface Pulse {
  score: Num;
  label: string;
  components: PulseComponent[];
  missing: string[];
  sensitivity: Sensitivity | null;
  sigma_pct: Num;
  series: { t: string; index: Num; score: Num }[];
  summary: string[];
  divergence: string | null;
}

export interface IndexRow {
  value: Num;
  change: Num;
  pct_change: Num;
  advances: Num;
  declines: Num;
  no_change: Num;
  n_ceiling: Num;
  n_floor: Num;
  total_value: Num;
  total_volume: Num;
  ad_ratio: Num;
  pct_advancing: Num;
}
export interface IndexBlock {
  code: string;
  row: IndexRow | null;
  series: { t: string; value: Num; pct_change: Num }[];
}
export interface Breadth {
  exchange: Partial<IndexRow> | null;
  universe: Record<string, Num>;
}
export interface RankRow {
  symbol: string;
  rank: number;
  score: Num;
  last: Num;
  pct_change: Num;
  obi3: Num;
  net_ratio: Num;
  spread_bps: Num;
  total_value: Num;
  z: Record<string, Num>;
  n_factors: number;
}
export interface AlertItem {
  t: string;
  symbol: string;
  rule: string;
  rule_name: string;
  severity: Severity;
  value: Num;
  threshold: Num;
  message: string;
}
export interface Alerts {
  total: number;
  by_severity: Record<Severity, number>;
  rule_names: Record<string, string>;
  items: AlertItem[];
}
export interface BookRow {
  symbol: string;
  last: Num;
  pct_change: Num;
  obi3: Num;
  pressure: Num;
  spread_bps: Num;
  depth_value: Num;
  total_value: Num;
  slippage_bps: Num;
  fill_ratio: Num;
  amihud: Num;
  liq_score: Num;
  micro_dev_bps: Num;
  auction: boolean;
}
export interface Book {
  rows: BookRow[];
  /** dạng cột; t = "HH:MM" giờ VN của trading_date */
  series: Record<string, { t: string[]; mid: Num[]; obi3: Num[] }>;
}
export interface ForeignRow {
  symbol: string;
  buy: Num;
  sell: Num;
  net: Num;
  net_ratio: Num;
  participation: Num;
  room_used: Num;
  total_value: Num;
}
export interface Foreign {
  summary: Record<string, Num> | null;
  rows: ForeignRow[];
}
export interface Futures {
  available: boolean;
  state: {
    symbol: string | null;
    label: string | null;
    basis: Num;
    basis_pct: Num;
    z: Num;
    dtm: Num;
    carry_ann: Num;
    mispricing: Num;
  } | null;
  future?: Num;
  spot?: Num;
  series: { t: string; basis: Num; future: Num; spot: Num }[];
}
export type IcRow = Record<string, string | number | null>;
export interface Validation {
  ic: { train: string[]; test: string[]; note: string | null; table: IcRow[] };
  ic_by_session: { trading_date: string; ic_mean: Num }[];
  simulated_signals_are_planted: boolean;
  data_quality: {
    n_quotes: number;
    n_sessions: number;
    n_symbols: number;
    n_gaps: number;
    issues: Record<string, number>;
    runs: Record<string, string | number | null>[];
  };
}

export interface Payload {
  meta: Meta;
  pulse?: Pulse;
  index?: IndexBlock;
  breadth?: Breadth;
  ranking?: RankRow[];
  alerts?: Alerts;
  book?: Book;
  foreign?: Foreign;
  futures?: Futures;
  validation?: Validation;
}

export interface IndexEntry {
  source: string;
  is_simulated: boolean;
  trading_date: string;
  index_code: string;
  path: string;
  generated_at: string;
  pulse_score: Num;
  n_symbols: number;
}
export interface SessionIndex {
  schema_version: number;
  generated_at: string;
  sessions: IndexEntry[];
}
