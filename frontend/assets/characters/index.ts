/**
 * Character Assets
 * 
 * 统一管理角色资源：avatar, chat-background, videos/intro
 * 
 * 角色列表：sakura, luna, vera, mei, meiqiu
 */

// Character IDs
export const CHARACTER_IDS = {
  SAKURA: 'e3c4d5e6-f7a8-4b9c-0d1e-2f3a4b5c6d7e',
  LUNA: 'd2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d',
  VERA: 'b6c7d8e9-f0a1-4b2c-3d4e-5f6a7b8c9d0e',
  MEI: 'a5b6c7d8-e9f0-4a1b-2c3d-4e5f6a7b8c9d',
  MEIQIU: 'a7b8c9d0-e1f2-4a3b-5c6d-7e8f9a0b1c2d',
};

// Character avatar images
export const characterAvatars: Record<string, any> = {
  [CHARACTER_IDS.SAKURA]: require('./sakura/avatar.jpeg'),
  [CHARACTER_IDS.LUNA]: require('./luna/avatar.jpg'),
  [CHARACTER_IDS.VERA]: require('./vera/avatar.png'),
  [CHARACTER_IDS.MEI]: require('./mei/avatar.jpg'),
  [CHARACTER_IDS.MEIQIU]: require('./meiqiu/avatar.png'),
};

// Character background images
export const characterBackgrounds: Record<string, any> = {
  [CHARACTER_IDS.SAKURA]: require('./sakura/chat-background.png'),
  [CHARACTER_IDS.LUNA]: require('./luna/chat_background.png'),
  [CHARACTER_IDS.VERA]: require('./vera/chat_background.png'),
  [CHARACTER_IDS.MEI]: require('./mei/chat-background.png'),
  [CHARACTER_IDS.MEIQIU]: require('./meiqiu/chat-background.jpg'),
};

// Character intro videos (全屏播放)
export const characterIntroVideos: Record<string, any> = {
  [CHARACTER_IDS.SAKURA]: require('./sakura/videos/intro.mp4'),
  [CHARACTER_IDS.LUNA]: require('./luna/intro.mp4'),
  [CHARACTER_IDS.VERA]: require('./vera/videos/intro.mp4'),
  [CHARACTER_IDS.MEI]: require('./mei/video/intro.mp4'),
};

// Default avatar for unknown characters
const defaultAvatar = require('../images/default-avatar.png');

/**
 * Get character avatar source
 */
export const getCharacterAvatar = (characterId: string, remoteUrl?: string | null) => {
  if (characterAvatars[characterId]) {
    return characterAvatars[characterId];
  }
  if (remoteUrl) {
    return { uri: remoteUrl };
  }
  return defaultAvatar;
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

/**
 * Get character intro video source (if available)
 */
export const getCharacterIntroVideo = (characterId: string) => {
  return characterIntroVideos[characterId] || null;
};
