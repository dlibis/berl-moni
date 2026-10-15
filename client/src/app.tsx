import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { RoutesView } from "./components/routes-view";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
});
export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RoutesView />
      <Toaster
        position="bottom-left"
        visibleToasts={2}
        duration={5000}
        closeButton
        richColors
      />
    </QueryClientProvider>
  );
}
