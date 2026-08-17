import type { Metadata } from "next";
import { cookies } from "next/headers";

import { AppShell } from "@/components/app-shell";
import { ObservabilityClient } from "@/components/observability-client";
import { ThemeProvider } from "@/components/theme-provider";
import { getSessionSnapshot } from "@/lib/api";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Curriculum Navigator",
    template: "%s · Curriculum Navigator",
  },
  description: "Navegación curricular y planificación académica explicable.",
};

export const dynamic = "force-dynamic";

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const cookieHeader = (await cookies()).toString();
  const session = await getSessionSnapshot(cookieHeader ? { Cookie: cookieHeader } : undefined);

  return (
    <html lang="es-CO" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <ObservabilityClient />
          <AppShell session={session}>{children}</AppShell>
        </ThemeProvider>
      </body>
    </html>
  );
}
