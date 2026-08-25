import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { AdminCatalogue } from "@/components/admin/admin-catalogue";
import { RequireAdmin } from "@/components/admin/require-admin";

export const metadata = { title: "Manage · FlashCart" };

export default function AdminPage() {
  return (
    <>
      <SiteHeader />
      <RequireAdmin>
        <AdminCatalogue />
      </RequireAdmin>
      <SiteFooter />
    </>
  );
}
