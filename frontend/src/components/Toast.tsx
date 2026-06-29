"use client";

import { createContext, useCallback, useContext, useReducer, ReactNode } from "react";

type ToastKind = "info" | "success" | "error" | "warning";

interface Toast {
  id: number;
  message: string;
  kind: ToastKind;
}

interface ToastContextValue {
  toast: (message: string, kind?: ToastKind) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

type Action =
  | { type: "ADD"; payload: Toast }
  | { type: "REMOVE"; id: number };

let nextId = 0;

function reducer(state: Toast[], action: Action): Toast[] {
  switch (action.type) {
    case "ADD": return [...state, action.payload];
    case "REMOVE": return state.filter((t) => t.id !== action.id);
    default: return state;
  }
}

const kindStyles: Record<ToastKind, string> = {
  info: "border-accent-cyan text-accent-cyan",
  success: "border-accent-green text-accent-green",
  error: "border-accent-red text-accent-red",
  warning: "border-accent-amber text-accent-amber",
};

const kindIcons: Record<ToastKind, string> = {
  info: "◈",
  success: "✓",
  error: "✕",
  warning: "⚠",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, dispatch] = useReducer(reducer, []);

  const toast = useCallback((message: string, kind: ToastKind = "info") => {
    const id = nextId++;
    dispatch({ type: "ADD", payload: { id, message, kind } });
    setTimeout(() => dispatch({ type: "REMOVE", id }), 4000);
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 space-y-2 pointer-events-none">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`flex items-center gap-2 px-4 py-2.5 rounded border bg-bg-secondary text-sm pointer-events-auto shadow-lg ${kindStyles[t.kind]}`}
          >
            <span className="text-base leading-none">{kindIcons[t.kind]}</span>
            <span>{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside ToastProvider");
  return ctx;
}
