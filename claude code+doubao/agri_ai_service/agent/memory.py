"""
记忆系统
- SessionMemory: 短期会话记忆（滑动窗口，每会话最多 20 轮）
- UserProfileManager: 长期用户画像（基于 openid，JSON 持久化，预留向量库接口）
"""
import json
import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("agri_ai.memory")

# ====================== 数据目录 ======================
BASE_DIR = Path(__file__).parent.parent
USER_PROFILE_DIR = BASE_DIR / "data" / "user_profiles"
USER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

# ====================== 数据模型 ======================
MAX_SESSION_TURNS = 20  # 滑动窗口上限


@dataclass
class Message:
    """单条消息"""
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class SessionState:
    """短期会话状态"""
    session_id: str
    openid: str = ""
    messages: List[Message] = field(default_factory=list)

    def add_message(self, role: str, content: str):
        self.messages.append(Message(role=role, content=content))
        # 滑动窗口裁剪
        if len(self.messages) > MAX_SESSION_TURNS:
            self.messages = self.messages[-MAX_SESSION_TURNS:]

    def to_chat_history(self, max_turns: int = 10) -> str:
        """格式化为 LLM 可读的对话历史（最近 N 轮）"""
        recent = self.messages[-max_turns * 2:] if len(self.messages) > max_turns * 2 else self.messages
        lines = []
        for msg in recent:
            label = "用户" if msg.role == "user" else "助手"
            lines.append(f"{label}：{msg.content}")
        return "\n".join(lines)

    def clear(self):
        self.messages.clear()


@dataclass
class UserProfile:
    """长期用户画像"""
    openid: str
    # 基础信息（由 Agent 自动提取积累）
    region: str = ""           # 所在地区
    crops: List[str] = field(default_factory=list)  # 种植作物
    farm_size: str = ""       # 种植规模
    # 交互统计
    interaction_count: int = 0
    first_interaction: float = 0.0
    last_interaction: float = 0.0
    # 历史摘要（由 Agent 定期生成）
    history_summary: str = ""
    # 预留：向量库 embedding（后面接入）
    embedding: Optional[List[float]] = None
    # 扩展字段
    extra: Dict = field(default_factory=dict)


# ====================== 短期会话记忆 ======================

class SessionMemory:
    """
    短期会话记忆（内存级别，程序重启后丢失）
    滑动窗口保留最近 MAX_SESSION_TURNS 轮对话。

    隔离策略：按 openid 命名空间隔离，不同用户的 session_id 互不干扰。
    空 openid 统一归类到 "_anonymous" 命名空间。
    """

    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}

    @staticmethod
    def _build_key(session_id: str, openid: str = "") -> str:
        """按 openid 构建隔离的存储 key"""
        ns = openid.strip() if openid else "_anonymous"
        return f"{ns}:{session_id}"

    def get_or_create(self, session_id: str, openid: str = "") -> SessionState:
        key = self._build_key(session_id, openid)
        if key not in self._sessions:
            self._sessions[key] = SessionState(
                session_id=session_id,
                openid=openid,
            )
        return self._sessions[key]

    def add_message(self, session_id: str, role: str, content: str, openid: str = ""):
        key = self._build_key(session_id, openid)
        session = self._sessions.get(key)
        if session:
            session.add_message(role, content)

    def get_history(self, session_id: str, max_turns: int = 10, openid: str = "") -> str:
        key = self._build_key(session_id, openid)
        session = self._sessions.get(key)
        if session:
            return session.to_chat_history(max_turns)
        return ""

    def clear_session(self, session_id: str, openid: str = ""):
        key = self._build_key(session_id, openid)
        self._sessions.pop(key, None)


# ====================== 长期用户画像 ======================

class UserProfileManager:
    """
    长期用户画像管理（基于 openid，JSON 文件持久化）
    后续可替换为向量数据库实现。
    """

    def __init__(self, storage_dir: str = None):
        self._storage_dir = Path(storage_dir) if storage_dir else USER_PROFILE_DIR
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, UserProfile] = {}

    def _profile_path(self, openid: str) -> Path:
        safe_id = openid if openid else "_anonymous"
        return self._storage_dir / f"{safe_id}.json"

    def get_profile(self, openid: str) -> UserProfile:
        """获取用户画像（缓存+文件加载）"""
        if openid in self._cache:
            return self._cache[openid]

        path = self._profile_path(openid)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                profile = UserProfile(**data)
                self._cache[openid] = profile
                return profile
            except Exception as e:
                logger.warning(f"加载用户画像失败 {openid}: {e}")

        profile = UserProfile(
            openid=openid,
            first_interaction=time.time(),
            last_interaction=time.time(),
        )
        self._cache[openid] = profile
        return profile

    def save_profile(self, openid: str):
        """保存用户画像到文件"""
        profile = self._cache.get(openid)
        if not profile:
            return
        profile.last_interaction = time.time()
        path = self._profile_path(openid)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(profile), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存用户画像失败 {openid}: {e}")

    def update_profile(self, openid: str, **kwargs):
        """更新用户画像字段"""
        profile = self.get_profile(openid)
        for k, v in kwargs.items():
            if hasattr(profile, k):
                setattr(profile, k, v)
        profile.interaction_count += 1
        profile.last_interaction = time.time()
        self.save_profile(openid)

    def extract_and_update(self, openid: str, user_message: str, llm=None):
        """
        用 LLM 从用户消息中提取画像信息并更新。
        预留：后续可改为向量库 + embedding。
        """
        profile = self.get_profile(openid)
        profile.interaction_count += 1
        profile.last_interaction = time.time()

        if llm and profile.interaction_count % 15 == 1:
            # 每 3 次交互主动提取一次用户画像
            extract_prompt = f"""从用户的对话中提取画像信息，只输出 JSON。
已知信息：地区="{profile.region}"，作物={profile.crops}，规模="{profile.farm_size}"
用户消息：{user_message}

提取新信息并合并，输出格式：
{{"region":"地区","crops":["作物1","作物2"],"farm_size":"规模"}}
没有新信息就保持原值。"""
            try:
                result = llm.chat(extract_prompt, temperature=0.0)
                data = json.loads(result.strip().replace("```json", "").replace("```", ""))
                if data.get("region"):
                    profile.region = data["region"]
                if data.get("crops"):
                    profile.crops = list(set(profile.crops + data["crops"]))
                if data.get("farm_size"):
                    profile.farm_size = data["farm_size"]
            except Exception as e:
                logger.debug(f"画像提取跳过: {e}")

        self.save_profile(openid)

    def profile_summary(self, openid: str) -> str:
        """返回人类可读的画像摘要"""
        profile = self.get_profile(openid)
        parts = []
        if profile.region:
            parts.append(f"地区：{profile.region}")
        if profile.crops:
            parts.append(f"种植：{'、'.join(profile.crops)}")
        if profile.farm_size:
            parts.append(f"规模：{profile.farm_size}")
        if profile.interaction_count > 0:
            parts.append(f"对话次数：{profile.interaction_count}")
        return "；".join(parts) if parts else "新用户"
