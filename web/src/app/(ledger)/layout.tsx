import AppLayout from "@/components/AppLayout";
import { LedgerSessionProvider } from "@/context/LedgerSessionContext";

export default function LedgerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <LedgerSessionProvider>
      <AppLayout>{children}</AppLayout>
    </LedgerSessionProvider>
  );
}
