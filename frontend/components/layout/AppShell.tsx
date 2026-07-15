"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useAuth } from "@/context/AuthContext";
import { SystemStatus } from "@/components/SystemStatus";
import {
  getActiveAgent,
  getActiveIntegration,
  PLATFORM,
  PLATFORM_AGENTS,
  PLATFORM_INTEGRATIONS,
} from "@/lib/platform";

function isNavActive(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname.startsWith(href);
}

const AGENT_ICONS: Record<string, ReactNode> = {
  kubernetes: (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden>
      <path
        d="M12 2L4 6v6c0 5 3.5 9.5 8 11 4.5-1.5 8-6 8-11V6l-8-4z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    </svg>
  ),
  aws: (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden>
      <path
        d="M4 14c2-1 4-1.5 8-1.5s6 .5 8 1.5M6 10h12M8 6h8"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <rect x="3" y="4" width="18" height="16" rx="2" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  ),
  "cloud-cost": (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden>
      <path
        d="M12 3v18M7 8h10M7 12h8M7 16h6"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  ),
  "pr-reviewer": (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden>
      <path
        d="M7 8h10M7 12h7M7 16h10"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <rect x="4" y="3" width="16" height="18" rx="2" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  ),
  performance: (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden>
      <path
        d="M4 19V5M4 19h16"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path
        d="M8 15l3-4 3 2 4-6"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  ),
  security: (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden>
      <path
        d="M12 2L4 6v5c0 5.25 3.4 10.15 8 11.25 4.6-1.1 8-6 8-11.25V6l-8-4z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M9 12l2 2 4-4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  ),
};

function getPageTitle(pathname: string, sectionName: string): string {
  const integration = getActiveIntegration(pathname);
  if (integration) {
    const item = integration.nav.find((nav) => isNavActive(pathname, nav.href));
    return item?.label ?? integration.name;
  }
  const agent = getActiveAgent(pathname);
  const item = agent.nav.find((nav) => isNavActive(pathname, nav.href));
  return item?.label ?? agent.name;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const activeAgent = getActiveAgent(pathname);
  const activeIntegration = getActiveIntegration(pathname);
  const sectionName = activeIntegration?.name ?? activeAgent.name;
  const subNav = activeIntegration?.nav ?? activeAgent.nav;
  const pageTitle = getPageTitle(pathname, sectionName);
  const userInitials = user?.email?.slice(0, 2).toUpperCase() ?? "DO";

  return (
    <div className="flex min-h-screen bg-surface">
      {/* Sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 flex w-[var(--sidebar-width)] flex-col border-r border-sidebar-border bg-sidebar-gradient">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-grid-pattern-dark bg-grid opacity-30"
        />

        <div className="relative flex flex-1 flex-col overflow-y-auto">
          {/* Brand */}
          <div className="border-b border-sidebar-border px-5 py-5">
            <Link href="/" className="flex items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-cyan-600 shadow-glow-sm">
                <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5 text-white" aria-hidden>
                  <path
                    d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-bold tracking-tight text-white">
                  {PLATFORM.name}
                </p>
                <p className="truncate text-[10px] font-medium uppercase tracking-wider text-slate-400">
                  Operations Hub
                </p>
              </div>
            </Link>
          </div>

          {/* Agents */}
          <nav className="px-3 py-4">
            <p className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">
              Agents
            </p>
            <ul className="space-y-0.5">
              {PLATFORM_AGENTS.map((agent) => {
                const isActive =
                  !activeIntegration && activeAgent.id === agent.id;
                return (
                  <li key={agent.id}>
                    <Link
                      href={agent.href}
                      className={`group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                        isActive
                          ? "bg-brand-600/90 text-white shadow-sm"
                          : "text-slate-300 hover:bg-sidebar-hover hover:text-white"
                      }`}
                    >
                      <span
                        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
                          isActive
                            ? "bg-white/15 text-white"
                            : "bg-slate-800/80 text-slate-400 group-hover:text-slate-200"
                        }`}
                      >
                        {AGENT_ICONS[agent.id]}
                      </span>
                      <span className="truncate leading-tight">{agent.name}</span>
                      {!agent.available && (
                        <span className="ml-auto rounded bg-amber-500/20 px-1.5 py-0.5 text-[9px] font-bold uppercase text-amber-300">
                          Soon
                        </span>
                      )}
                    </Link>
                    {isActive && subNav.length > 0 && !activeIntegration && (
                      <ul className="ml-11 mt-1 space-y-0.5 border-l border-slate-700/60 pl-3">
                        {subNav.map((item) => {
                          const active = isNavActive(pathname, item.href);
                          return (
                            <li key={item.href}>
                              <Link
                                href={item.href}
                                className={`block rounded-md px-2.5 py-1.5 text-xs transition ${
                                  active
                                    ? "bg-white/15 font-semibold text-white"
                                    : "text-slate-200 hover:bg-white/10 hover:text-white"
                                }`}
                              >
                                {item.label}
                              </Link>
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </li>
                );
              })}
            </ul>
          </nav>

          {/* Integrations */}
          <nav className="border-t border-sidebar-border px-3 py-4">
            <p className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">
              Platform
            </p>
            <ul className="space-y-0.5">
              <li>
                <Link
                  href={PLATFORM_INTEGRATIONS.href}
                  className={`group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                    activeIntegration
                      ? "bg-brand-600/90 text-white shadow-sm"
                      : "text-slate-300 hover:bg-sidebar-hover hover:text-white"
                  }`}
                >
                  <span
                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
                      activeIntegration
                        ? "bg-white/15 text-white"
                        : "bg-slate-800/80 text-slate-400 group-hover:text-slate-200"
                    }`}
                  >
                    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden>
                      <path
                        d="M8 12h8M12 8v8"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                      />
                      <rect
                        x="3"
                        y="3"
                        width="18"
                        height="18"
                        rx="3"
                        stroke="currentColor"
                        strokeWidth="1.5"
                      />
                    </svg>
                  </span>
                  <span>{PLATFORM_INTEGRATIONS.name}</span>
                </Link>
                {activeIntegration && (
                  <ul className="ml-11 mt-1 space-y-0.5 border-l border-slate-700/60 pl-3">
                    {PLATFORM_INTEGRATIONS.nav.map((item) => {
                      const active = isNavActive(pathname, item.href);
                      return (
                        <li key={item.href}>
                          <Link
                            href={item.href}
                                className={`block rounded-md px-2.5 py-1.5 text-xs transition ${
                                  active
                                    ? "bg-white/15 font-semibold text-white"
                                    : "text-slate-200 hover:bg-white/10 hover:text-white"
                                }`}
                          >
                            {item.label}
                          </Link>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </li>
            </ul>
          </nav>

          <div className="flex-1" />

          {/* System status */}
          <div className="border-t border-sidebar-border px-4 py-4">
            <SystemStatus variant="sidebar" />
          </div>

          {/* User */}
          {user && (
            <div className="border-t border-sidebar-border px-4 py-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-cyan-600 text-xs font-bold text-white">
                  {userInitials}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-medium text-slate-200">{user.email}</p>
                  <button
                    type="button"
                    onClick={logout}
                    className="mt-0.5 text-[11px] text-slate-500 transition hover:text-red-300"
                  >
                    Sign out
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* Main content */}
      <div className="flex min-h-screen flex-1 flex-col pl-[var(--sidebar-width)]">
        <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 px-6 py-4 backdrop-blur-md">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
                {sectionName}
              </p>
              <h1 className="text-xl font-bold tracking-tight text-slate-900">{pageTitle}</h1>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {PLATFORM.badges.slice(0, 2).map((badge) => (
                <span
                  key={badge}
                  className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-[11px] font-medium text-slate-600"
                >
                  {badge === "Open Source" && (
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  )}
                  {badge}
                </span>
              ))}
            </div>
          </div>
        </header>

        <main className="content-surface flex-1 px-6 py-6">
          <div className="animate-fade-in">{children}</div>
        </main>
      </div>
    </div>
  );
}
