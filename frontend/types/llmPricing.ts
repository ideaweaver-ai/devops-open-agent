export interface ModelPricingRates {
  input_per_1m_usd: number;
  output_per_1m_usd: number;
}

export type LlmPricingTable = Record<string, Record<string, ModelPricingRates>>;

export interface LlmPricingTableResponse {
  table: LlmPricingTable;
  source_path: string;
}
