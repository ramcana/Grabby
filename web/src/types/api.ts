export interface HistoryItem {
  id: string;
  url: string;
  title?: string;
  uploader?: string;
  status: 'completed' | 'failed' | 'cancelled';
  file_size?: number;
  duration?: string;
  completed_at: string;
  error_message?: string;
}

export interface HistoryResponse {
  items: HistoryItem[];
  total: number;
  offset: number;
  limit: number;
}

export interface DownloadItem {
  id: string;
  url: string;
  title?: string;
  status: 'pending' | 'downloading' | 'completed' | 'failed' | 'cancelled';
  progress_percent: number;
  speed?: string;
  eta?: string;
  downloaded_bytes: number;
  total_bytes: number;
  filename?: string;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
}

export interface QueueResponse {
  items: DownloadItem[];
  total: number;
}

export interface StatsResponse {
  total_downloads: number;
  completed_downloads: number;
  failed_downloads: number;
  total_size: number;
  active_downloads: number;
}
