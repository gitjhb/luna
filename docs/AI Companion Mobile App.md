# AI Companion Mobile App

A premium, white-label ready React Native mobile application for an AI Emotional Companion platform. Built with Expo, TypeScript, and a sophisticated "Dark Luxury" design system.

## 🎨 Design Philosophy

**Target Audience:** Men 40+  
**Visual Style:** Dark Luxury - Seductive, not flashy  
**UX Principles:** Intuitive navigation, readable fonts, premium feel

## 🏗️ Architecture

### Technology Stack
- **Framework:** Expo (React Native) with Expo Router
- **Language:** TypeScript
- **Styling:** NativeWind (Tailwind CSS for React Native)
- **State Management:** Zustand with AsyncStorage persistence
- **Networking:** Axios + TanStack Query
- **Animations:** React Native Reanimated
- **Authentication:** Firebase Admin SDK (Apple/Google Sign-In)

### Key Features
- ✅ **White-Label Ready** - Single config file to reskin entire app
- ✅ **Dark Luxury Theme** - Gold accents, gradient buttons, premium feel
- ✅ **Spicy Mode** - Premium feature with subscription gate
- ✅ **Credit System** - Real-time balance tracking with low balance warnings
- ✅ **Tinder-Style Cards** - Swipeable character selection
- ✅ **Blur & Unlock** - NSFW content protection with tap-to-unlock
- ✅ **Optimized Performance** - FlatList for message rendering
- ✅ **Type-Safe** - Full TypeScript coverage

## 📁 Project Structure

```
ai-companion-mobile/
├── app/                          # Expo Router file-based routing
│   ├── (tabs)/                   # Tab navigation group
│   │   ├── index.tsx             # Companions (Home) screen
│   │   ├── chats.tsx             # Chat history screen
│   │   └── profile.tsx           # Profile & settings screen
│   ├── auth/
│   │   └── login.tsx             # Login screen
│   ├── chat/
│   │   └── [characterId].tsx    # Dynamic chat screen
│   └── _layout.tsx               # Root layout
├── components/
│   ├── atoms/                    # Basic UI elements
│   │   └── TypingIndicator.tsx
│   ├── molecules/                # Composite components
│   │   ├── CharacterCard.tsx
│   │   ├── ChatBubble.tsx
│   │   └── CreditHeader.tsx
│   └── organisms/                # Complex components
│       └── PaywallModal.tsx
├── services/                     # API service layer
│   ├── api.ts                    # Axios client & interceptors
│   ├── authService.ts
│   ├── characterService.ts
│   ├── chatService.ts
│   └── walletService.ts
├── store/                        # Zustand state management
│   ├── userStore.ts              # User auth & credits
│   └── chatStore.ts              # Chat sessions & messages
├── theme/
│   └── config.ts                 # White-label theme configuration
├── types/
│   └── index.ts                  # TypeScript type definitions
├── assets/                       # Images, fonts, etc.
├── app.json                      # Expo configuration
├── package.json
└── tsconfig.json
```

## 🎨 White-Label Theming System

The entire app can be reskinned by editing a **single file**: `theme/config.ts`

### Theme Configuration

```typescript
export const defaultTheme: ThemeConfig = {
  appName: "LuxeCompanion",
  appTagline: "Your Premium AI Experience",
  
  colors: {
    background: {
      primary: "#0A0A0F",      // Deep black
      secondary: "#1A1A24",    // Elevated surfaces
      tertiary: "#252530",     // Input fields
      gradient: ["#0A0A0F", "#1A1520", "#0A0A0F"],
    },
    
    primary: {
      main: "#FFD700",         // Luxe gold
      gradient: ["#FFD700", "#FFA500"],
    },
    
    spicy: {
      main: "#FF69B4",         // Hot pink
      gradient: ["#FF1493", "#FF69B4", "#FF8DC7"],
    },
    
    text: {
      primary: "#FFFFFF",
      secondary: "#A0A0B0",
      accent: "#FFD700",
    },
  },
  
  typography: {
    fontFamily: {
      regular: "Inter-Regular",
      bold: "Inter-Bold",
    },
    fontSize: {
      base: 16,  // Optimized for 40+ readability
      lg: 18,
      xl: 20,
    },
  },
  
  // ... more configuration
};
```

### How to Reskin

1. **Change Colors:** Edit `colors` object to match your brand
2. **Update Typography:** Replace font families and sizes
3. **Modify Assets:** Replace logo and images in `assets/`
4. **Adjust Spacing:** Modify `spacing` and `borderRadius` values

**Result:** The entire app instantly reflects your brand identity.

## 🚀 Getting Started

### Prerequisites
- Node.js 18+
- npm or yarn
- Expo CLI (`npm install -g expo-cli`)
- iOS Simulator (Mac) or Android Emulator

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd ai-companion-mobile

# Install dependencies
npm install

# Start development server
npm start
```

### Running the App

```bash
# iOS
npm run ios

# Android
npm run android

# Web (for testing)
npm run web
```

## 🔑 Environment Configuration

Create a `.env` file in the root directory:

```bash
# API Configuration
EXPO_PUBLIC_API_URL=http://localhost:8000/api/v1

# Firebase (for production)
EXPO_PUBLIC_FIREBASE_API_KEY=your-api-key
EXPO_PUBLIC_FIREBASE_PROJECT_ID=your-project-id

# Feature Flags
EXPO_PUBLIC_MOCK_API=true  # Use mock API for development
```

## 📱 Key Screens

### 1. Login Screen (`app/auth/login.tsx`)
- **Features:**
  - Continue with Apple
  - Continue with Google
  - Compelling value proposition
  - Terms and privacy links
- **UX:** High-conversion design with gradient backgrounds

### 2. Companions Screen (`app/(tabs)/index.tsx`)
- **Features:**
  - Character cards with Tinder-style swipe
  - Search and filter functionality
  - Premium badge for locked characters
  - Optimized scrolling performance
- **UX:** Intuitive browsing with clear visual hierarchy

### 3. Chat Screen (`app/chat/[characterId].tsx`)
- **Features:**
  - Real-time messaging
  - Spicy mode toggle (subscription-gated)
  - Credit header with balance
  - Typing indicator
  - Blur & unlock for NSFW content
  - Message history with FlatList
- **UX:** Smooth animations, clear feedback, premium feel

### 4. Paywall Modal (`components/organisms/PaywallModal.tsx`)
- **Features:**
  - Subscription plans comparison
  - Feature highlights
  - Bonus credits display
  - Restore purchases option
- **UX:** High-conversion design with urgency and value

## 🎯 Core Components

### CharacterCard
Tinder-style swipeable card with:
- Gesture handling (swipe left/right)
- Premium badge for locked characters
- Gradient overlay for readability
- "Chat Now" CTA button

### ChatBubble
Flexible message bubble with:
- Text and image support
- Locked content with blur overlay
- Tap-to-unlock functionality
- User vs Assistant styling
- Spicy mode color adaptation

### CreditHeader
Sticky header displaying:
- Real-time credit balance
- Animated counter on changes
- Low balance warning
- Quick buy button

### PaywallModal
Subscription upsell modal with:
- Plan comparison
- Feature lists
- Pricing display
- High-conversion design

## 🔐 State Management

### User Store (`store/userStore.ts`)
Manages:
- Authentication state
- User profile
- Credit balance
- Subscription tier
- Persisted to AsyncStorage

### Chat Store (`store/chatStore.ts`)
Manages:
- Active chat session
- Messages by session
- Spicy mode state
- Typing indicator
- In-memory (not persisted)

## 🌐 API Integration

### Mock API (Development)
Set `EXPO_PUBLIC_MOCK_API=true` to use mock responses.

### Real API (Production)
Set `EXPO_PUBLIC_API_URL` to your backend URL.

### Service Layer
- **authService:** Login, profile, token refresh
- **characterService:** Get characters, character details
- **chatService:** Sessions, messages, unlock content
- **walletService:** Balance, transactions, purchases

## 🎨 Design System

### Colors
- **Background:** Deep blacks with subtle gradients
- **Primary:** Gold (#FFD700) for CTAs and accents
- **Spicy:** Hot pink (#FF69B4) for premium features
- **Text:** High contrast white with muted grays

### Typography
- **Font:** Inter (regular, medium, semibold, bold)
- **Base Size:** 16px (optimized for 40+ readability)
- **Line Height:** 1.5 for body text

### Spacing
- **Base Grid:** 8px
- **Consistent Padding:** 16px, 24px, 32px
- **Generous Touch Targets:** 44px minimum

### Animations
- **Fast:** 150ms (micro-interactions)
- **Normal:** 300ms (transitions)
- **Slow:** 500ms (complex animations)

## 🔒 Content Moderation

### NSFW Content Handling
1. **Default State:** All potentially explicit images are blurred
2. **Unlock Mechanism:** User taps "Unlock" button (costs 5 credits)
3. **Warning:** "This content may be explicit" message displayed
4. **Safety:** Prevents accidental exposure in public settings

### Content Policy
- **Allowed:** NSFW/adult content, flirting, suggestive themes
- **Blocked:** Illegal content (handled by backend)

## 📊 Performance Optimization

### Message List
- **FlatList** for efficient rendering
- **Key extraction** for proper reconciliation
- **Scroll to bottom** on new messages
- **Lazy loading** for history

### Image Handling
- **Loading indicators** for network images
- **Blur overlay** for locked content
- **Cached images** for repeated views

### State Updates
- **Zustand selectors** for optimized re-renders
- **Memoized components** where appropriate
- **Debounced search** for character filtering

## 🧪 Testing

```bash
# Type checking
npm run type-check

# Linting
npm run lint
```

## 📦 Building for Production

### iOS

```bash
# Install EAS CLI
npm install -g eas-cli

# Configure EAS
eas build:configure

# Build for iOS
eas build --platform ios
```

### Android

```bash
# Build for Android
eas build --platform android
```

## 🚀 Deployment

### Expo Application Services (EAS)

1. **Create Expo account:** https://expo.dev
2. **Configure EAS:** `eas build:configure`
3. **Submit to App Store:** `eas submit --platform ios`
4. **Submit to Play Store:** `eas submit --platform android`

### Over-the-Air Updates

```bash
# Publish update
eas update --branch production
```

## 🎯 Subscription Tiers

| Tier    | Price/Month | Daily Credits | Features                        |
|---------|-------------|---------------|---------------------------------|
| Free    | $0          | 10            | Basic chat                      |
| Premium | $9.99       | 100           | RAG memory, Spicy Mode, 30% off |
| VIP     | $29.99      | 500           | All features, 50% off, priority |

## 🔮 Future Enhancements

- [ ] Streaming chat responses (SSE)
- [ ] Voice message support
- [ ] Image generation integration
- [ ] Push notifications
- [ ] Offline mode
- [ ] Multi-language support
- [ ] Dark/Light theme toggle
- [ ] Advanced analytics

## 📝 License

[Your License Here]

## 🙏 Acknowledgments

- Expo team for the amazing framework
- React Native community
- Design inspiration from premium dating apps

---

**Built with ❤️ for premium AI companionship experiences**
