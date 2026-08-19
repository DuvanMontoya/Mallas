"use client";

import { useState, useTransition } from "react";

import {
  exportPersonProfile,
  problemMessage,
  updatePersonProfile,
  type PersonProfileView,
} from "@/lib/api";

export function PersonProfileForm({ initialProfile }: { initialProfile: PersonProfileView }) {
  const [profile, setProfile] = useState(initialProfile);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const institutionControlled = ["INSTITUTION_VERIFIED", "PREEXISTING_UNCLASSIFIED"].includes(profile.verification_method);

  function submit(formData: FormData) {
    setMessage(null);
    setError(null);
    startTransition(async () => {
      const result = await updatePersonProfile({
        first_name: String(formData.get("first_name") ?? ""),
        middle_names: String(formData.get("middle_names") ?? ""),
        first_surname: String(formData.get("first_surname") ?? ""),
        second_surname: String(formData.get("second_surname") ?? ""),
        preferred_name: String(formData.get("preferred_name") ?? ""),
        birth_date: String(formData.get("birth_date") ?? ""),
      }, profile.version);
      if (!result.data) {
        setError(problemMessage(result.failure?.problem ?? null, "No fue posible actualizar tu identidad."));
        return;
      }
      setProfile(result.data);
      setMessage("Tus datos de identidad quedaron actualizados y auditados.");
    });
  }

  function downloadExport() {
    setMessage(null);
    setError(null);
    startTransition(async () => {
      const result = await exportPersonProfile();
      if (!result.data) {
        setError(problemMessage(result.failure?.problem ?? null, "No fue posible preparar la exportación."));
        return;
      }
      const blob = new Blob([JSON.stringify(result.data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "mis-datos-de-identidad.json";
      link.click();
      URL.revokeObjectURL(url);
      setMessage("Exportación preparada en formato JSON.");
    });
  }

  return (
    <div className="profile-settings-grid">
      <section className="panel profile-settings-card" aria-labelledby="identity-data-title">
        <div className="section-heading"><div><p className="eyebrow">Identidad privada</p><h2 id="identity-data-title">Tus nombres y fecha de nacimiento</h2></div></div>
        <p className="muted-copy">La fecha se usa para administración académica y sólo pueden verla tú y administradores con alcance autorizado. La edad se calcula al consultar; no se almacena. La fecha se conserva mientras exista la relación académica y luego según el plazo legal que defina la institución; el sistema no inventa ese plazo.</p>
        {message ? <div className="alert alert-success" role="status">{message}</div> : null}
        {error ? <div className="alert alert-error" role="alert">{error}</div> : null}
        {institutionControlled ? <div className="alert" role="status">Tu identidad académica está bajo control institucional. Para corregir nombres o fecha de nacimiento, solicita una rectificación verificada a administración; la plataforma no sustituirá estos datos con una declaración informal.</div> : null}
        <form className="person-profile-form" action={submit}>
          <fieldset disabled={institutionControlled || pending}>
          <legend className="sr-only">Datos estructurados de identidad</legend>
          <label className="field-group"><span>Primer nombre</span><input name="first_name" required autoComplete="given-name" defaultValue={profile.first_name} /></label>
          <label className="field-group"><span>Otros nombres</span><input name="middle_names" autoComplete="additional-name" defaultValue={profile.middle_names} /></label>
          <label className="field-group"><span>Primer apellido</span><input name="first_surname" required autoComplete="family-name" defaultValue={profile.first_surname} /></label>
          <label className="field-group"><span>Segundo apellido</span><input name="second_surname" defaultValue={profile.second_surname} /></label>
          <label className="field-group"><span>Nombre preferido</span><input name="preferred_name" defaultValue={profile.preferred_name} /></label>
          <label className="field-group"><span>Fecha de nacimiento</span><input name="birth_date" type="date" required autoComplete="bday" defaultValue={profile.birth_date ?? ""} /></label>
          </fieldset>
          <div className="profile-form-summary"><span>Correo de acceso</span><strong>{profile.email}</strong><span>Edad calculada</span><strong>{profile.age ?? "Pendiente"}</strong></div>
          {!institutionControlled ? <button className="button button-primary" type="submit" disabled={pending}>{pending ? "Guardando…" : "Guardar cambios"}</button> : null}
        </form>
      </section>
      <aside className="panel profile-privacy-card" aria-labelledby="privacy-title">
        <p className="eyebrow">Privacidad</p><h2 id="privacy-title">Control de tus datos</h2>
        <p>Descarga una copia portable con tu correo, nombres, apellidos, nombre preferido, fecha de nacimiento y estado de identidad.</p>
        <button className="button button-secondary" type="button" onClick={downloadExport} disabled={pending}>Exportar datos de identidad</button>
        <p className="muted-copy">Esta descarga no incluye historia académica, roles, sesiones ni auditoría. Para una copia integral, presenta una solicitud al responsable institucional de tratamiento de datos; la plataforma no mezcla esas fuentes sin revisión de acceso.</p>
        <p className="muted-copy">La supresión de una cuenta activa requiere revisión institucional porque la historia académica y la auditoría pueden tener deberes legales de conservación. La solicitud nunca borra silenciosamente evidencia curricular.</p>
      </aside>
    </div>
  );
}
