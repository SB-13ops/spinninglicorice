import { Suspense } from "react";
import CollectionLive from "../../components/CollectionLive";
export default function CollectionPage(){
  return (
    <Suspense fallback={null}>
      <CollectionLive />
    </Suspense>
  );
}
