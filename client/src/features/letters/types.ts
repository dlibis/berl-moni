export type LetterStatusFilter =
  | "not_analyzed"
  | "failed"
  | "requires_review"
  | "needs_analysis"
  | "relevant"
  | "irrelevant";

export type AnalysisStatus =
  "discovered" | "queued" | "analyzing" | "analyzed" | "failed";

export type LetterItem = {
  slug: string;
  letter_url: string;
  letter_date: string | null;
  ministry: string | null;
  request_numbers: string[];
  first_seen_at: string;
  analysis_status: AnalysisStatus;
  analyzed_at: string | null;
  relevant: boolean;
  complete: boolean;
  needs_analysis: boolean;
  outdated: boolean;
  requires_review: boolean;
  passed: boolean;
  passed_date: string | null;
  passage_detected_at: string | null;
  legacy: boolean;
  last_error: string | null;
  last_error_at: string | null;
  report_available: boolean;
  last_sent_at: string | null;
  send_count: number;
};

export type ReportItem = { code: string; name: string; amount: number };

export type ReportTable = {
  columns: string[];
  rows: (string | number | null)[][];
};

export type ReportUse = { text: string; coalition: boolean };

export type ReportWhyRow = ReportItem & { master: boolean; uses: ReportUse[] };

export type LetterReport = {
  header: { letterhead: string[]; scanned: boolean; source: string };
  summary: { label: string; value: string }[];
  money_flow: {
    metric: string;
    hubs: { name: string; items: ReportItem[] }[];
    destinations: ReportItem[];
    folded: ReportItem[];
    master: string[];
  };
  why: { shown: ReportWhyRow[]; folded: ReportWhyRow[]; sources: string[] };
  appendix: {
    table: { rows: string[][]; spans: [number, number, number][] };
    budget_history: { label: string; table: ReportTable }[];
    decision_links: string[];
    staffing_changes: string;
  };
};

export type LetterDetail = LetterItem & { report: LetterReport | null };

export type LettersPage = { items: LetterItem[]; total: number };
