import Link from "next/link";

import { PersonProfileForm } from "@/components/person-profile-form";
import { getPersonProfile } from "@/lib/api";
import { requireAuthenticatedSession } from "@/lib/require-authenticated-session";

export default async function ProfilePage() {
  const { headers } = await requireAuthenticatedSession("/profile");
  const result = await getPersonProfile(headers);
  if (!result.data) {
    return <section className="panel"><p className="eyebrow">Perfil</p><h1>No pudimos cargar tus datos</h1><p>Tu información no se modificó.</p><Link className="button button-secondary" href="/profile">Reintentar</Link></section>;
  }
  return <><header className="route-command"><div><p className="eyebrow accent">Tu cuenta</p><h1>Identidad y privacidad</h1></div></header><PersonProfileForm initialProfile={result.data} /></>;
}
