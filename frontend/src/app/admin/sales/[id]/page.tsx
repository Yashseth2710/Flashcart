import { AdminSaleDetail } from "@/components/admin/admin-sale-detail";
import { RequireAdmin } from "@/components/admin/require-admin";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

export default async function AdminSaleDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <>
      <SiteHeader />
      <RequireAdmin>
        <AdminSaleDetail saleId={id} />
      </RequireAdmin>
      <SiteFooter />
    </>
  );
}
