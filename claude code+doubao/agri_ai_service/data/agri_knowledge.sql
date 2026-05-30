-- ============================================================
-- 农技知识库 + 农事提醒 数据库表结构
-- 在 agri_db 数据库中运行本脚本
-- ============================================================

-- 1. 知识分类（作物类别）
CREATE TABLE IF NOT EXISTS agri_knowledge_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '分类名称，如水稻、小麦',
    icon VARCHAR(500) DEFAULT '' COMMENT '图标URL',
    sort_order INT DEFAULT 0 COMMENT '排序',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识分类';

-- 2. 知识条目（病害/虫害详情）
CREATE TABLE IF NOT EXISTS agri_knowledge (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT NOT NULL COMMENT '分类ID',
    title VARCHAR(255) NOT NULL COMMENT '病害名称',
    cover_image VARCHAR(500) DEFAULT '' COMMENT '封面图',
    summary TEXT COMMENT '简介',
    symptoms TEXT COMMENT '症状特征',
    cause TEXT COMMENT '发病原因',
    prevention TEXT COMMENT '预防措施',
    treatment TEXT COMMENT '防治方法',
    drugs JSON COMMENT '推荐用药 [{name,usage,image_url,purchase_url}]',
    tags VARCHAR(500) DEFAULT '' COMMENT '搜索标签，逗号分隔',
    view_count INT DEFAULT 0 COMMENT '浏览量',
    is_pest TINYINT(1) DEFAULT 0 COMMENT '1虫害 0病害',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES agri_knowledge_categories(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识条目';

-- 3. 用户收藏
CREATE TABLE IF NOT EXISTS user_favorites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    openid VARCHAR(100) NOT NULL COMMENT '用户标识',
    knowledge_id INT NOT NULL COMMENT '知识条目ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (knowledge_id) REFERENCES agri_knowledge(id) ON DELETE CASCADE,
    UNIQUE KEY uk_favorite (openid, knowledge_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户收藏';

-- 4. 用户浏览历史
CREATE TABLE IF NOT EXISTS user_browse_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    openid VARCHAR(100) NOT NULL COMMENT '用户标识',
    knowledge_id INT NOT NULL COMMENT '知识条目ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (knowledge_id) REFERENCES agri_knowledge(id) ON DELETE CASCADE,
    INDEX idx_history (openid, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='浏览历史';

-- 5. 农事提醒
CREATE TABLE IF NOT EXISTS agri_reminders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    openid VARCHAR(100) NOT NULL COMMENT '用户标识',
    title VARCHAR(255) NOT NULL COMMENT '提醒标题',
    content TEXT COMMENT '提醒内容',
    remind_date DATE NOT NULL COMMENT '提醒日期',
    remind_time TIME DEFAULT '08:00' COMMENT '提醒时间',
    remind_type ENUM('weather','crop','pesticide','custom') DEFAULT 'custom' COMMENT '类型',
    crop_type VARCHAR(100) DEFAULT '' COMMENT '关联作物',
    status ENUM('pending','completed','cancelled') DEFAULT 'pending' COMMENT '状态',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_reminder (openid, remind_date DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='农事提醒';

-- 6. 病虫害预警
CREATE TABLE IF NOT EXISTS pest_warnings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    region VARCHAR(100) NOT NULL COMMENT '地区',
    crop VARCHAR(100) NOT NULL COMMENT '作物',
    pest_name VARCHAR(255) NOT NULL COMMENT '病虫害名称',
    warning_level ENUM('low','medium','high','extreme') DEFAULT 'medium' COMMENT '预警等级',
    description TEXT COMMENT '预警描述',
    prevention_measures TEXT COMMENT '防治措施',
    start_date DATE COMMENT '开始日期',
    end_date DATE COMMENT '结束日期',
    source VARCHAR(255) DEFAULT '' COMMENT '信息来源',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_warning (region, crop, start_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='病虫害预警';

-- 7. AI 诊断日志（备份）
CREATE TABLE IF NOT EXISTS agri_advice_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    openid VARCHAR(100) NOT NULL COMMENT '用户标识',
    image_base64 TEXT COMMENT '原图base64（可选，用于回溯）',
    diagnosis TEXT COMMENT 'AI诊断结果原文',
    drugs_info TEXT COMMENT '推荐用药JSON',
    reminder_id INT DEFAULT 0 COMMENT '关联提醒ID(0表示未创建提醒)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_log (openid, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI诊断日志';
