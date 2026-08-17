"use client";

import { useEffect } from "react";

import { reportFrontendError, reportWebVital } from "@/lib/observability";

type PerformanceEntryWithValue = PerformanceEntry & {
  value?: number;
  hadRecentInput?: boolean;
};

function observeVital(type: string, onEntry: (entry: PerformanceEntryWithValue) => void): PerformanceObserver | null {
  if (typeof PerformanceObserver === "undefined") return null;
  if (Array.isArray(PerformanceObserver.supportedEntryTypes) && !PerformanceObserver.supportedEntryTypes.includes(type)) {
    return null;
  }
  const observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) onEntry(entry as PerformanceEntryWithValue);
  });
  observer.observe({ type, buffered: true });
  return observer;
}

export function ObservabilityClient() {
  useEffect(() => {
    const onError = (event: ErrorEvent) => reportFrontendError(event.error ?? new Error("WindowError"), { phase: "window" });
    const onRejection = (event: PromiseRejectionEvent) => reportFrontendError(event.reason, { phase: "promise" });
    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onRejection);

    const observers = [
      observeVital("largest-contentful-paint", (entry) =>
        reportWebVital({ name: "LCP", value: entry.startTime }),
      ),
      observeVital("layout-shift", (entry) => {
        if (!entry.hadRecentInput) reportWebVital({ name: "CLS", value: entry.value ?? 0 });
      }),
      observeVital("first-input", (entry) =>
        reportWebVital({ name: "FID", value: entry.startTime }),
      ),
    ].filter((observer): observer is PerformanceObserver => observer !== null);

    return () => {
      window.removeEventListener("error", onError);
      window.removeEventListener("unhandledrejection", onRejection);
      for (const observer of observers) observer.disconnect();
    };
  }, []);

  return null;
}
