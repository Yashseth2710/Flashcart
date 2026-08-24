import { AccountShell } from "@/components/account/account-shell";
import { HoldList } from "@/components/account/hold-list";
import { SiteHeader } from "@/components/site-header";

export const metadata = { title: "Holds · FlashCart" };

export default function HoldsPage() {
  return (
    <>
      <SiteHeader />
      <AccountShell>
        <HoldList />
      </AccountShell>
    </>
  );
}
