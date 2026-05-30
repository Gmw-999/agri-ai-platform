import { createContext, useContext, useReducer, ReactNode, Dispatch } from "react";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  hasImage?: boolean;
  imageBase64?: string;
  intent?: string;
  tools_used?: string[];
}

export interface AppState {
  sessionId: string;
  openid: string;
  messages: ChatMessage[];
  isProcessing: boolean;
  tabIndex: number;
}

type Action =
  | { type: "ADD_MESSAGE"; payload: ChatMessage }
  | { type: "SET_PROCESSING"; payload: boolean }
  | { type: "UPDATE_LAST_MESSAGE"; payload: Partial<ChatMessage> }
  | { type: "CLEAR_MESSAGES" }
  | { type: "SET_TAB"; payload: number }
  | { type: "SET_SESSION"; payload: { sessionId: string; openid: string } };

const initialState: AppState = {
  sessionId: `session_${Date.now()}`,
  openid: `user_${Math.random().toString(36).slice(2, 10)}`,
  messages: [],
  isProcessing: false,
  tabIndex: 0,
};

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "ADD_MESSAGE":
      return { ...state, messages: [...state.messages, action.payload] };
    case "SET_PROCESSING":
      return { ...state, isProcessing: action.payload };
    case "UPDATE_LAST_MESSAGE": {
      const msgs = [...state.messages];
      if (msgs.length > 0) {
        msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], ...action.payload };
      }
      return { ...state, messages: msgs };
    }
    case "CLEAR_MESSAGES":
      return { ...state, messages: [], sessionId: `session_${Date.now()}` };
    case "SET_TAB":
      return { ...state, tabIndex: action.payload };
    case "SET_SESSION":
      return { ...state, ...action.payload };
    default:
      return state;
  }
}

const AppContext = createContext<{
  state: AppState;
  dispatch: Dispatch<Action>;
}>({ state: initialState, dispatch: () => {} });

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppState() {
  return useContext(AppContext);
}
