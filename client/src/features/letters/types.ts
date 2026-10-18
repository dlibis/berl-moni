export type LetterStatusFilter =
  | "not_analyzed"
  | "queued"
  | "relevant"
  | "irrelevant"
  | "failed"
  | "sent"
  | "needs_analysis"
  | "outdated";

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
  legacy: boolean;
  last_error: string | null;
  last_error_at: string | null;
  last_sent_at: string | null;
  send_count: number;
};

export type ReportItem = { code: string; name: string; amount: number };

export type ReportTable = {
  columns: string[];
  rows: (string | number | null)[][];
};

export type LetterReport = {
  header: { letterhead: string[]; scanned: boolean; source: string };
  summary: {
    date: string;
    request_number: string;
    total_amount: string;
    coalition_funds: string;
    program_count: number;
    master_count: number;
  };
  money_flow: {
    metric: string;
    hubs: { name: string; items: ReportItem[] }[];
    destinations: ReportItem[];
    folded: ReportItem[];
  };
  why: {
    code: string;
    name: string;
    amount: number;
    direction: "in" | "out";
    master: boolean;
    uses: string;
  }[];
  appendix: {
    table: ReportTable;
    budget_history: { label: string; table: ReportTable }[];
    decision_links: string[];
    staffing_changes: string;
  };
};

export type LetterDetail = LetterItem & { report: LetterReport | null };

export type LettersPage = { items: LetterItem[]; total: number };
