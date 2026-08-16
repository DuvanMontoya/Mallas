import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Curriculum Navigator",
  description: "Navegación curricular y planificación académica explicable.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es-CO">
      <body>{children}</body>
    </html>
  );
}
