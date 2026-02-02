/**
 * Event Service Tests
 */

import { eventService, EventStoryPlaceholder, STORY_EVENT_TYPES } from '../services/eventService';

describe('eventService', () => {
  describe('parseEventStoryPlaceholder', () => {
    it('parses valid event story JSON', () => {
      const content = JSON.stringify({
        type: 'event_story',
        event_type: 'first_date',
        character_id: 'char-123',
        status: 'pending',
        story_id: null,
      });

      const result = eventService.parseEventStoryPlaceholder(content);

      expect(result).not.toBeNull();
      expect(result?.type).toBe('event_story');
      expect(result?.event_type).toBe('first_date');
      expect(result?.character_id).toBe('char-123');
      expect(result?.status).toBe('pending');
    });

    it('returns null for non-JSON content', () => {
      const result = eventService.parseEventStoryPlaceholder('Hello, this is a normal message');
      expect(result).toBeNull();
    });

    it('returns null for JSON without event_story type', () => {
      const content = JSON.stringify({
        type: 'gift',
        gift_type: 'rose',
      });

      const result = eventService.parseEventStoryPlaceholder(content);
      expect(result).toBeNull();
    });

    it('returns null for invalid JSON', () => {
      const result = eventService.parseEventStoryPlaceholder('{invalid json}');
      expect(result).toBeNull();
    });
  });

  describe('isEventStoryMessage', () => {
    it('returns true for event story messages', () => {
      const content = JSON.stringify({
        type: 'event_story',
        event_type: 'first_kiss',
        character_id: 'char-123',
        status: 'generated',
        story_id: 'story-456',
      });

      expect(eventService.isEventStoryMessage(content)).toBe(true);
    });

    it('returns false for regular messages', () => {
      expect(eventService.isEventStoryMessage('你好！今天心情怎么样？')).toBe(false);
    });
  });

  describe('isStoryEvent', () => {
    it('returns true for supported story events', () => {
      STORY_EVENT_TYPES.forEach((eventType) => {
        expect(eventService.isStoryEvent(eventType)).toBe(true);
      });
    });

    it('returns false for non-story events', () => {
      expect(eventService.isStoryEvent('first_chat')).toBe(false);
      expect(eventService.isStoryEvent('first_compliment')).toBe(false);
      expect(eventService.isStoryEvent('unknown_event')).toBe(false);
    });
  });

  describe('getEventInfo', () => {
    it('returns correct info for known events', () => {
      const dateInfo = eventService.getEventInfo('first_date');
      expect(dateInfo.name_cn).toBe('第一次约会');
      expect(dateInfo.icon).toBe('💕');

      const kissInfo = eventService.getEventInfo('first_kiss');
      expect(kissInfo.name_cn).toBe('初吻');
      expect(kissInfo.icon).toBe('💋');
    });

    it('returns default info for unknown events', () => {
      const unknownInfo = eventService.getEventInfo('unknown_event');
      expect(unknownInfo.name_cn).toBe('unknown_event');
      expect(unknownInfo.icon).toBe('📖');
    });
  });
});
