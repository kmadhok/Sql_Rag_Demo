import { configureStore } from '@reduxjs/toolkit';
import chatSlice from './chatSlice';
import dataSlice from './dataSlice';
import uiSlice from './uiSlice';

export const store = configureStore({
  reducer: {
    chat: chatSlice,
    data: dataSlice,
    ui: uiSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;