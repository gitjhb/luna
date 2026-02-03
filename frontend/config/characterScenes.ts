/**
 * Character Scene Configuration
 * 
 * 角色场景照片配置 - 约会解锁系统
 * 
 * 照片分级：
 * - base: 场景立绘（可作为约会背景）
 * - normal: 普通约会解锁
 * - perfect: 完美约会解锁（更诱惑）
 */

export interface ScenePhoto {
  id: string;
  scene: string;        // 场景ID
  sceneName: string;    // 场景中文名
  type: 'base' | 'normal' | 'perfect';
  requiredLevel: number; // 解锁需要的等级
  isUnlocked?: boolean;
  unlockedAt?: string;
}

export interface CharacterSceneConfig {
  characterId: string;
  characterName: string;
  scenes: {
    [sceneId: string]: {
      name: string;
      requiredLevel: number;
      description?: string;
      // 固定剧情placeholder
      fixedStory?: {
        intro: string;
        options: string[];
      };
    };
  };
}

// Sakura 场景配置
export const SAKURA_SCENES: CharacterSceneConfig = {
  characterId: 'sakura',
  characterName: '芽衣',
  scenes: {
    bedroom: {
      name: '卧室',
      requiredLevel: 1,  // 立绘，始终可用
      description: '芽衣的私人空间',
    },
    beach: {
      name: '海滩',
      requiredLevel: 20,
      description: '阳光沙滩，青春的气息',
      fixedStory: {
        intro: '夏日的海边，芽衣穿着泳装向你跑来...',
        options: ['一起去游泳', '帮她涂防晒霜', '在沙滩上休息'],
      },
    },
    ocean: {
      name: '海边露台',
      requiredLevel: 20,
      description: '浪漫的海边夜晚',
      fixedStory: {
        intro: '夜幕降临，海风轻拂，芽衣靠在栏杆上望着星空...',
        options: ['从背后拥抱她', '递给她一杯饮料', '一起看星星'],
      },
    },
    school: {
      name: '教室',
      requiredLevel: 20,
      description: '放学后的秘密约会',
      fixedStory: {
        intro: '放学后的教室，只剩下你们两个人...',
        options: ['帮她整理课本', '邀请她去天台', '一起做作业'],
      },
    },
  },
};

// 所有角色的场景配置
export const CHARACTER_SCENES: Record<string, CharacterSceneConfig> = {
  sakura: SAKURA_SCENES,
  // 后续可添加更多角色
};

/**
 * 获取场景照片路径
 */
export function getScenePhotoPath(
  characterId: string, 
  scene: string, 
  type: 'base' | 'normal' | 'perfect'
): string {
  const suffix = type === 'base' ? '' : `-${type}`;
  return `characters/${characterId}/scenes/${scene}${suffix}.jpeg`;
}

/**
 * 检查场景是否解锁
 */
export function isSceneUnlocked(
  characterId: string,
  scene: string,
  userLevel: number
): boolean {
  const config = CHARACTER_SCENES[characterId];
  if (!config) return false;
  
  const sceneConfig = config.scenes[scene];
  if (!sceneConfig) return false;
  
  return userLevel >= sceneConfig.requiredLevel;
}

/**
 * 获取约会解锁的照片类型
 */
export function getUnlockPhotoType(
  endingType: 'perfect' | 'good' | 'normal' | 'bad'
): 'perfect' | 'normal' | null {
  switch (endingType) {
    case 'perfect':
      return 'perfect';
    case 'good':
    case 'normal':
      return 'normal';
    case 'bad':
      return null;  // 糟糕约会不解锁照片
  }
}
