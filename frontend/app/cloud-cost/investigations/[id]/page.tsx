import { redirect } from "next/navigation";

export default async function CloudCostInvestigationRedirectPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/investigations/${id}?from=/cloud-cost/investigations`);
}
