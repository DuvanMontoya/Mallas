import { NextRequest } from "next/server";

const MAX_REQUEST_BYTES = 12 * 1024 * 1024;
const MAX_RESPONSE_BYTES = 16 * 1024 * 1024;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const API_SEGMENT_PATTERN = /^[A-Za-z0-9_-]+$/;
const MAX_CONCURRENT_BUFFERED_REQUESTS = 4;
let activeBufferedRequests = 0;

class PayloadLimitError extends Error {}

async function readBoundedBody(
  body: ReadableStream<Uint8Array> | null,
  maximumBytes: number,
): Promise<ArrayBuffer | null> {
  if (body === null) return null;
  const reader = body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > maximumBytes) {
        await reader.cancel("payload limit exceeded");
        throw new PayloadLimitError();
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const merged = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    merged.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return merged.buffer;
}

function payloadTooLarge(requestId: string): Response {
  return Response.json(
    {
      type: "https://curriculum.local/problems/payload-too-large",
      title: "Archivo demasiado grande",
      status: 413,
      code: "PAYLOAD_TOO_LARGE",
      detail: "La solicitud supera el tamaño máximo permitido.",
      fields: {},
      correlation_id: requestId,
    },
    {
      status: 413,
      headers: { "cache-control": "no-store", "x-request-id": requestId },
    },
  );
}

function proxyBusy(requestId: string): Response {
  return Response.json(
    { title: "Servicio ocupado", status: 429, code: "PROXY_CAPACITY_EXHAUSTED", detail: "Hay demasiadas cargas simultáneas. Intenta de nuevo en unos segundos.", fields: {}, correlation_id: requestId },
    { status: 429, headers: { "cache-control": "no-store", "retry-after": "2", "x-request-id": requestId } },
  );
}

function safeResponseHeaders(upstream: Headers): Headers {
  const result = new Headers(upstream);
  for (const header of [
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade", "content-length", "content-encoding",
  ]) result.delete(header);
  return result;
}

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  if (!path.length || path.some((segment) => !API_SEGMENT_PATTERN.test(segment))) {
    return Response.json(
      { title: "Ruta inválida", status: 400, code: "INVALID_API_PATH", detail: "La ruta solicitada no es válida.", fields: {} },
      { status: 400, headers: { "cache-control": "no-store" } },
    );
  }
  const backend = process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const target = new URL(`/api/v1/${path.join("/")}`, backend);
  if (!target.pathname.startsWith("/api/v1/")) {
    return Response.json(
      { title: "Ruta inválida", status: 400, code: "INVALID_API_PATH", detail: "La ruta solicitada no es válida.", fields: {} },
      { status: 400, headers: { "cache-control": "no-store" } },
    );
  }
  target.search = request.nextUrl.search;
  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");
  const suppliedRequestId = request.headers.get("x-request-id") ?? "";
  const requestId = UUID_PATTERN.test(suppliedRequestId) ? suppliedRequestId : crypto.randomUUID();
  headers.set("x-request-id", requestId);
  const declaredLength = Number(request.headers.get("content-length") ?? "0");
  if (Number.isFinite(declaredLength) && declaredLength > MAX_REQUEST_BYTES) {
    return payloadTooLarge(requestId);
  }
  const buffersRequest = !["GET", "HEAD"].includes(request.method);
  if (buffersRequest && activeBufferedRequests >= MAX_CONCURRENT_BUFFERED_REQUESTS) {
    return proxyBusy(requestId);
  }
  if (buffersRequest) activeBufferedRequests += 1;
  try {
  let body: ArrayBuffer | null | undefined;
  try {
    body = buffersRequest ? await readBoundedBody(request.body, MAX_REQUEST_BYTES) : undefined;
  } catch (error) {
    if (error instanceof PayloadLimitError) return payloadTooLarge(requestId);
    throw error;
  }
  try {
    const response = await fetch(target, {
      method: request.method,
      headers,
      body,
      redirect: "manual",
    });
    // Materialize the bounded API response before returning it. Passing the
    // upstream stream through kept Undici's parser paused while the downstream
    // client applied backpressure and produced intermittent Node assertions
    // under concurrent requests. Upload request bodies are already bounded by
    // the API and response payloads are JSON, so buffering here is predictable.
    const responseBody =
      request.method === "HEAD" ? null : await readBoundedBody(response.body, MAX_RESPONSE_BYTES);
    return new Response(responseBody, {
      status: response.status,
      statusText: response.statusText,
      headers: safeResponseHeaders(response.headers),
    });
  } catch (error) {
    if (error instanceof PayloadLimitError) {
      return Response.json(
        { title: "Respuesta upstream inválida", status: 502, code: "UPSTREAM_PAYLOAD_TOO_LARGE", detail: "El servicio académico devolvió una respuesta mayor al límite permitido.", fields: {}, correlation_id: requestId },
        { status: 502, headers: { "cache-control": "no-store", "x-request-id": requestId } },
      );
    }
    console.error("api.proxy.unavailable", { requestId, target: target.pathname, error });
    return Response.json(
      {
        type: "https://curriculum.local/problems/service-unavailable",
        title: "Servicio temporalmente no disponible",
        status: 503,
        code: "SERVICE_UNAVAILABLE",
        detail: "No fue posible contactar el servicio académico. Intenta de nuevo.",
        fields: {},
        correlation_id: requestId,
      },
      {
        status: 503,
        headers: {
          "cache-control": "no-store",
          "retry-after": "2",
          "x-request-id": requestId,
        },
      },
    );
  }
  } finally {
    if (buffersRequest) activeBufferedRequests -= 1;
  }
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const PUT = proxy;
export const DELETE = proxy;
export const dynamic = "force-dynamic";
