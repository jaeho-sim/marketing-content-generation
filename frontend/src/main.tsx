import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ProducerPage from "@/pages/ProducerPage";
import StatusPage from "@/pages/StatusPage";
import ReviewPage from "@/pages/ReviewPage";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 10_000 } },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/producer" replace />} />
          <Route path="/producer" element={<ProducerPage />} />
          <Route path="/producer/:eventId/status" element={<StatusPage />} />
          <Route path="/review/:eventId" element={<ReviewPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
