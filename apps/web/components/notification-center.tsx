"use client";

import { Bell, Check, CheckCheck, Mail, Settings2, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";

import {
  getNotificationPreferences,
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  updateNotificationPreference,
  type NotificationPreferenceView,
  type NotificationView,
} from "@/lib/api";
import { messages } from "@/lib/i18n";

const notificationMessages = messages["es-CO"];

function safeNotificationPath(path: string) {
  return path.startsWith("/") && !path.startsWith("//") ? path : "/audit";
}

function eventLabel(eventType: string) {
  if (eventType === "curriculum.revision.published") return notificationMessages.curriculumRevisionPublished;
  return notificationMessages.notifications;
}

function errorMessage(failure: { problem: { detail?: string } | null; unavailable: boolean } | null) {
  if (!failure) return null;
  return failure.problem?.detail ?? (failure.unavailable ? notificationMessages.notificationsUnavailable : notificationMessages.notificationsLoadError);
}

function notificationDate(value: unknown) {
  if (typeof value !== "string") return null;
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return null;
  return new Intl.DateTimeFormat("es-CO", { dateStyle: "short", timeStyle: "short" }).format(date);
}

function preferenceBody(preference: NotificationPreferenceView) {
  return {
    in_app_enabled: preference.in_app_enabled,
    email_enabled: preference.email_enabled,
    locale: preference.locale || "es-CO",
  };
}

export function NotificationCenter({ enabled }: { enabled: boolean }) {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationView[]>([]);
  const [preferences, setPreferences] = useState<NotificationPreferenceView[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [preferencesOpen, setPreferencesOpen] = useState(false);
  const [savingPreference, setSavingPreference] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const panelId = useId();
  const headingId = useId();
  const triggerRef = useRef<HTMLButtonElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const wasOpenRef = useRef(false);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    void getNotifications({ limit: 50 }).then((result) => {
      if (cancelled) return;
      if (result.data) {
        setNotifications(result.data.items);
        setUnreadCount(result.data.unread_count);
      } else {
        setError(errorMessage(result.failure));
      }
    });
    return () => {
      cancelled = true;
    };
  }, [enabled]);

  useEffect(() => {
    if (!open) return;
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        setPreferencesOpen(false);
      }
    }
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [open]);

  useEffect(() => {
    if (open) {
      headingRef.current?.focus();
    } else if (wasOpenRef.current) {
      triggerRef.current?.focus();
    }
    wasOpenRef.current = open;
  }, [open]);

  if (!enabled) return null;

  async function refreshCenter() {
    setLoading(true);
    setError(null);
    const [notificationResult, preferenceResult] = await Promise.all([
      getNotifications({ limit: 50 }),
      getNotificationPreferences(),
    ]);
    if (notificationResult.data) {
      setNotifications(notificationResult.data.items);
      setUnreadCount(notificationResult.data.unread_count);
    }
    if (preferenceResult.data) setPreferences(preferenceResult.data.items);
    const failure = notificationResult.failure ?? preferenceResult.failure;
    if (failure) setError(errorMessage(failure));
    setLoading(false);
  }

  function closePanel() {
    setOpen(false);
    setPreferencesOpen(false);
  }

  function toggleOpen() {
    if (open) {
      closePanel();
      return;
    }
    setOpen(true);
    void refreshCenter();
  }

  async function handleRead(notification: NotificationView) {
    if (notification.read_at) return;
    const readAt = new Date().toISOString();
    setNotifications((current) => current.map((item) => item.id === notification.id ? { ...item, read_at: readAt } : item));
    setUnreadCount((current) => Math.max(0, current - 1));
    const result = await markNotificationRead(notification.id);
    if (!result.data) {
      setError(errorMessage(result.failure));
      void refreshCenter();
    }
  }

  async function handleReadAll() {
    if (!unreadCount) return;
    const result = await markAllNotificationsRead();
    if (result.data) {
      const readAt = new Date().toISOString();
      setNotifications((current) => current.map((item) => ({ ...item, read_at: item.read_at ?? readAt })));
      setUnreadCount(0);
    } else {
      setError(errorMessage(result.failure));
    }
  }

  async function handlePreferenceChange(
    preference: NotificationPreferenceView,
    patch: Partial<Pick<NotificationPreferenceView, "in_app_enabled" | "email_enabled" | "locale">>,
  ) {
    const next = { ...preference, ...patch };
    setSavingPreference(preference.event_type);
    setError(null);
    const result = await updateNotificationPreference(preference.event_type, preferenceBody(next));
    if (result.data) {
      setPreferences((current) => current.map((item) => item.event_type === result.data?.event_type ? result.data : item));
    } else {
      setError(errorMessage(result.failure));
    }
    setSavingPreference(null);
  }

  return (
    <div className="notification-center">
      <button
        className="icon-button notification-trigger"
        type="button"
        ref={triggerRef}
        aria-label={notificationMessages.openNotifications}
        aria-expanded={open}
        aria-controls={panelId}
        title={notificationMessages.notifications}
        onClick={toggleOpen}
      >
        <Bell size={17} strokeWidth={1.8} aria-hidden="true" />
        {unreadCount > 0 ? (
          <span className="notification-badge" aria-label={`${unreadCount} ${notificationMessages.unreadNotifications}`}>
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        ) : null}
      </button>
      {open ? (
        <section className="popover-panel notification-panel" id={panelId} aria-labelledby={headingId} role="dialog">
          <div className="notification-panel-header">
            <div>
          <h2 id={headingId} ref={headingRef} tabIndex={-1}>{notificationMessages.notifications}</h2>
              <p>{unreadCount ? `${unreadCount} ${notificationMessages.unreadNotifications}` : notificationMessages.allNotificationsRead}</p>
            </div>
            <button className="notification-close" type="button" aria-label={notificationMessages.closeNotifications} onClick={closePanel}>
              <X size={16} aria-hidden="true" />
            </button>
          </div>

          {loading ? <p className="notification-status" role="status">{notificationMessages.loadingNotifications}</p> : null}
          {error ? <p className="notification-status notification-status-error" role="alert">{error}</p> : null}
          {!loading && !notifications.length ? <p className="notification-status">{notificationMessages.noNotifications}</p> : null}
          {notifications.length ? (
            <ul className="notification-list">
              {notifications.map((notification) => {
                const date = notificationDate(notification.created_at);
                return (
                  <li className={notification.read_at ? "notification-item" : "notification-item notification-item-unread"} key={notification.id}>
                    <div className="notification-item-copy">
                      <Link href={safeNotificationPath(notification.link_path)} onClick={() => void handleRead(notification)}>
                        <strong>{notification.title}</strong>
                        <span>{notification.body}</span>
                      </Link>
                      {date ? <time dateTime={typeof notification.created_at === "string" ? notification.created_at : undefined}>{date}</time> : null}
                    </div>
                    {!notification.read_at ? (
                      <button className="notification-read-button" type="button" aria-label={`${notificationMessages.markAsRead}: ${notification.title}`} onClick={() => void handleRead(notification)}>
                        <Check size={15} aria-hidden="true" />
                        <span>{notificationMessages.markAsRead}</span>
                      </button>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          ) : null}

          <div className="notification-actions">
            <button className="button button-quiet notification-action" type="button" onClick={() => void handleReadAll()} disabled={!unreadCount}>
              <CheckCheck size={15} aria-hidden="true" /> {notificationMessages.markAllAsRead}
            </button>
            <button className="button button-quiet notification-action" type="button" onClick={() => setPreferencesOpen((current) => !current)} aria-expanded={preferencesOpen}>
              <Settings2 size={15} aria-hidden="true" /> {notificationMessages.notificationPreferences}
            </button>
          </div>

          {preferencesOpen && preferences.length ? (
            <div className="notification-preferences">
              <h3>{notificationMessages.notificationPreferences}</h3>
              {preferences.map((preference) => (
                <fieldset key={preference.event_type} disabled={savingPreference === preference.event_type}>
                  <legend>{eventLabel(preference.event_type)}</legend>
                  <label>
                    <input
                      type="checkbox"
                      checked={preference.in_app_enabled}
                      onChange={(event) => void handlePreferenceChange(preference, { in_app_enabled: event.target.checked })}
                    />
                    {notificationMessages.inAppNotifications}
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={preference.email_enabled}
                      onChange={(event) => void handlePreferenceChange(preference, { email_enabled: event.target.checked })}
                    />
                    <Mail size={14} aria-hidden="true" /> {notificationMessages.emailNotifications}
                  </label>
                  <label className="notification-locale-field">
                    <span>{notificationMessages.notificationLanguage}</span>
                    <select value={preference.locale} onChange={(event) => void handlePreferenceChange(preference, { locale: event.target.value })}>
                      <option value="es-CO">Español (Colombia)</option>
                      <option value="en">English</option>
                    </select>
                  </label>
                </fieldset>
              ))}
              <p className="notification-privacy-note">{notificationMessages.notificationPrivacyNote}</p>
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
