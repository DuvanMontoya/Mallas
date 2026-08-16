import createClient from "openapi-fetch";

import type { paths } from "./generated";

export const createApiClient = (baseUrl = "http://localhost:8000/api/v1") =>
  createClient<paths>({ baseUrl });

export type ApiPaths = paths;
