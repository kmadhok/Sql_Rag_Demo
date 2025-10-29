import api from './api';
import { ChatRequest, ChatResponse } from '../types/api';

export const chatService = {
  // Send a message to the chat assistant
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    try {
      console.log('Sending chat request:', request);
      const response = await api.post<any>('/chat/', {
        message: request.message,
        agent_type: request.agentType,
        session_id: request.sessionId,
        user_id: request.userId
      });
      
      console.log('Chat response:', response.data);
      
      // Map response fields to frontend types
      const chatResponse: ChatResponse = {
        message: response.data.message,
        sessionId: response.data.session_id,
        timestamp: response.data.timestamp,
        agentUsed: response.data.agent_used,
        sqlQuery: response.data.sql_query,
        sqlResult: response.data.sql_result,
        sources: response.data.sources || [],
        tokenUsage: response.data.token_usage || { prompt: 0, completion: 0, total: 0 },
        contextUtilization: response.data.context_utilization,
      };
      
      return chatResponse;
    } catch (error: any) {
      console.error('Error sending chat message:', error);
      throw new Error(
        error.response?.data?.detail || 
        error.message || 
        'Failed to send message'
      );
    }
  },

  // Create a new chat session
  async createSession(userId?: string): Promise<{ sessionId: string; message: string }> {
    try {
      const response = await api.post('/chat/sessions', { user_id: userId });
      return {
        sessionId: response.data.session_id,
        message: response.data.message
      };
    } catch (error: any) {
      console.error('Error creating session:', error);
      throw new Error(
        error.response?.data?.detail || 
        error.message || 
        'Failed to create session'
      );
    }
  },

  // Get session history
  async getHistory(sessionId: string): Promise<{ messages: any[] }> {
    try {
      const response = await api.get(`/chat/sessions/${sessionId}/messages`);
      return response.data.data;
    } catch (error: any) {
      console.error('Error getting history:', error);
      throw new Error(
        error.response?.data?.detail || 
        error.message || 
        'Failed to get history'
      );
    }
  },

  // Get all sessions for a user
  async getUserSessions(userId: string): Promise<{ sessions: any[] }> {
    try {
      const response = await api.get(`/chat/sessions/${userId}`);
      return response.data.data;
    } catch (error: any) {
      console.error('Error getting user sessions:', error);
      throw new Error(
        error.response?.data?.detail || 
        error.message || 
        'Failed to get user sessions'
      );
    }
  },

  // Delete a session
  async deleteSession(sessionId: string): Promise<void> {
    try {
      await api.delete(`/chat/sessions/${sessionId}`);
    } catch (error: any) {
      console.error('Error deleting session:', error);
      throw new Error(
        error.response?.data?.detail || 
        error.message || 
        'Failed to delete session'
      );
    }
  }
};