"use client";

import {
  BookOpen,
  CalendarClock,
  CheckCircle2,
  ChevronDown,
  ClipboardCheck,
  BarChart3,
  FileSearch,
  History,
  LayoutDashboard,
  LogIn,
  LogOut,
  Map,
  Menu,
  Network,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState, useTransition } from "react";

import { signOut, type SessionSnapshot } from "@/lib/api";
import { messages } from "@/lib/i18n";

import { ThemeToggle } from "./theme-toggle";
import { NotificationCenter } from "./notification-center";
import { Alert } from "./ui/alert";
import { StatusBadge } from "./ui/status-badge";

type NavigationItem = {
  href: string;
  label: string;
  shortLabel: string;
  icon: typeof LayoutDashboard;
};

const publicNavigation: NavigationItem[] = [
  { href: "/curriculum", label: messages["es-CO"].curriculum, shortLabel: "Malla", icon: Map },
  { href: "/offerings", label: messages["es-CO"].offerings, shortLabel: "Oferta", icon: BookOpen },
  { href: "/graph", label: messages["es-CO"].graph, shortLabel: "Grafo", icon: Network },
  { href: "/", label: messages["es-CO"].home, shortLabel: "Inicio", icon: LayoutDashboard },
];

const studentNavigation: NavigationItem[] = [
  { href: "/planner", label: messages["es-CO"].planner, shortLabel: "Plan", icon: CalendarClock },
  { href: "/audit", label: messages["es-CO"].audit, shortLabel: "Auditoría", icon: ClipboardCheck },
  { href: "/history", label: messages["es-CO"].history, shortLabel: "Historia", icon: History },
  { href: "/analytics", label: messages["es-CO"].analytics, shortLabel: "Analítica", icon: BarChart3 },
];

const editorialNavigation: NavigationItem[] = [
  { href: "/sources", label: messages["es-CO"].sources, shortLabel: "Fuentes", icon: FileSearch },
];

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

function NavigationLinks({ items, pathname, mobile = false, onNavigate }: { items: NavigationItem[]; pathname: string; mobile?: boolean; onNavigate?: () => void }) {
  return (
    <ul className={mobile ? "mobile-nav-list" : "nav-list"}>
      {items.map(({ href, label, shortLabel, icon: Icon }) => {
        const active = isActive(pathname, href);
        return (
          <li key={href}>
            <Link className={active ? "nav-link active" : "nav-link"} href={href} aria-current={active ? "page" : undefined} onClick={onNavigate}>
              <Icon size={18} strokeWidth={1.8} aria-hidden="true" />
              <span className="nav-label">{label}</span>
              {mobile ? <span className="nav-short-label">{shortLabel}</span> : null}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

function roleLabel(roles: string[]) {
  if (roles.includes("ADMIN")) return "Admin";
  if (roles.includes("REVIEWER")) return "Revisor";
  if (roles.includes("EDITOR")) return "Editor";
  if (roles.includes("ADVISOR")) return "Asesor";
  if (roles.includes("ANALYST")) return "Analista";
  return "Estudiante";
}

export function AppShell({ children, session }: { children: React.ReactNode; session: SessionSnapshot }) {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const mobileMenuToggleRef = useRef<HTMLButtonElement>(null);
  const mobileMoreMenuRef = useRef<HTMLElement>(null);
  const hadOpenMobileMenu = useRef(false);
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const isAuthRoute = pathname === "/login";
  const canSeeEditorial = session.user?.roles.some((role) => ["EDITOR", "REVIEWER", "ADMIN"].includes(role)) ?? false;
  // Student is the default product persona and older accounts can legitimately
  // have no explicit STUDENT assignment. Editorial-only accounts must opt in.
  const canSeeStudentWorkspace = Boolean(session.user?.student_profile_id) || (session.user?.roles.includes("STUDENT") ?? false);
  const visibleNavigation = canSeeStudentWorkspace
    ? [publicNavigation[0], studentNavigation[0], publicNavigation[1], studentNavigation[1], studentNavigation[2], publicNavigation[3], publicNavigation[2], studentNavigation[3]]
    : publicNavigation;
  const allVisibleNavigation = canSeeEditorial ? [...visibleNavigation, ...editorialNavigation] : visibleNavigation;

  useEffect(() => {
    if (isAuthRoute) return;
    if (mobileMenuOpen) {
      const firstMenuControl = mobileMoreMenuRef.current?.querySelector<HTMLElement>("a, button, input, select, textarea");
      window.queueMicrotask(() => firstMenuControl?.focus());
      const closeOnEscape = (event: KeyboardEvent) => {
        if (event.key !== "Escape") return;
        event.preventDefault();
        setMobileMenuOpen(false);
      };
      document.addEventListener("keydown", closeOnEscape);
      hadOpenMobileMenu.current = true;
      return () => document.removeEventListener("keydown", closeOnEscape);
    }
    if (hadOpenMobileMenu.current) {
      window.queueMicrotask(() => mobileMenuToggleRef.current?.focus());
      hadOpenMobileMenu.current = false;
    }
  }, [isAuthRoute, mobileMenuOpen]);

  function handleLogout() {
    setLogoutError(null);
    startTransition(async () => {
      const failure = await signOut();
      if (failure) {
        setLogoutError(failure.problem?.detail ?? "No se pudo cerrar la sesión.");
        return;
      }
      router.replace("/login");
      router.refresh();
    });
  }

  if (isAuthRoute) {
    return (
      <div className="auth-frame">
        <a className="skip-link" href="#main-content">{messages["es-CO"].skipToContent}</a>
        <header className="auth-header">
          <Link className="brand brand-dark" href="/" aria-label={`${messages["es-CO"].brandName} ${messages["es-CO"].brandProduct}`}>
            <span className="brand-mark" aria-hidden="true">CN</span>
            <span><strong>{messages["es-CO"].brandName}</strong><span>{messages["es-CO"].brandProduct}</span></span>
          </Link>
          <ThemeToggle />
        </header>
        <main id="main-content" className="auth-content" tabIndex={-1}>{children}</main>
      </div>
    );
  }

  return (
    <div className="app-frame">
      <a className="skip-link" href="#main-content">{messages["es-CO"].skipToContent}</a>
      <aside className="sidebar" aria-label={messages["es-CO"].navigationLabel}>
        <Link className="brand" href="/" aria-label={`${messages["es-CO"].brandName} ${messages["es-CO"].brandProduct}`}>
          <span className="brand-mark" aria-hidden="true">CN</span>
          <span><strong>{messages["es-CO"].brandName}</strong><span>{messages["es-CO"].brandProduct}</span></span>
        </Link>
        <nav className="main-nav" aria-label={messages["es-CO"].navigationLabel}>
          <NavigationLinks items={visibleNavigation.slice(0, 5)} pathname={pathname} />
          {visibleNavigation.length > 5 ? <div className="nav-section"><p className="nav-section-label">Más herramientas</p><NavigationLinks items={visibleNavigation.slice(5)} pathname={pathname} /></div> : null}
          {canSeeEditorial ? (
            <div className="nav-section">
              <p className="nav-section-label">Editorial</p>
              <NavigationLinks items={editorialNavigation} pathname={pathname} />
            </div>
          ) : null}
        </nav>
        <div className="sidebar-note">
          <CheckCircle2 size={16} aria-hidden="true" />
          <span>{messages["es-CO"].normativeData}</span>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">{messages["es-CO"].workspaceLabel}</p>
            <p className="breadcrumb" aria-live="polite">{allVisibleNavigation.find((item) => isActive(pathname, item.href))?.label ?? messages["es-CO"].workspaceLabel}</p>
          </div>
          <div className="topbar-actions">
            <NotificationCenter enabled={session.state === "authenticated" && Boolean(session.user)} />
            <ThemeToggle />
            {session.state === "authenticated" && session.user ? (
              <details className="profile-menu">
                <summary className="profile-chip" aria-label={`${session.user.email}, ${roleLabel(session.user.roles)}. Abrir menú de perfil`}>
                  <span className="avatar" aria-hidden="true">{session.user.email.slice(0, 2).toUpperCase()}</span>
                  <span className="profile-copy"><strong>{session.user.email}</strong><small>{roleLabel(session.user.roles)}</small></span>
                  <ChevronDown size={15} aria-hidden="true" />
                </summary>
                <div className="profile-popover">
                  <p className="popover-label">{messages["es-CO"].connectionAuthenticated}</p>
                  <button className="menu-action" type="button" onClick={handleLogout} disabled={isPending}>
                    <LogOut size={16} aria-hidden="true" />
                    {isPending ? "Cerrando…" : messages["es-CO"].signOut}
                  </button>
                  {logoutError ? <p className="menu-error" role="alert">{logoutError}</p> : null}
                </div>
              </details>
            ) : (
              <Link className="button button-secondary sign-in-link" href="/login">
                <LogIn size={16} aria-hidden="true" /> {messages["es-CO"].signIn}
              </Link>
            )}
          </div>
        </header>

        {session.state === "unavailable" ? (
          <div className="connection-banner" role="status">
            <span className="connection-dot" aria-hidden="true" />
            {messages["es-CO"].connectionUnavailable}
          </div>
        ) : null}
        {session.state === "anonymous" ? (
          <div className="connection-banner connection-banner-neutral" role="status">
            <span className="connection-dot" aria-hidden="true" />
            {messages["es-CO"].connectionAnonymous}
          </div>
        ) : null}

        <main id="main-content" className="content-area" tabIndex={-1}>{children}</main>
        <footer className="content-footer">
          <span>{messages["es-CO"].engineVersion}</span>
          <Link href="/sources">{messages["es-CO"].evidenceLink}</Link>
        </footer>
      </div>

      <nav className="mobile-nav" aria-label={`${messages["es-CO"].navigationLabel} móvil`}>
        <NavigationLinks items={visibleNavigation.slice(0, 5)} pathname={pathname} mobile />
        <button ref={mobileMenuToggleRef} className="mobile-menu-toggle" type="button" aria-expanded={mobileMenuOpen} aria-controls="mobile-more-menu" onClick={() => setMobileMenuOpen((open) => !open)}>
          {mobileMenuOpen ? <X size={19} aria-hidden="true" /> : <Menu size={19} aria-hidden="true" />}
          <span>{mobileMenuOpen ? messages["es-CO"].closeMenu : messages["es-CO"].menu}</span>
        </button>
      </nav>
      {mobileMenuOpen ? (
        <nav ref={mobileMoreMenuRef} className="mobile-more-menu" id="mobile-more-menu" aria-label="Más opciones de navegación">
          <NavigationLinks items={visibleNavigation.slice(5)} pathname={pathname} onNavigate={() => setMobileMenuOpen(false)} />
          {canSeeEditorial ? <NavigationLinks items={editorialNavigation} pathname={pathname} onNavigate={() => setMobileMenuOpen(false)} /> : null}
        </nav>
      ) : null}
      {logoutError ? <Alert tone="error">{logoutError}</Alert> : null}
    </div>
  );
}
