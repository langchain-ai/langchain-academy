export interface BaseData {
  type: string;
}

// Add new interface for Log structure
export interface LogData extends BaseData {
  type: 'log';
  header: string;
  text: string;
  processedData?: {
    field: string;
    htmlContent: string;
    isMarkdown: boolean;
  }[];
  metadata?: any;
}

// Add new interface for Report Data
export interface ReportData extends BaseData {
  type: 'report';
  output: string;
}

// Keep existing interfaces
export interface BasicData extends BaseData {
  type: 'basic';
  content: string;
}

export interface LanggraphButtonData extends BaseData {
  type: 'langgraphButton';
  link: string;
}

export interface DifferencesData extends BaseData {
  type: 'differences';
  content: string;
  output: string;
}

export interface QuestionData extends BaseData {
  type: 'question';
  content: string;
}

export interface ChatData extends BaseData {
  type: 'chat';
  content: string;
}

// Update Data type to include new interfaces
export type Data = BasicData | LanggraphButtonData | DifferencesData | QuestionData | ChatData | LogData | ReportData;

export interface ChatBoxSettings {
  report_source: string;
  report_type: string;
  tone: string;
}