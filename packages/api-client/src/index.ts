import createClient from "openapi-fetch";

import type { components, paths } from "./generated";

export const getApiBaseUrl = () =>
  typeof window === "undefined"
    ? process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
    : process.env.NEXT_PUBLIC_API_URL ?? "";

export const createApiClient = (baseUrl = getApiBaseUrl()) =>
  createClient<paths>({ baseUrl, credentials: "include" });

export type ApiPaths = paths;
export type ApiComponents = components;
