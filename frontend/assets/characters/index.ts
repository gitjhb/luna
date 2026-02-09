/**
 * Character Images
 * 
 * Local character avatar images - no more remote URLs!
 */

// Character avatar images by character ID
export const characterAvatars: Record<string, any> = {
  // 小美 - 温柔邻家女孩
  'c1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c': require('./小美.jpg'),
  
  // Luna - 月亮/猫系角色，安静理智
  'd2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d': require('./luna/avatar.jpg'),
  
  // Sakura - 元气少女
  'e3c4d5e6-f7a8-4b9c-0d1e-2f3a4b5c6d7e': require('./Sakura.jpeg'),
  
  // Yuki - 高冷大小姐
  'f4d5e6f7-a8b9-4c0d-1e2f-3a4b5c6d7e8f': require('./Yuki.jpg'),
  
  // 芽衣 (Mei) - 赛博高中生
  'a5b6c7d8-e9f0-4a1b-2c3d-4e5f6a7b8c9d': require('./mei.jpg'),
  
  // Vera - 性感成熟的酒吧老板娘 [Spicy]
  'b6c7d8e9-f0a1-4b2c-3d4e-5f6a7b8c9d0e': require('./vera.jpg'),
  
  // 煤球 - 毒舌黑猫搭子 [Buddy]
  'a7b8c9d0-e1f2-4a3b-5c6d-7e8f9a0b1c2d': require('./meiqiu.jpg'),
};

// Character background images
export const characterBackgrounds: Record<string, any> = {
  // 小美 - 用头像作为背景
  'c1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c': require('./小美.jpg'),
  
  // Luna - 使用全身照作为背景
  'd2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d': require('./luna.jpg'),
  
  // Sakura
  'e3c4d5e6-f7a8-4b9c-0d1e-2f3a4b5c6d7e': require('./Sakura.jpeg'),
  
  // Yuki
  'f4d5e6f7-a8b9-4c0d-1e2f-3a4b5c6d7e8f': require('./Yuki.jpg'),
  
  // 芽衣
  'a5b6c7d8-e9f0-4a1b-2c3d-4e5f6a7b8c9d': require('./mei.jpg'),
  
  // Vera
  'b6c7d8e9-f0a1-4b2c-3d4e-5f6a7b8c9d0e': require('./vera.jpg'),
  
  // 煤球
  'a7b8c9d0-e1f2-4a3b-5c6d-7e8f9a0b1c2d': require('./meiqiu.jpg'),
};

/**
 * Get character avatar source
 * Returns local require() for known characters, or fallback
 */
export const getCharacterAvatar = (characterId: string, remoteUrl?: string | null) => {
  if (characterAvatars[characterId]) {
    return characterAvatars[characterId];
  }
  // Fallback: use remote URL or default placeholder
  return { uri: remoteUrl || 'https://i.pravatar.cc/300' };
};

/**
 * Get character background source
 */
export const getCharacterBackground = (characterId: string, remoteUrl?: string | null) => {
  if (characterBackgrounds[characterId]) {
    return characterBackgrounds[characterId];
  }
  if (remoteUrl) {
    return { uri: remoteUrl };
  }
  return null;
};
