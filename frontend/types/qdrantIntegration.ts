export interface QdrantIntegrationSettings {
  enabled: boolean;
  url: string;
  api_key?: string | null;
  collection?: string | null;
  use_kubernetes: boolean;
  use_aws: boolean;
  use_cloud_cost: boolean;
  use_performance: boolean;
  use_security: boolean;
}

export interface QdrantIntegrationResponse {
  enabled: boolean;
  url: string;
  api_key_configured: boolean;
  api_key_preview: string | null;
  collection: string;
  use_kubernetes: boolean;
  use_aws: boolean;
  use_cloud_cost: boolean;
  use_performance: boolean;
  use_security: boolean;
  instance_url_configured: boolean;
  embedding_provider: string;
  embedding_model: string;
}

export interface QdrantTestResponse {
  status: string;
  message: string;
  collection: string;
  vector_count: number | null;
  embedding_provider: string | null;
  embedding_dimension: number | null;
}
