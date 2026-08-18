import { NextRequest } from "next/server";

const MAX_REQUEST_BYTES = 12 * 1024 * 1024;
const MAX_STANDARD_REQUEST_BYTES = 512 * 1024;
const MAX_AUTH_REQUEST_BYTES = 32 * 1024;
const MAX_RESPONSE_BYTES = 16 * 1024 * 1024;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const API_SEGMENT_PATTERN = /^[A-Za-z0-9_-]+$/;
const MAX_CONCURRENT_UPLOAD_BUFFERS = 2;
const MAX_CONCURRENT_UPLOAD_BUFFERS_PER_CLIENT = 1;
const MAX_CONCURRENT_AUTH_BUFFERS = 256;
const MAX_CONCURRENT_STANDARD_BUFFERS = 128;
const MAX_CONCURRENT_AUTH_BUFFERS_PER_CLIENT = 2;
const MAX_CONCURRENT_STANDARD_BUFFERS_PER_CLIENT = 4;
const MAX_CONCURRENT_RESPONSE_BUFFERS = 8;
const REQUEST_BODY_TIMEOUT_MS = 30_000;
const AUTH_BODY_TIMEOUT_MS = 5_000;
const STANDARD_BODY_TIMEOUT_MS = 10_000;
const UPSTREAM_TIMEOUT_MS = 30_000;
let activeUploadBuffers = 0;
let activeAuthBuffers = 0;
let activeStandardBuffers = 0;
let activeResponseBuffers = 0;
const authBuffersByClient = new Map<string, number>();
const standardBuffersByClient = new Map<string, number>();
const uploadBuffersByClient = new Map<string, number>();

class PayloadLimitError extends Error {}
class PayloadTimeoutError extends Error {}

async function readBoundedBody(
  body: ReadableStream<Uint8Array> | null,
  maximumBytes: number,
  timeoutMs = REQUEST_BODY_TIMEOUT_MS,
): Promise<ArrayBuffer | null> {
  if (body === null) return null;
  const reader = body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  const deadline = Date.now() + timeoutMs;
  try {
    while (true) {
      const remaining = deadline - Date.now();
      if (remaining <= 0) throw new PayloadTimeoutError();
      let timeout: ReturnType<typeof setTimeout> | undefined;
      const { done, value } = await Promise.race([
        reader.read(),
        new Promise<never>((_, reject) => {
          timeout = setTimeout(() => reject(new PayloadTimeoutError()), remaining);
        }),
      ]).finally(() => {
        if (timeout) clearTimeout(timeout);
      });
      if (done) break;
      size += value.byteLength;
      if (size > maximumBytes) {
        await reader.cancel("payload limit exceeded");
        throw new PayloadLimitError();
      }
      chunks.push(value);
    }
  } finally {
    if (Date.now() >= deadline) await reader.cancel("payload read timeout").catch(() => undefined);
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
    {
      type: "https://curriculum.local/problems/proxy-capacity-exhausted",
      title: "Servicio ocupado",
      status: 429,
      code: "PROXY_CAPACITY_EXHAUSTED",
      detail: "Hay demasiadas solicitudes simultáneas. Intenta de nuevo en unos segundos.",
      fields: {},
      correlation_id: requestId,
    },
    {
      status: 429,
      headers: { "cache-control": "no-store", "retry-after": "2", "x-request-id": requestId },
    },
  );
}

function proxyTimeout(requestId: string): Response {
  return Response.json(
    {
      type: "https://curriculum.local/problems/request-body-timeout",
      title: "La solicitud tardó demasiado",
      status: 408,
      code: "REQUEST_BODY_TIMEOUT",
      detail: "La carga no se recibió dentro del tiempo permitido.",
      fields: {},
      correlation_id: requestId,
    },
    { status: 408, headers: { "cache-control": "no-store", "x-request-id": requestId } },
  );
}

function lengthRequired(requestId: string): Response {
  return Response.json(
    {
      type: "https://curriculum.local/problems/content-length-required",
      title: "Longitud de solicitud requerida",
      status: 411,
      code: "CONTENT_LENGTH_REQUIRED",
      detail: "Las operaciones de escritura deben declarar un tamaño antes de enviar el cuerpo.",
      fields: {},
      correlation_id: requestId,
    },
    { status: 411, headers: { "cache-control": "no-store", "x-request-id": requestId } },
  );
}

function safeResponseHeaders(upstream: Headers): Headers {
  const result = new Headers(upstream);
  for (const header of [
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "content-length",
    "content-encoding",
  ]) {
    result.delete(header);
  }
  return result;
}

function clientKey(request: NextRequest): string {
  const trusted = request.headers.get("x-client-ip")?.trim() ?? "";
  return /^[0-9a-f:.]{3,64}$/i.test(trusted) ? trusted : "direct-client";
}

function releaseClientSlot(slots: Map<string, number>, key: string) {
  const remaining = (slots.get(key) ?? 1) - 1;
  if (remaining > 0) slots.set(key, remaining);
  else slots.delete(key);
}

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  if (!path.length || path.some((segment) => !API_SEGMENT_PATTERN.test(segment))) {
    return Response.json(
      { type: "https://curriculum.local/problems/invalid-api-path", title: "Ruta inválida", status: 400, code: "INVALID_API_PATH", detail: "La ruta solicitada no es válida.", fields: {} },
      { status: 400, headers: { "cache-control": "no-store" } },
    );
  }
  const backend = process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const target = new URL(`/api/v1/${path.join("/")}`, backend);
  if (!target.pathname.startsWith("/api/v1/")) {
    return Response.json(
      { type: "https://curriculum.local/problems/invalid-api-path", title: "Ruta inválida", status: 400, code: "INVALID_API_PATH", detail: "La ruta solicitada no es válida.", fields: {} },
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
  const declaredLengthHeader = request.headers.get("content-length");
  if (declaredLengthHeader !== null && !/^(0|[1-9][0-9]*)$/.test(declaredLengthHeader)) {
    return Response.json(
      { type: "https://curriculum.local/problems/invalid-content-length", title: "Longitud de solicitud inválida", status: 400, code: "INVALID_CONTENT_LENGTH", detail: "Content-Length debe ser un entero decimal no negativo.", fields: {}, correlation_id: requestId },
      { status: 400, headers: { "cache-control": "no-store", "x-request-id": requestId } },
    );
  }
  const declaredLength = Number(declaredLengthHeader ?? "0");
  if (!Number.isSafeInteger(declaredLength)) {
    return payloadTooLarge(requestId);
  }
  if (Number.isFinite(declaredLength) && declaredLength > MAX_REQUEST_BYTES) {
    return payloadTooLarge(requestId);
  }
  const buffersRequest = !["GET", "HEAD"].includes(request.method);
  if (buffersRequest && request.body !== null && declaredLengthHeader === null) {
    return lengthRequired(requestId);
  }
  const contentType = request.headers.get("content-type")?.toLowerCase() ?? "";
  const buffersLargeUpload = buffersRequest && (
    contentType.startsWith("multipart/form-data") || declaredLength > MAX_STANDARD_REQUEST_BYTES
  );
  const buffersAuthRequest = buffersRequest && path[0] === "auth";
  const buffersStandardRequest = buffersRequest && !buffersLargeUpload && !buffersAuthRequest;
  const client = clientKey(request);
  if (buffersLargeUpload && (
    activeUploadBuffers >= MAX_CONCURRENT_UPLOAD_BUFFERS ||
    (uploadBuffersByClient.get(client) ?? 0) >= MAX_CONCURRENT_UPLOAD_BUFFERS_PER_CLIENT
  )) {
    return proxyBusy(requestId);
  }
  if (buffersAuthRequest && (
    activeAuthBuffers >= MAX_CONCURRENT_AUTH_BUFFERS ||
    (authBuffersByClient.get(client) ?? 0) >= MAX_CONCURRENT_AUTH_BUFFERS_PER_CLIENT
  )) return proxyBusy(requestId);
  if (buffersStandardRequest && (
    activeStandardBuffers >= MAX_CONCURRENT_STANDARD_BUFFERS ||
    (standardBuffersByClient.get(client) ?? 0) >= MAX_CONCURRENT_STANDARD_BUFFERS_PER_CLIENT
  )) return proxyBusy(requestId);
  if (buffersLargeUpload) {
    activeUploadBuffers += 1;
    uploadBuffersByClient.set(client, (uploadBuffersByClient.get(client) ?? 0) + 1);
  }
  if (buffersAuthRequest) {
    activeAuthBuffers += 1;
    authBuffersByClient.set(client, (authBuffersByClient.get(client) ?? 0) + 1);
  }
  if (buffersStandardRequest) {
    activeStandardBuffers += 1;
    standardBuffersByClient.set(client, (standardBuffersByClient.get(client) ?? 0) + 1);
  }
  let responseSlotAcquired = false;
  try {
    let body: ArrayBuffer | null | undefined;
    try {
      body = buffersRequest
        ? await readBoundedBody(
            request.body,
            buffersLargeUpload
              ? MAX_REQUEST_BYTES
              : buffersAuthRequest
                ? MAX_AUTH_REQUEST_BYTES
                : MAX_STANDARD_REQUEST_BYTES,
            buffersLargeUpload
              ? REQUEST_BODY_TIMEOUT_MS
              : buffersAuthRequest
                ? AUTH_BODY_TIMEOUT_MS
                : STANDARD_BODY_TIMEOUT_MS,
          )
        : undefined;
    } catch (error) {
      if (error instanceof PayloadLimitError) return payloadTooLarge(requestId);
      if (error instanceof PayloadTimeoutError) return proxyTimeout(requestId);
      throw error;
    }
    if (activeResponseBuffers >= MAX_CONCURRENT_RESPONSE_BUFFERS) {
      return proxyBusy(requestId);
    }
    activeResponseBuffers += 1;
    responseSlotAcquired = true;
    try {
      const response = await fetch(target, {
        method: request.method,
        headers,
        body,
        redirect: "manual",
        signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
      });
      // Materialize a bounded response so the proxy cannot retain an
      // unbounded upstream stream under downstream backpressure.
      const responseBody =
        request.method === "HEAD"
          ? null
          : await readBoundedBody(response.body, MAX_RESPONSE_BYTES);
      const responseHeaders = safeResponseHeaders(response.headers);
      responseHeaders.set("x-request-id", responseHeaders.get("x-request-id") ?? requestId);
      return new Response(responseBody, {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders,
      });
    } catch (error) {
      if (error instanceof PayloadLimitError) {
        return Response.json(
          {
            type: "https://curriculum.local/problems/upstream-payload-too-large",
            title: "Respuesta upstream inválida",
            status: 502,
            code: "UPSTREAM_PAYLOAD_TOO_LARGE",
            detail: "El servicio académico devolvió una respuesta mayor al límite permitido.",
            fields: {},
            correlation_id: requestId,
          },
          {
            status: 502,
            headers: { "cache-control": "no-store", "x-request-id": requestId },
          },
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
    if (responseSlotAcquired) activeResponseBuffers -= 1;
    if (buffersLargeUpload) {
      activeUploadBuffers -= 1;
      releaseClientSlot(uploadBuffersByClient, client);
    }
    if (buffersAuthRequest) {
      activeAuthBuffers -= 1;
      releaseClientSlot(authBuffersByClient, client);
    }
    if (buffersStandardRequest) {
      activeStandardBuffers -= 1;
      releaseClientSlot(standardBuffersByClient, client);
    }
  }
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const PUT = proxy;
export const DELETE = proxy;
export const dynamic = "force-dynamic";
