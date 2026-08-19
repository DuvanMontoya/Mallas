import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { PersonProfileForm } from "@/components/person-profile-form";
import { getPersonProfile, getSessionSnapshot } from "@/lib/api";

export default async function ProfilePage() {
  const cookieHeader = (await cookies()).toString();
  const headers = cookieHeader ? { Cookie: cookieHeader } : undefined;
  const session = await getSessionSnapshot(headers);
  if (session.state !== "authenticated") redirect("/login?next=/profile");
  const result = await getPersonProfile(headers);
  if (!result.data) {
    return <section className="panel"><p className="eyebrow">Perfil</p><h1>No pudimos cargar tus datos</h1><p>Tu información no se modificó.</p><Link className="button button-secondary" href="/profile">Reintentar</Link></section>;
  }
  return <><header className="route-command"><div><p className="eyebrow accent">Tu cuenta</p><h1>Identidad y privacidad</h1></div></header><PersonProfileForm initialProfile={result.data} /></>;
}
