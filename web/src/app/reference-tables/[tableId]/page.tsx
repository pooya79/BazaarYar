import { ReferenceTableDetailPageView } from "@/view/ReferenceTableDetailPageView";

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
  return <ReferenceTableDetailPageView tableId={tableId} />;
}
