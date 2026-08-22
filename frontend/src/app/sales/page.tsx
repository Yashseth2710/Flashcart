import { SaleListing } from "@/components/sales/sale-listing";
import { SiteHeader } from "@/components/site-header";

export const metadata = { title: "Sales · FlashCart" };

export default function SalesPage() {
  return (
    <>
      <SiteHeader />
      <SaleListing />
    </>
  );
}
