import { AdminSales } from "@/components/admin/admin-sales";
import { RequireAdmin } from "@/components/admin/require-admin";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

export const metadata = { title: "Sales · Manage · FlashCart" };

export default function AdminSalesPage() {
  return (
    <>
      <SiteHeader />
      <RequireAdmin>
        <AdminSales />
      </RequireAdmin>
      <SiteFooter />
    </>
  );
}
