/**
 * Interactions Service - 拍照、换装等消费功能
 */

import { API_BASE_URL } from './api';

export interface InteractionConfig {
  photo: {
    name: string;
    cost: number;
    unlock_level: number;
    event_name: string;
  };
  dressup: {
    name: string;
    cost: number;
    unlock_level: number;
    event_name: string;
  };
}

export interface DressupOption {
  id: string;
  name: string;
  icon: string;
}

export interface DressupOptions {
  tops: DressupOption[];
  bottoms: DressupOption[];
  cost: number;
  unlock_level: number;
}

export interface PhotoResponse {
  success: boolean;
  image_url: string;
  cost: number;
  is_first: boolean;
  message: string;
  album_id: string;
}

export interface AlbumEntry {
  id: string;
  type: 'photo' | 'dressup';
  image_url: string;
  created_at: string;
  context?: string;
  outfit?: { top: string; bottom: string };
}

export interface AlbumResponse {
  character_id: string;
  photos: AlbumEntry[];
  total: number;
}

class InteractionsService {
  /**
   * 获取互动功能配置
   */
  async getConfig(): Promise<InteractionConfig> {
    const res = await fetch(`${API_BASE_URL}/interactions/config`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  /**
   * 获取换装选项
   */
  async getDressupOptions(): Promise<DressupOptions> {
    const res = await fetch(`${API_BASE_URL}/interactions/dressup/options`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  /**
   * 拍照
   */
  async takePhoto(characterId: string, context?: string): Promise<PhotoResponse> {
    const res = await fetch(`${API_BASE_URL}/interactions/photo`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ character_id: characterId, context }),
    });
    
    if (res.status === 402) {
      const err = await res.json();
      throw new Error(err.detail || '月石不足');
    }
    if (res.status === 403) {
      const err = await res.json();
      throw new Error(err.detail || '等级不足');
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    
    return res.json();
  }

  /**
   * 换装
   */
  async dressup(characterId: string, topId: string, bottomId: string): Promise<PhotoResponse> {
    const res = await fetch(`${API_BASE_URL}/interactions/dressup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ character_id: characterId, top_id: topId, bottom_id: bottomId }),
    });
    
    if (res.status === 402) {
      const err = await res.json();
      throw new Error(err.detail || '月石不足');
    }
    if (res.status === 403) {
      const err = await res.json();
      throw new Error(err.detail || '等级不足');
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    
    return res.json();
  }

  /**
   * 获取相册
   */
  async getAlbum(characterId: string): Promise<AlbumResponse> {
    const res = await fetch(`${API_BASE_URL}/interactions/album/${characterId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }
}

export const interactionsService = new InteractionsService();
