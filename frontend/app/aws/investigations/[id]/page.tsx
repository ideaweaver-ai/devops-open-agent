import { redirect } from "next/navigation";

export default async function AwsInvestigationRedirectPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/investigations/${id}?from=/aws/investigations`);
}
