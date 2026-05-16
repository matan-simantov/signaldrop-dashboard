export interface Overview {
  total_posts: number;
  channels: number;
  date_range: {
    start: string;
    end: string;
  };
  monthly_volumes: Record<string, number>;
  declining_trends_found: number;
  top_trends_included: number;
}

export interface Trend {
  rank: number;
  topic: string;
  group_id?: string;
  label?: string;
  representative_topic?: string;
  member_topics?: string[];
  sep_mentions: number;
  dec_mentions: number;
  sep_share: number;
  dec_share: number;
  absolute_delta: number;
  decline_percentage: number;
  ranking_score: number;
  display_quality_score?: number;
  is_displayable?: boolean;
  display_exclusion_reason?: string;
  quality_notes?: string[];
  consolidation?: {
    member_count: number;
    merge_method: string;
    confidence: number;
    evidence_summary: string;
  };
}

export interface TrendTimeseries {
  monthly_shares: Record<string, number>;
  monthly_mentions: Record<string, number>;
}

export interface ChannelScore {
  channel: string;
  sep_mentions: number;
  dec_mentions: number;
  sep_share: number;
  dec_share: number;
  decline_percentage: number;
}

export interface TrendDetail {
  trend: Trend;
  timeseries: TrendTimeseries;
  channels: ChannelScore[];
  representative_posts: {
    id: string;
    published_at: string;
    content: string;
    channel: string;
  }[];
}

export interface Methodology {
  description: string;
  ranking?: string;
  steps: string[];
  normalization: string;
  filters_applied?: Record<string, string>;
  thresholds: Record<string, number>;
  limitations: string[];
}

export interface AiLabel {
  short_label?: string;
  label: string;
  category: string;
  explanation: string;
}

export type AiLabels = Record<string, AiLabel>;

export interface AiInsightFinding {
  title: string;
  value?: string;
  detail: string;
}

export interface AiInsights {
  headline?: string;
  findings?: AiInsightFinding[];
  caveat?: string;
}
