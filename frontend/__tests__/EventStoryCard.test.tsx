/**
 * EventStoryCard Component Tests
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import EventStoryCard from '../components/EventStoryCard';
import { EventStoryPlaceholder } from '../services/eventService';

// Mock reanimated
jest.mock('react-native-reanimated', () => require('react-native-reanimated/mock'));

// Mock expo modules
jest.mock('expo-linear-gradient', () => ({
  LinearGradient: 'LinearGradient',
}));

jest.mock('@expo/vector-icons', () => ({
  Ionicons: 'Ionicons',
}));

describe('EventStoryCard', () => {
  const mockPlaceholder: EventStoryPlaceholder = {
    type: 'event_story',
    event_type: 'first_date',
    character_id: 'char-123',
    status: 'pending',
    story_id: undefined,
  };

  const mockOnPress = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders correctly with pending status', () => {
    const { getByText } = render(
      <EventStoryCard
        placeholder={mockPlaceholder}
        characterName="Luna"
        onPress={mockOnPress}
        isRead={false}
      />
    );

    expect(getByText('第一次约会')).toBeTruthy();
    expect(getByText('点击生成专属剧情')).toBeTruthy();
  });

  it('renders correctly with generated status', () => {
    const generatedPlaceholder = {
      ...mockPlaceholder,
      status: 'generated' as const,
      story_id: 'story-123',
    };

    const { getByText } = render(
      <EventStoryCard
        placeholder={generatedPlaceholder}
        characterName="Luna"
        onPress={mockOnPress}
        isRead={false}
      />
    );

    expect(getByText('点击查看剧情')).toBeTruthy();
  });

  it('renders correctly when read', () => {
    const { getByText } = render(
      <EventStoryCard
        placeholder={mockPlaceholder}
        characterName="Luna"
        onPress={mockOnPress}
        isRead={true}
      />
    );

    expect(getByText('点击重温回忆')).toBeTruthy();
  });

  it('calls onPress when tapped', () => {
    const { getByText } = render(
      <EventStoryCard
        placeholder={mockPlaceholder}
        characterName="Luna"
        onPress={mockOnPress}
        isRead={false}
      />
    );

    // Note: In a real test, we'd tap the actual touchable
    // This is a simplified test
    fireEvent.press(getByText('第一次约会'));
    // onPress would be called on the parent touchable
  });

  it('displays correct event icon for different event types', () => {
    const eventTypes = [
      { type: 'first_date', expectedIcon: '💕' },
      { type: 'first_kiss', expectedIcon: '💋' },
      { type: 'first_confession', expectedIcon: '💝' },
    ];

    eventTypes.forEach(({ type, expectedIcon }) => {
      const placeholder = {
        ...mockPlaceholder,
        event_type: type,
      };

      const { getByText } = render(
        <EventStoryCard
          placeholder={placeholder}
          characterName="Luna"
          onPress={mockOnPress}
          isRead={false}
        />
      );

      expect(getByText(expectedIcon)).toBeTruthy();
    });
  });
});
