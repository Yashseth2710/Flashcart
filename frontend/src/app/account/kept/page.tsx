import { AccountShell } from "@/components/account/account-shell";
import { KeptList } from "@/components/account/kept-list";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

export const metadata = { title: "Kept · FlashCart" };

export default function KeptPage() {
  return (
    <>
      <SiteHeader />
      <AccountShell>
        <KeptList />
      </AccountShell>
      <SiteFooter />
    </>
  );
}
