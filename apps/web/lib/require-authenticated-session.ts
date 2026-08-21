import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { getSessionSnapshot, type SessionSnapshot } from "@/lib/api";

export type AuthenticatedRequest = {
  headers: HeadersInit | undefined;
  session: SessionSnapshot & { state: "authenticated" };
};

/**
 * Authoritative server-side guard for every product route.
 *
 * `proxy.ts` makes the common no-cookie case inexpensive, but a cookie's
 * presence is not proof of a valid session. This check consults the backend on
 * every protected render and fails closed when the identity service cannot
 * validate the session.
 */
export async function requireAuthenticatedSession(nextPath: string): Promise<AuthenticatedRequest> {
  const cookieHeader = (await cookies()).toString();
  const headers = cookieHeader ? { Cookie: cookieHeader } : undefined;
  const session = await getSessionSnapshot(headers);

  if (session.state !== "authenticated" || !session.user) {
    redirect(`/login?next=${encodeURIComponent(nextPath)}`);
  }
  if (session.user.must_change_password && nextPath !== "/change-password") {
    redirect("/change-password");
  }

  return { headers, session: session as AuthenticatedRequest["session"] };
}
