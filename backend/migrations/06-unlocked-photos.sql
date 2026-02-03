-- 照片解锁记录表
-- 记录用户解锁的角色照片

CREATE TABLE IF NOT EXISTS unlocked_photos (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    character_id TEXT NOT NULL,
    scene TEXT NOT NULL,           -- 场景: bedroom, beach, ocean, school
    photo_type TEXT NOT NULL,      -- 照片类型: normal, perfect
    source TEXT DEFAULT 'date',    -- 解锁来源: date, purchase, gift
    unlocked_at TEXT NOT NULL,
    
    -- 索引
    UNIQUE(user_id, character_id, scene, photo_type)
);

CREATE INDEX IF NOT EXISTS idx_unlocked_photos_user_char 
ON unlocked_photos(user_id, character_id);
