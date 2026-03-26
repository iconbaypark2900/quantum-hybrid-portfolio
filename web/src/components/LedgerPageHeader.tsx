"use client";

import Link from "next/link";
import { type ReactNode } from "react";

interface LedgerPageHeaderProps {
  title: string;
  subtitle: string;
  primaryAction?: ReactNode;
  labLink?: boolean;
}

export default function LedgerPageHeader({
  title,
  subtitle,
  primaryAction,
  labLink = true,
}: LedgerPageHeaderProps) {
  return (
    <div className="flex flex-col lg:flex-row justify-between items-start lg:items-end gap-4 min-w-0">
      <div className="min-w-0 flex-1">
        <h2 className="font-headline text-3xl font-bold tracking-tighter text-ql-on-surface">
          {title}
        </h2>
        <p className="text-ql-on-surface-variant text-sm mt-1 max-w-2xl">{subtitle}</p>
      </div>
      <div className="flex flex-col sm:flex-row flex-wrap gap-3 w-full lg:w-auto lg:max-w-none items-stretch sm:items-center min-w-0">
        {primaryAction}
        {labLink && (
          <Link
            href="/portfolio"
            className="inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-lg text-xs font-bold primary-gradient text-[#001D33] shadow-md shadow-ql-primary/15 hover:opacity-95 transition-opacity no-underline shrink-0"
          >
            <span className="material-symbols-outlined text-base">science</span>
            PL
          </Link>
        )}
      </div>
    </div>
  );
}
