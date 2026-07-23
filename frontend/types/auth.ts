export interface AuthUser {
  id: string;
  email: string;
  created_at: string;
  must_change_password?: boolean;
  llm_daily_budget_usd?: number | null;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignUpRequest {
  email: string;
  password: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}
