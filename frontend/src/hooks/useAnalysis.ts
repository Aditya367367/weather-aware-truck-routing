import { useCallback, useRef, useState } from "react";
import { api } from "../api/client";
import type { Analysis, AnalyzeRequest } from "../api/types";

interface State {
  status: "idle" | "loading" | "success" | "error";
  data: Analysis | null; // kept while reloading so the map doesn't blank out
  error: string | null;
}

export function useAnalysis() {
  const [state, setState] = useState<State>({ status: "idle", data: null, error: null });
  const controller = useRef<AbortController | null>(null);

  const run = useCallback(async (request: AnalyzeRequest) => {
    controller.current?.abort(); // latest request wins
    const c = new AbortController();
    controller.current = c;
    setState((s) => ({ ...s, status: "loading", error: null }));
    try {
      const data = await api.analyze(request, c.signal);
      if (!c.signal.aborted) setState({ status: "success", data, error: null });
    } catch (e) {
      if (c.signal.aborted) return;
      setState((s) => ({ ...s, status: "error", error: e instanceof Error ? e.message : "Something went wrong." }));
    }
  }, []);

  return { ...state, run };
}
