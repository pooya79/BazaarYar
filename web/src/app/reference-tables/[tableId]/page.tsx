import { ReferenceTableDetailPage as ReferenceTableDetailFeaturePage } from "@/features/reference-tables";

type ReferenceTableDetailPageProps = {
  params:
    | Promise<{
        tableId: string;
      }>
    | {
        tableId: string;
      };
};

export default async function ReferenceTableDetailPage({
  params,
}: ReferenceTableDetailPageProps) {
  const { tableId } = await params;
  return <ReferenceTableDetailFeaturePage tableId={tableId} />;
}
