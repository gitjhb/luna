/**
 * useMessages Hook
 * 
 * React Query based infinite scroll for chat messages.
 * Uses cursor-based pagination with inverted FlatList pattern.
 * 
 * SQLite-first strategy:
 * 1. First load from SQLite instantly (no loading state)
 * 2. Background sync from backend for any new messages
 * 3. Pagination fetches from backend (older messages)
 */

import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { chatService } from '../services/chatService';
import { Message } from '../store/chatStore';

interface MessagesPage {
  messages: Message[];
  nextCursor: string | null;  // oldest message ID for next page
  hasMore: boolean;
  fromCache?: boolean;  // indicate if this page was from SQLite
}

interface UseMessagesOptions {
  sessionId: string | null;
  characterId: string;
  enabled?: boolean;
}

/**
 * Fetch messages with true SQLite-first strategy
 * For inverted list: we load newest first, then fetch older on scroll
 */
const fetchMessages = async ({ 
  sessionId, 
  pageParam = null,
  limit = 20 
}: { 
  sessionId: string; 
  pageParam?: string | null;
  limit?: number;
}): Promise<MessagesPage> => {
  if (!sessionId) {
    return { messages: [], nextCursor: null, hasMore: false };
  }

  // First page (pageParam = null) - try SQLite first for instant display
  if (!pageParam) {
    try {
      console.log('[useMessages] Checking SQLite for session:', sessionId);
      const { MessageRepository } = await import('../services/database/repositories');
      // Get NEWEST messages first (desc order), then reverse to asc to match API format
      const cachedMessages = await MessageRepository.getBySessionId(sessionId, { 
        limit, 
        order: 'desc' 
      });
      
      console.log('[useMessages] SQLite returned:', cachedMessages?.length || 0, 'messages');
      
      if (cachedMessages && cachedMessages.length > 0) {
        console.log('[useMessages] ✅ Loaded', cachedMessages.length, 'messages from SQLite');
        
        // Convert SQLite format to Message format
        // extra_data may contain type, imageUrl, videoUrl, reaction
        // Reverse to get chronological order (asc) to match API format
        const messages: Message[] = cachedMessages.reverse().map(m => {
          const extra = m.extra_data || {};
          return {
            messageId: m.id,
            role: m.role as 'user' | 'assistant' | 'system',
            content: m.content,
            createdAt: m.created_at,
            isLocked: !m.is_unlocked,
            type: extra.type,
            imageUrl: extra.imageUrl,
            videoUrl: extra.videoUrl,
            reaction: extra.reaction,
          };
        });

        // Background sync: fetch latest from backend and merge
        // Don't await - let it happen in background
        syncFromBackend(sessionId, messages[0]?.createdAt);
        
        return {
          messages,
          nextCursor: cachedMessages.length >= limit ? cachedMessages[cachedMessages.length - 1].id : null,
          hasMore: cachedMessages.length >= limit,
          fromCache: true,
        };
      }
    } catch (e) {
      console.log('[useMessages] SQLite read failed, falling back to API:', e);
    }
  }

  // Fallback to backend (for initial load if SQLite empty, or for pagination)
  console.log('[useMessages] Fetching from backend, cursor:', pageParam);
  const { messages, hasMore, oldestId } = await chatService.getSessionHistory(
    sessionId,
    limit,
    pageParam || undefined  // before_message_id
  );

  // Save to SQLite for future use (async, don't block)
  if (messages.length > 0) {
    saveToSQLite(sessionId, messages);
  }

  return {
    messages,
    nextCursor: hasMore ? oldestId : null,
    hasMore,
  };
};

/**
 * Background sync: fetch any new messages from backend since last cached message
 */
const syncFromBackend = async (sessionId: string, latestCachedTime?: string) => {
  try {
    // Fetch latest messages from backend
    const { messages } = await chatService.getSessionHistory(sessionId, 20);
    
    if (messages.length > 0) {
      // Find messages newer than our cache
      const newMessages = latestCachedTime 
        ? messages.filter(m => new Date(m.createdAt) > new Date(latestCachedTime))
        : messages;
      
      if (newMessages.length > 0) {
        console.log('[useMessages] Background sync found', newMessages.length, 'new messages');
        saveToSQLite(sessionId, newMessages);
        // Note: React Query will pick up changes on next render
      }
    }
  } catch (e) {
    console.log('[useMessages] Background sync failed:', e);
  }
};

/**
 * Save messages to SQLite (fire and forget)
 * Store type, imageUrl, videoUrl, reaction in extra_data JSON
 */
const saveToSQLite = async (sessionId: string, messages: Message[]) => {
  try {
    const { MessageRepository } = await import('../services/database/repositories');
    for (const msg of messages) {
      // Store extra fields in extra_data JSON
      const extra_data: Record<string, any> = {};
      if (msg.type) extra_data.type = msg.type;
      if (msg.imageUrl) extra_data.imageUrl = msg.imageUrl;
      if (msg.videoUrl) extra_data.videoUrl = msg.videoUrl;
      if (msg.reaction) extra_data.reaction = msg.reaction;
      
      await MessageRepository.create({
        id: msg.messageId,
        session_id: sessionId,
        role: msg.role,
        content: msg.content,
        created_at: msg.createdAt,
        is_unlocked: !msg.isLocked,
        extra_data: Object.keys(extra_data).length > 0 ? extra_data : undefined,
      }).catch(() => {}); // Ignore duplicate errors
    }
    console.log('[useMessages] Saved to SQLite:', messages.length, 'messages');
  } catch (e) {
    // Ignore SQLite errors
  }
};

export function useMessages({ sessionId, characterId, enabled = true }: UseMessagesOptions) {
  const queryClient = useQueryClient();

  const query = useInfiniteQuery<MessagesPage, Error>({
    queryKey: ['messages', characterId, sessionId],
    queryFn: ({ pageParam }) => fetchMessages({ 
      sessionId: sessionId!, 
      pageParam: pageParam as string | null,
    }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage: MessagesPage) => lastPage.nextCursor,
    enabled: enabled && !!sessionId,
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 30,   // 30 minutes (formerly cacheTime)
    refetchOnWindowFocus: false,  // 防止键盘收起等触发 refetch 导致消息闪跳
    refetchOnReconnect: false,
  });

  // Flatten all pages into a single array for inverted FlatList
  // API returns messages in chronological order (oldest first) per page
  // For inverted list: index 0 = newest, last index = oldest
  // 
  // Page order: pages[0] = newest batch, pages[1] = older batch, ...
  // Within each page: [oldest_in_batch, ..., newest_in_batch]
  // 
  // We need: [newest_overall, ..., oldest_overall]
  // So: reverse each page, then flatten in order
  // 
  // DEDUP: optimistic adds + refetch can cause duplicates, so deduplicate by messageId
  const allMessages = (() => {
    const raw = query.data?.pages
      .flatMap((page: MessagesPage) => [...page.messages].reverse())
      ?? [];
    const seen = new Set<string>();
    return raw.filter((msg: Message) => {
      if (seen.has(msg.messageId)) return false;
      seen.add(msg.messageId);
      return true;
    });
  })();

  // Add a new message to the cache (optimistic update)
  const addMessage = (message: Message) => {
    // Also save to SQLite immediately
    if (sessionId) {
      saveToSQLite(sessionId, [message]);
    }

    queryClient.setQueryData(
      ['messages', characterId, sessionId],
      (oldData: any) => {
        if (!oldData) return oldData;
        
        // Dedup check: don't add if messageId already exists in any page
        const exists = oldData.pages.some((page: MessagesPage) =>
          page.messages.some((m: Message) => m.messageId === message.messageId)
        );
        if (exists) return oldData;
        
        // Add to the first page (newest messages)
        const newPages = [...oldData.pages];
        if (newPages.length > 0) {
          newPages[0] = {
            ...newPages[0],
            messages: [...newPages[0].messages, message],
          };
        }
        
        return {
          ...oldData,
          pages: newPages,
        };
      }
    );
  };

  // Update a message in cache (e.g., add reaction)
  const updateMessage = (messageId: string, updates: Partial<Message>) => {
    queryClient.setQueryData(
      ['messages', characterId, sessionId],
      (oldData: any) => {
        if (!oldData) return oldData;
        
        const newPages = oldData.pages.map((page: MessagesPage) => ({
          ...page,
          messages: page.messages.map((msg: Message) =>
            msg.messageId === messageId ? { ...msg, ...updates } : msg
          ),
        }));
        
        return {
          ...oldData,
          pages: newPages,
        };
      }
    );
  };

  // Invalidate and refetch
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['messages', characterId, sessionId] });
  };

  return {
    messages: allMessages,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    
    // Pagination
    fetchNextPage: query.fetchNextPage,
    hasNextPage: query.hasNextPage ?? false,
    isFetchingNextPage: query.isFetchingNextPage,
    
    // Mutations
    addMessage,
    updateMessage,
    refresh,
  };
}

export default useMessages;
