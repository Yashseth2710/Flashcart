import { AccountSettings } from "@/components/account/account-settings";
import { AccountShell } from "@/components/account/account-shell";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

export const metadata = { title: "Settings · FlashCart" };

export default function SettingsPage() {
  return (
    <>
      <SiteHeader />
      <AccountShell>
        <AccountSettings />
      </AccountShell>
      <SiteFooter />
    </>
  );
}
