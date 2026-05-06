export type UserRole = "student" | "teacher" | "admin";

export type AuthUser = {
  id?: string;
  username: string;
  role: UserRole;
  display_name?: string | null;
};

export type LoginRequest = {
  username: string;
  password: string;
};

export type LoginResponse = {
  token_type: "Bearer";
  access_token: string;
  expires_in: number;
  user: AuthUser;
};

export type AuthSession = {
  accessToken: string;
  expiresIn: number;
  user: AuthUser;
};
