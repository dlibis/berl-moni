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
  | "discovered"
  | "queued"
  | "analyzing"
  | "analyzed"
  | "failed";

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

export type LetterReport = {
  source: string;
  scanned: boolean;
  letterhead: string[];
  summary: Record<string, string | number>;
  money_flow: Record<string, unknown>;
  why: Record<string, unknown>[];
  appendix: Record<string, unknown>;
};

export type LetterDetail = LetterItem & { report: LetterReport | null };

export type LettersPage = { items: LetterItem[]; total: number };
