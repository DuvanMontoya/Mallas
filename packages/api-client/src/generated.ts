/**
 * Generated contract placeholder for the bootstrap health contract.
 * Regenerate with `pnpm --dir packages/api-client generate` after the API is running.
 */
export interface paths {
  "/health/live": {
    get: operations["health_live"];
  };
  "/health/ready": {
    get: operations["health_ready"];
  };
}

export interface operations {
  health_live: {
    responses: {
      200: { content: { "application/json": { status: string; service: string; version: string } } };
    };
  };
  health_ready: {
    responses: {
      200: { content: { "application/json": { status: string; service: string; database: string } } };
    };
  };
}
