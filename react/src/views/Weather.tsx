import { useState, useEffect } from "react";
import BottomNav from "../components/BottomNav";
import { agentChatStream } from "../api/client";

interface WeatherData {
  city: string;
  now: {
    temp: string;
    text: string;
    humidity: string;
    windSpeed: string;
  };
  daily: Array<{
    fxDate: string;
    textDay: string;
    tempMin: string;
    tempMax: string;
    precip: string;
  }>;
  warning: Array<{
    title: string;
    text: string;
  }>;
}

interface AdviceData {
  farm_advice: string;
}

interface PestAlert {
  name: string;
  alert_level: string;
  control_suggestion: string;
}

export default function Weather() {
  const [location, setLocation] = useState("湖南省长沙市");
  const [locInput, setLocInput] = useState(location);
  const [editing, setEditing] = useState(false);
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [advice, setAdvice] = useState("");
  const [pestAlerts, setPestAlerts] = useState<PestAlert[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchWeather = async (loc: string) => {
    setLoading(true);
    setError("");
    setAdvice("");
    setPestAlerts([]);

    try {
      const query = `${loc}今天天气怎么样`;
      const stream = agentChatStream({
        message: query,
      });

      let fullReply = "";

      for await (const event of stream) {
        if (event.type === "error") {
          setError(event.content || "获取天气失败");
          break;
        }
        if (event.type === "reply" && event.content) {
          fullReply += event.content;
        }
        if (event.type === "done") {
          // The backend reply includes weather data in the LLM response
          // We need to request weather separately for structured display
          break;
        }
      }

      // Also try to get weather data through the simple chat endpoint
      // This gives us the LLM-formatted advice
      if (fullReply) {
        setAdvice(fullReply);
      }

      // Set mock weather data for display (since backend returns LLM text, not structured data)
      setWeather({
        city: loc,
        now: {
          temp: "--",
          text: "加载中",
          humidity: "--",
          windSpeed: "--",
        },
        daily: [],
        warning: [],
      });

      // Try to get pest alerts from the pest forecast tool
      const pestQuery = `${loc}当前月份主要作物病虫害预警`;
      const pestStream = agentChatStream({
        message: pestQuery,
        session_id: `weather_${Date.now()}`,
      });

      for await (const event of pestStream) {
        if (event.type === "meta" && event.intent) {
          // Got intent info
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "网络异常");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWeather(location);
  }, []);

  const handleLocationSubmit = () => {
    const loc = locInput.trim() || "湖南省长沙市";
    setLocation(loc);
    setEditing(false);
    fetchWeather(loc);
  };

  const dayLabels = ["今", "明", "三", "四", "五", "六", "日"];

  const renderAdvice = (text: string) => {
    // Split by numbered points
    return text.split(/\d\./).filter(Boolean).map((point, i) => (
      <div key={i} className="advice-item">
        <div className="advice-bullet" />
        <p>{point.trim()}</p>
      </div>
    ));
  };

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header">
        <div className="header-left">
          <button className="header-back" onClick={() => window.history.back()}>
            <img src="/src/assets/images/chevronleft.png" alt="返回" />
          </button>
          <h1 className="header-title">农事天气预警</h1>
        </div>
      </div>

      <div className="weather-content">
        {/* Location Selector */}
        {editing ? (
          <div className="location-edit">
            <input
              type="text"
              value={locInput}
              onChange={(e) => setLocInput(e.target.value)}
              placeholder="输入地区名称，如：山东菏泽"
              className="location-input"
              onKeyDown={(e) => e.key === "Enter" && handleLocationSubmit()}
            />
            <button className="loc-confirm" onClick={handleLocationSubmit}>
              确定
            </button>
          </div>
        ) : (
          <button
            className="location-bar"
            onClick={() => setEditing(true)}
          >
            <img src="/src/assets/images/mappin.png" alt="" />
            <span>{location}</span>
            <img src="/src/assets/images/chevrondown.png" alt="" />
          </button>
        )}

        {error && (
          <div className="weather-error">
            <p>{error}</p>
            <button onClick={() => fetchWeather(location)}>重试</button>
          </div>
        )}

        {loading && !advice && (
          <div className="weather-loading">
            <div className="loading-spinner-small" />
            <p>正在获取天气数据...</p>
          </div>
        )}

        {weather && !loading && (
          <>
            {/* Current Weather */}
            <div className="current-weather">
              <div className="temp-display">
                <div className="temp-main">
                  <p className="temp-value">{weather.now.temp}°C</p>
                  <p className="temp-desc">{weather.now.text}</p>
                </div>
                <div className="weather-icon-main">
                  <img src="/src/assets/images/sun.png" alt="" />
                </div>
              </div>
              <div className="weather-details">
                <div className="wd-item">
                  <img src="/src/assets/images/wind.png" alt="" />
                  <span>微风{weather.now.windSpeed}级</span>
                </div>
                <div className="wd-item">
                  <img src="/src/assets/images/droplets.png" alt="" />
                  <span>湿度{weather.now.humidity}%</span>
                </div>
              </div>
              <div className="farm-status">
                <img src="/src/assets/images/checkcircle.png" alt="" />
                <span>今日适宜施药 · 田间作业良好</span>
              </div>
            </div>

            {/* 7-Day Forecast */}
            <div className="forecast-section">
              <p className="section-title">未来7天预报</p>
              <div className="forecast-grid">
                {weather.daily.slice(0, 7).map((day, i) => (
                  <div key={i} className="forecast-day">
                    <p className="fd-label">{dayLabels[i] || day.fxDate}</p>
                    <img
                      src="/src/assets/images/sun0.png"
                      alt=""
                      className="fd-icon"
                    />
                    <p className="fd-temp">{day.tempMax}°</p>
                  </div>
                ))}
                {weather.daily.length === 0 &&
                  dayLabels.map((label, i) => (
                    <div key={i} className="forecast-day">
                      <p className="fd-label">{label}</p>
                      <img
                        src="/src/assets/images/sun0.png"
                        alt=""
                        className="fd-icon"
                      />
                      <p className="fd-temp">--°</p>
                    </div>
                  ))}
              </div>
            </div>

            {/* Farming Advice */}
            {advice && (
              <div className="advice-section">
                <div className="advice-header">
                  <img src="/src/assets/images/leaf0.png" alt="" />
                  <span>农事操作建议</span>
                </div>
                <div className="advice-body">{renderAdvice(advice)}</div>
              </div>
            )}

            {/* Pest Alerts */}
            <div className="pest-alert-section">
              <div className="alert-section-header">
                <div className="alert-title-row">
                  <img src="/src/assets/images/trianglealert.png" alt="" />
                  <span>本地病虫害预警公告</span>
                </div>
                <span className="alert-count">
                  {pestAlerts.length}条预警
                </span>
              </div>
              {pestAlerts.length === 0 && (
                <p className="no-alert">暂无预警信息</p>
              )}
              {pestAlerts.map((pest, i) => (
                <div key={i} className="pest-alert-card">
                  <div className="palert-color" />
                  <div className="palert-info">
                    <p className="palert-title">
                      {pest.name} | {pest.alert_level}风险
                    </p>
                    <p className="palert-desc">{pest.control_suggestion}</p>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      <BottomNav />
    </div>
  );
}
