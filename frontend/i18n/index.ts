/**
 * Lightweight i18n system for Luna
 *
 * Usage:
 *   const { t, locale, setLocale } = useLocale();
 *   <Text>{t.settings.title}</Text>
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { zh, type Translations } from './zh';
import { en } from './en';

// ── Types ──────────────────────────────────────────────────────────────────
export type Locale = 'zh' | 'en';

interface LocaleContextValue {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: Translations;
}

// ── Locale map ─────────────────────────────────────────────────────────────
const translations: Record<Locale, Translations> = { zh, en };

const STORAGE_KEY = 'luna_locale';

// ── Context ────────────────────────────────────────────────────────────────
const LocaleContext = createContext<LocaleContextValue>({
  locale: 'zh',
  setLocale: () => {},
  t: zh,
});

// ── Provider ───────────────────────────────────────────────────────────────
export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, _setLocale] = useState<Locale>('zh');

  // Load persisted locale on mount
  useEffect(() => {
    (async () => {
      try {
        const saved = await AsyncStorage.getItem(STORAGE_KEY);
        if (saved === 'en' || saved === 'zh') {
          _setLocale(saved);
        }
      } catch {}
    })();
  }, []);

  const setLocale = useCallback((l: Locale) => {
    _setLocale(l);
    AsyncStorage.setItem(STORAGE_KEY, l).catch(() => {});
  }, []);

  const value: LocaleContextValue = {
    locale,
    setLocale,
    t: translations[locale],
  };

  return React.createElement(LocaleContext.Provider, { value }, children);
}

// ── Hook ───────────────────────────────────────────────────────────────────
export function useLocale() {
  return useContext(LocaleContext);
}

// ── Helper: interpolate {key} in strings ───────────────────────────────────
export function tt(template: string, vars: Record<string, string | number>): string {
  let result = template;
  for (const [key, val] of Object.entries(vars)) {
    result = result.replace(new RegExp(`\\{${key}\\}`, 'g'), String(val));
  }
  return result;
}

export type { Translations };
