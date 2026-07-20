export interface AwsAccountSettings {
  id?: string | null;
  label: string;
  account_id: string;
  role_arn: string;
  external_id?: string | null;
  default_region?: string | null;
  enabled: boolean;
}

export interface AwsAccountResponse {
  id: string;
  label: string;
  account_id: string;
  role_arn: string;
  external_id_configured: boolean;
  external_id_preview: string | null;
  default_region: string;
  enabled: boolean;
}

export interface AwsIntegrationSettings {
  enabled: boolean;
  accounts: AwsAccountSettings[];
}

export interface AwsIntegrationResponse {
  enabled: boolean;
  accounts: AwsAccountResponse[];
}

export interface AwsTestRequest {
  account_id?: string | null;
}

export interface AwsTestResponse {
  status: string;
  message: string;
  account_id: string | null;
  caller_arn: string | null;
  assumed_role: boolean;
}
