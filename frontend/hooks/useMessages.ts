/**
 * useMessages Hook
 * 
 * React Query based infinite scroll for chat messages.
 * Uses cursor-based pagination with inverted FlatList pattern.
 * 
 * SQLite-first strategy:
 * 1. First load from SQLite (offline-capable)
 * 2. Only fetch from backend if SQLite is empty or for pagination
 * 3. Sync backend data to SQLite for future use
 */

import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { chatService } from '../services/chatService';
import { Message } from '../store/chatStore';

interface MessagesPage {
  messages: Message[];
  nextCursor: string | null;  // oldest message ID for next page
  hasMore: boolean;
}

interface UseMessagesOptions {
  sessionId: string | null;
  characterId: string;
  enabled?: boolean;
}

/**
 * Fetch messages with SQLite-first strategy
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

  // First page (pageParam = null) - ALWAYS fetch from backend for freshness
  // SQLite is used as write-through cache, not read-first cache
  // This ensures we always see the latest messages after app reload
  if (!pageParam) {
    console.log('[useMessages] Fetching first page from backend (fresh load)');
  }

  // Fallback to backend (for initial load if SQLite empty, or for pagination)
  const { messages, hasMore, oldestId } = await chatService.getSessionHistory(
    sessionId,
    limit,
    pageParam || undefined  // before_message_id
  );

  // Save to SQLite for future use (async, don't block)
  if (messages.length > 0) {
    (async () => {
      try {
        const { MessageRepository } = await import('../services/database/repositories');
        for (const msg of messages) {
          await MessageRepository.create({
            id: msg.messageId,
            session_id: sessionId,
            role: msg.role,
            content: msg.content,
            created_at: msg.createdAt,
            is_unlocked: msg.isLocked ? 0 : 1,
          }).catch(() => {}); // Ignore duplicate errors
        }
        console.log('[useMessages] Synced to SQLite:', messages.length, 'messages');
      } catch (e) {
        // Ignore SQLite errors
      }
    })();
  }

  return {
    messages,
    nextCursor: hasMore ? oldestId : null,
    hasMore,
  };
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
