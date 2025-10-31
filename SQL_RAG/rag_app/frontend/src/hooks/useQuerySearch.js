import { useReducer } from "react";
import { runQuerySearch } from "../services/ragClient.js";

const initialState = {
  isLoading: false,
  data: null,
  error: null,
  lastPayload: null,
};

function reducer(state, action) {
  switch (action.type) {
    case "REQUEST":
      return {
        ...state,
        isLoading: true,
        error: null,
        lastPayload: action.payload,
      };
    case "SUCCESS":
      return {
        ...state,
        isLoading: false,
        data: action.data,
      };
    case "FAILURE":
      return {
        ...state,
        isLoading: false,
        error: action.error,
      };
    case "RESET":
      return { ...initialState };
    default:
      return state;
  }
}

export function useQuerySearch() {
  const [state, dispatch] = useReducer(reducer, initialState);

  const submitQuery = async (payload) => {
    dispatch({ type: "REQUEST", payload });
    try {
      const data = await runQuerySearch(payload);
      dispatch({ type: "SUCCESS", data });
      return data;
    } catch (error) {
      dispatch({
        type: "FAILURE",
        error:
          error?.message ||
          "Failed to run query search. Check server logs for details.",
      });
      throw error;
    }
  };

  const resetQuery = () => {
    dispatch({ type: "RESET" });
  };

  return {
    state,
    submitQuery,
    resetQuery,
  };
}
