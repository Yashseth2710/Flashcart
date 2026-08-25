import { AccountShell } from "@/components/account/account-shell";
import { OrderList } from "@/components/account/order-list";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

export const metadata = { title: "Orders · FlashCart" };

export default function OrdersPage() {
  return (
    <>
      <SiteHeader />
      <AccountShell>
        <OrderList />
      </AccountShell>
      <SiteFooter />
    </>
  );
}
