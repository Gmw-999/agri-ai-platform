import { useState } from "react";
import BottomNav from "../components/BottomNav";

const categories = [
  { key: "grain", label: "粮食作物" },
  { key: "veg", label: "蔬菜" },
  { key: "fruit", label: "水果" },
  { key: "flower", label: "花卉" },
  { key: "cash", label: "经济作物" },
];

const diseaseDB: Record<string, Array<{ name: string; desc: string; cat: string }>> = {
  grain: [
    { name: "水稻稻瘟病", desc: "真菌性病害，高温高湿易发", cat: "grain" },
    { name: "玉米蚜虫", desc: "刺吸式害虫，传播病毒", cat: "grain" },
    { name: "小麦白粉病", desc: "真菌性，叶面白粉状斑", cat: "grain" },
    { name: "水稻纹枯病", desc: "真菌性，叶鞘云纹状病斑", cat: "grain" },
    { name: "玉米大斑病", desc: "真菌性，叶片长梭形病斑", cat: "grain" },
    { name: "小麦锈病", desc: "真菌性，叶片锈黄色粉状", cat: "grain" },
  ],
  veg: [
    { name: "番茄晚疫病", desc: "卵菌纲，叶片水渍状", cat: "veg" },
    { name: "黄瓜霜霉病", desc: "真菌性，叶角状黄斑", cat: "veg" },
    { name: "白菜软腐病", desc: "细菌性，基部软腐", cat: "veg" },
    { name: "辣椒疫病", desc: "卵菌纲，茎基黑褐色", cat: "veg" },
  ],
  fruit: [
    { name: "苹果轮纹病", desc: "真菌性，果实轮纹斑", cat: "fruit" },
    { name: "葡萄霜霉病", desc: "卵菌纲，叶背白霉", cat: "fruit" },
    { name: "柑橘黄龙病", desc: "细菌性，叶片黄化", cat: "fruit" },
    { name: "桃褐腐病", desc: "真菌性，果实褐腐", cat: "fruit" },
  ],
  flower: [
    { name: "月季黑斑病", desc: "真菌性，叶片黑斑", cat: "flower" },
    { name: "兰花炭疽病", desc: "真菌性，叶斑凹陷", cat: "flower" },
  ],
  cash: [
    { name: "棉花枯萎病", desc: "真菌性，维管束褐变", cat: "cash" },
    { name: "大豆胞囊线虫", desc: "线虫病害，根系结瘤", cat: "cash" },
    { name: "花生叶斑病", desc: "真菌性，叶面黄斑", cat: "cash" },
  ],
};

export default function KnowledgeBase() {
  const [activeCat, setActiveCat] = useState("grain");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<{ name: string; desc: string } | null>(null);

  const allDiseases = Object.values(diseaseDB).flat();

  const filtered = search.trim()
    ? allDiseases.filter(
        (d) =>
          d.name.includes(search) ||
          d.desc.includes(search)
      )
    : diseaseDB[activeCat] || [];

  const handleDiseaseClick = (d: { name: string; desc: string }) => {
    setSelected(d);
  };

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header">
        <div className="header-left">
          <h1 className="header-title">病害知识库</h1>
        </div>
      </div>

      <div className="kb-content">
        {/* Search */}
        <div className="kb-search">
          <img src="/src/assets/images/search.png" alt="" className="search-icon" />
          <input
            type="text"
            placeholder="搜索作物 / 病害名称"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="kb-search-input"
          />
        </div>

        {/* Category Tabs */}
        {!search.trim() && (
          <div className="kb-categories">
            {categories.map((cat) => (
              <button
                key={cat.key}
                className={`kb-cat-tab ${activeCat === cat.key ? "active" : ""}`}
                onClick={() => setActiveCat(cat.key)}
              >
                {cat.label}
              </button>
            ))}
          </div>
        )}

        {/* Detail View */}
        {selected ? (
          <div className="kb-detail">
            <button className="kb-detail-back" onClick={() => setSelected(null)}>
              <img src="/src/assets/images/chevronleft.png" alt="" />
              返回列表
            </button>
            <div className="kb-detail-card">
              <h2 className="kb-detail-name">{selected.name}</h2>
              <p className="kb-detail-desc">{selected.desc}</p>
              <div className="kb-detail-actions">
                <button
                  className="kb-ask-btn"
                  onClick={() => {
                    window.location.href = `/ai-chat?q=${encodeURIComponent(
                      `${selected.name}怎么防治`
                    )}`;
                  }}
                >
                  咨询 AI 助手
                </button>
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* Empty State */}
            {search.trim() && filtered.length === 0 && (
              <div className="kb-empty">
                <img src="/src/assets/images/searchx.png" alt="" />
                <p className="kb-empty-title">未找到相关病害</p>
                <p className="kb-empty-sub">
                  没有找到「{search}」的相关内容
                  <br />
                  试试换个关键词搜索
                </p>
                <button
                  className="kb-ask-btn"
                  onClick={() => {
                    window.location.href = `/ai-chat?q=${encodeURIComponent(search)}`;
                  }}
                >
                  咨询 AI 助手
                </button>
              </div>
            )}

            {/* Disease List */}
            {filtered.length > 0 && (
              <div className="kb-list">
                {filtered.map((disease, i) => (
                  <div
                    key={i}
                    className="kb-list-item"
                    onClick={() => handleDiseaseClick(disease)}
                  >
                    <div className="kb-item-icon">
                      <img
                        src={
                          disease.cat === "grain"
                            ? "/src/assets/images/sprout.png"
                            : "/src/assets/images/leaf.png"
                        }
                        alt=""
                      />
                    </div>
                    <div className="kb-item-info">
                      <p className="kb-item-name">{disease.name}</p>
                      <p className="kb-item-desc">{disease.desc}</p>
                    </div>
                    <img
                      src="/src/assets/images/chevronright.png"
                      alt=""
                      className="kb-item-arrow"
                    />
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      <BottomNav />
    </div>
  );
}
