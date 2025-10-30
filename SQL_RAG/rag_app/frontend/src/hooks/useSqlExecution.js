import { useReducer } from "react";
import { executeSql } from "../services/ragClient.js";

const initialState = {
  isLoading: false,
  data: null,
  error: null,
};

function reducer(state, action) {
  switch (action.type) {
    case "REQUEST":
      return { ...state, isLoading: true, error: null };
    case "SUCCESS":
      return { ...state, isLoading: false, data: action.data };
    case "FAILURE":
      return { ...state, isLoading: false, error: action.error };
    case "RESET":
      return { ...initialState };
    default:
      return state;
  }
}

export function useSqlExecution() {
  const [state, dispatch] = useReducer(reducer, initialState);

  const executeSqlQuery = async (payload) => {
    dispatch({ type: "REQUEST" });
    try {
      const data = await executeSql(payload);
      dispatch({ type: "SUCCESS", data });
    } catch (error) {
      dispatch({
        type: "FAILURE",
        error:
          error?.message ||
          "SQL execution failed. See API logs for more information.",
      });
    }
  };

  const resetExecution = () => dispatch({ type: "RESET" });

  return {
    state,
    executeSql: executeSqlQuery,
    resetExecution,
  };
}
