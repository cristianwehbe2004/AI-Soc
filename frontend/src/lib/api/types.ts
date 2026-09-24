import type { components } from "./schema";

export type ApiUser = components["schemas"]["UserResponse"];
export type TokenResponse = components["schemas"]["TokenResponse"];
export type HealthResponse = components["schemas"]["HealthResponse"];
export type RoleName = ApiUser["role_name"];

export interface ApiErrorBody {
  detail?: string | Array<{ loc?: Array<string | number>; msg?: string }>;
}
