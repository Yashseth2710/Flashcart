import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { ProductView } from "@/components/catalogue/product-view";

export default async function ProductPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;

  return (
    <>
      <SiteHeader />
      <ProductView slug={slug} />
      <SiteFooter />
    </>
  );
}
