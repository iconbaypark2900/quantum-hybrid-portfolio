import { use } from "react";

/** Props Next.js passes to client `page.tsx` default exports (async dynamic APIs). */
export type NextClientPageProps = {
  params: Promise<Record<string, string | string[]>>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

/** Dynamic `[id]` segment — `params.id` is the route param. */
export type NextClientPagePropsWithId = {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

/**
 * Next.js 16+ passes `params` and `searchParams` as Promises to Client Components
 * used as `page.tsx` default exports. Unwrap them with `React.use()` per:
 * https://nextjs.org/docs/messages/sync-dynamic-apis
 */
export function useNextPageProps<
  P extends Record<string, string | string[] | undefined>,
  S extends Record<string, string | string[] | undefined>,
>(props: { params: Promise<P>; searchParams: Promise<S> }): {
  params: P;
  searchParams: S;
} {
  return {
    params: use(props.params),
    searchParams: use(props.searchParams),
  };
}
