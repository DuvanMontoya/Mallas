import Link from "next/link";

import { messages } from "@/lib/i18n";

import { EmptyState } from "./ui/empty-state";

export function ModuleLanding({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <div className="page-shell module-shell">
      <Link className="text-link" href="/">← {messages["es-CO"].backToSummary}</Link>
      <section className="panel module-panel">
        <p className="eyebrow accent">{eyebrow}</p>
        <h1>{title}</h1>
        <EmptyState
          title={messages["es-CO"].preparedModule}
          description={description || messages["es-CO"].preparedModuleDescription}
          action={<Link className="button button-primary" href="/">{messages["es-CO"].continueHome}</Link>}
        />
      </section>
    </div>
  );
}
