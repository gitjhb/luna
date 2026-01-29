# Luna AI Companion - Mobile Frontend

Premium AI companion mobile app built with React Native (Expo Router).

## 🚀 Features

### ✅ Implemented

- **Authentication**
  - Login screen with Apple/Google Sign-In (mock mode)
  - Token-based authentication
  - Auto-logout on 401

- **Characters (Companions)**
  - Character listing with filter chips (All/Free/Premium/Spicy)
  - Search functionality
  - Character cards with tier badges
  - Locked state for premium characters

- **Chat**
  - Real-time messaging interface
  - Typing indicator
  - Spicy mode toggle (premium feature)
  - Credit header with balance display
  - Message locking/unlocking
  - Session management

- **Chat History**
  - Session list with character info
  - Last message preview
  - Message count and credits spent
  - Delete sessions (long press)
  - Pull to refresh

- **Profile**
  - User info display
  - Credit balance breakdown
  - Credit packages for purchase
  - Subscription plans display
  - Settings section
  - Logout

- **Navigation**
  - Bottom tab navigation with gradient icons
  - Low balance indicator on profile tab
  - Stack navigation for chat screens

### 🎨 Design System

- **Theme**: Dark mode with golden accent (#FFD700)
- **Typography**: SF Pro Display (iOS) / Roboto (Android)
- **Components**: Atomic design (atoms/molecules/organisms)
- **Animations**: React Native Reanimated

## 📁 Project Structure

```
frontend/
├── app/                    # Expo Router screens
│   ├── (tabs)/            # Tab screens
│   │   ├── index.tsx      # Companions (Home)
│   │   ├── chats.tsx      # Chat history
│   │   ├── profile.tsx    # User profile
│   │   └── _layout.tsx    # Tab navigation
│   ├── auth/
│   │   └── login.tsx      # Login screen
│   ├── chat/
│   │   └── [characterId].tsx  # Chat screen
│   └── _layout.tsx        # Root layout
├── components/
│   ├── atoms/             # Basic components
│   ├── molecules/         # Composite components
│   └── organisms/         # Complex components
├── services/              # API services
│   ├── api.ts             # Axios client + mock API
│   ├── authService.ts
│   ├── chatService.ts
│   ├── characterService.ts
│   ├── walletService.ts
│   └── intimacyService.ts
├── store/                 # Zustand state management
│   ├── userStore.ts       # User + wallet state
│   └── chatStore.ts       # Chat + sessions state
├── theme/
│   └── config.ts          # Design tokens
├── types/
│   └── index.ts           # TypeScript types
└── package.json
```

## 🛠️ Setup

```bash
# Install dependencies
npm install

# Start development server
npx expo start

# Run on iOS simulator
npm run ios

# Run on Android emulator
npm run android
```

## 🔧 Configuration

### Environment Variables

Create `.env` file:

```env
EXPO_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### Mock Mode

By default, the app runs in mock mode for development. To connect to real backend:

1. Set `EXPO_PUBLIC_API_URL` to your backend URL
2. In `services/api.ts`, set `mockApi.enabled = false`

## 📱 Screens

### Login
- Social login buttons (Apple/Google)
- Feature highlights
- Terms & privacy links

### Companions (Home)
- Horizontal filter chips
- Search bar
- Character grid with cards
- Tier badges (Free/Premium/VIP)
- Spicy indicator (🔥)

### Chats
- Session list with avatars
- Last message preview
- Timestamp (relative)
- Stats (messages, credits)
- Long-press to delete

### Chat
- Credit header with buy CTA
- Character name + typing indicator
- Spicy mode toggle (🔥)
- Message list (user/assistant)
- Input field + send button

### Profile
- User card with avatar
- Subscription badge
- Credit balance breakdown
- Credit packages grid
- Subscription plans (if not subscribed)
- Settings list
- Logout button

## 🔌 Backend Integration

API endpoints expected:

```
POST /api/v1/auth/login
GET  /api/v1/auth/me
GET  /api/v1/characters
GET  /api/v1/characters/:id
GET  /api/v1/chat/sessions
POST /api/v1/chat/sessions
GET  /api/v1/chat/sessions/:id/messages
POST /api/v1/chat/completions
GET  /api/v1/wallet/balance
POST /api/v1/market/buy_credits
POST /api/v1/market/subscribe
GET  /api/v1/market/products
```

## 📦 Dependencies

- **expo** ~50.0.0 - React Native framework
- **expo-router** ~3.4.0 - File-based routing
- **zustand** ^4.5.0 - State management
- **axios** ^1.6.5 - HTTP client
- **react-native-reanimated** ~3.6.1 - Animations
- **expo-linear-gradient** ~12.7.0 - Gradients
- **expo-blur** ~12.9.0 - Blur effects
- **date-fns** ^3.2.0 - Date formatting
- **@tanstack/react-query** ^5.17.19 - Data fetching

## 🎯 Next Steps

1. **Real Authentication**: Implement actual Apple/Google OAuth
2. **Backend Connection**: Point to real API server
3. **Push Notifications**: Implement expo-notifications
4. **In-App Purchases**: Integrate RevenueCat
5. **Voice Messages**: Add audio recording/playback
6. **Image Generation**: Display AI-generated images
7. **Offline Support**: Add persistence layer
8. **Analytics**: Integrate tracking

## 📄 License

MIT
