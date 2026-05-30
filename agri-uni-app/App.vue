<script setup>
import { onShow, onHide } from '@dcloudio/uni-app';
onShow(() => {});
onHide(() => {});
</script>

<style>
/* ===== Global Styles ===== */
page {
  --brand-green: #2e8b57;
  --brand-green-mid: #4caf82;
  --brand-green-light: #e8f5e9;
  --primary-green: #27ae60;
  --danger-red: #e74c3c;
  --warning-orange: #f39c12;
  --page-bg: #f8f9fa;
  --card-white: #ffffff;
  --text-primary: #333333;
  --text-secondary: #666666;
  --text-gray: #999999;
  --border-color: #e8e8e8;
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;

  background-color: var(--page-bg);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
    "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.5;
  box-sizing: border-box;
}

view, scroll-view, swiper, text, image, input, button, navigator {
  box-sizing: border-box;
}

.page-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--page-bg);
}

.page-content {
  flex: 1;
  padding: 12px 16px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 44px;
  padding: 0 16px;
  background: var(--card-white);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
  position: relative;
}

.header-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
}

.header-action {
  font-size: 13px;
  color: var(--text-secondary);
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  background: var(--page-bg);
}

.section-card {
  background: var(--card-white);
  border-radius: var(--radius-md);
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.section-more {
  font-size: 12px;
  color: var(--brand-green);
}

/* CTA Card */
.home-cta-card {
  background: linear-gradient(135deg, var(--brand-green), var(--brand-green-mid));
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}

.cta-icon {
  width: 48px;
  height: 48px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cta-icon image {
  width: 28px;
  height: 28px;
}

.cta-title {
  font-size: 17px;
  font-weight: 600;
  color: white;
  margin-bottom: 4px;
}

.cta-sub {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.85);
}

/* Quick Actions */
.quick-actions-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}

.quick-action-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 14px 4px;
  background: var(--card-white);
  border-radius: var(--radius-md);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  width: calc(25% - 8px);
}

.quick-action-card:active {
  opacity: 0.8;
}

.qa-icon image {
  width: 28px;
  height: 28px;
}

.qa-label {
  font-size: 12px;
  color: var(--text-primary);
  font-weight: 500;
}

/* Alert */
.alert-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
}

.alert-item:last-child {
  border-bottom: none;
}

.alert-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  white-space: nowrap;
  font-weight: 500;
  flex-shrink: 0;
  margin-top: 2px;
}

.alert-tag.high {
  background: #fde8e8;
  color: var(--danger-red);
}

.alert-tag.mid {
  background: #fef3e2;
  color: var(--warning-orange);
}

.alert-text {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.5;
}

/* Crop Items */
.crop-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
}

.crop-item:last-child {
  border-bottom: none;
}

.crop-item image {
  width: 36px;
  height: 36px;
}

.crop-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.crop-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
}

/* Chat */
.chat-messages {
  flex: 1;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
}

.chat-bubble {
  display: flex;
  gap: 10px;
  max-width: 85%;
}

.chat-bubble.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.assistant-avatar {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  border-radius: 50%;
  overflow: hidden;
  background: var(--brand-green-light);
  display: flex;
  align-items: center;
  justify-content: center;
}

.assistant-avatar image {
  width: 28px;
  height: 28px;
}

.bubble-text {
  padding: 10px 14px;
  border-radius: var(--radius-md);
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.chat-bubble.assistant .bubble-text {
  background: var(--card-white);
  color: var(--text-primary);
  border-top-left-radius: 2px;
}

.chat-bubble.user .bubble-text {
  background: var(--brand-green);
  color: white;
  border-top-right-radius: 2px;
}

.bubble-image {
  width: 160px;
  height: 160px;
  border-radius: var(--radius-sm);
  margin-bottom: 6px;
}

.chat-input-area {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--card-white);
  border-top: 1px solid var(--border-color);
  flex-shrink: 0;
}

.input-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  flex-shrink: 0;
}

.input-btn image {
  width: 20px;
  height: 20px;
}

.upload-btn {
  background: var(--page-bg);
}

.send-btn {
  background: var(--brand-green);
}

.send-btn image {
  width: 18px;
  height: 18px;
}

.input-wrapper {
  flex: 1;
  background: var(--page-bg);
  border-radius: 20px;
  padding: 0 14px;
  height: 36px;
  display: flex;
  align-items: center;
}

.chat-input {
  width: 100%;
  font-size: 14px;
  color: var(--text-primary);
  background: transparent;
}

/* Weather */
.location-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
  padding: 12px 0;
}

.location-bar image {
  width: 16px;
  height: 16px;
}

.current-weather {
  background: linear-gradient(135deg, #43a047, #66bb6a);
  border-radius: var(--radius-lg);
  padding: 20px;
  color: white;
  margin-bottom: 12px;
}

.temp-display {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.temp-value {
  font-size: 42px;
  font-weight: 700;
}

.temp-desc {
  font-size: 15px;
  margin-top: 4px;
}

.weather-details {
  display: flex;
  gap: 24px;
  margin-top: 12px;
}

.wd-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  opacity: 0.9;
}

.wd-item image {
  width: 18px;
  height: 18px;
}

.farm-status {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
  font-size: 13px;
}

.forecast-grid {
  display: flex;
  justify-content: space-between;
  margin-top: 12px;
}

.forecast-day {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.fd-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.fd-temp {
  font-size: 14px;
  font-weight: 500;
}

.advice-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
}

.advice-header image {
  width: 18px;
  height: 18px;
}

.advice-header text {
  font-size: 14px;
  font-weight: 600;
}

.advice-item {
  display: flex;
  gap: 8px;
  padding: 6px 0;
  font-size: 13px;
  line-height: 1.6;
}

.advice-bullet {
  width: 6px;
  height: 6px;
  background: var(--brand-green);
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 8px;
}

/* Knowledge Base */
.kb-search {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--card-white);
  border-radius: 20px;
  padding: 0 14px;
  border: 1px solid var(--border-color);
  margin-bottom: 12px;
  height: 40px;
}

.kb-search image {
  width: 18px;
  height: 18px;
}

.kb-search-input {
  flex: 1;
  height: 100%;
  font-size: 14px;
}

.kb-categories {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  white-space: nowrap;
  overflow-x: auto;
  flex-wrap: nowrap;
}

.kb-cat-tab {
  padding: 6px 16px;
  border-radius: 16px;
  font-size: 13px;
  background: var(--card-white);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  white-space: nowrap;
  display: inline-block;
  flex-shrink: 0;
}

.kb-cat-tab.active {
  background: var(--brand-green);
  color: white;
  border-color: var(--brand-green);
}

.kb-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.kb-list-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  background: var(--card-white);
  border-radius: var(--radius-md);
  margin-bottom: 8px;
}

.kb-list-item:active {
  opacity: 0.8;
}

.kb-item-name {
  font-size: 14px;
  font-weight: 500;
}

.kb-item-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
}

/* Profile */
.profile-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px 16px;
  background: var(--card-white);
  margin-bottom: 1px;
}

.profile-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--brand-green-light);
  display: flex;
  align-items: center;
  justify-content: center;
}

.profile-avatar image {
  width: 36px;
  height: 36px;
}

.profile-name {
  font-size: 18px;
  font-weight: 600;
}

.profile-location {
  font-size: 13px;
  color: var(--text-secondary);
}

.profile-tags {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}

.profile-tag {
  padding: 2px 10px;
  background: var(--brand-green-light);
  color: var(--brand-green);
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.profile-stats {
  display: flex;
  align-items: center;
  justify-content: space-around;
  background: var(--card-white);
  padding: 16px;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  text-align: center;
}

.stat-label {
  font-size: 12px;
  color: var(--text-secondary);
  text-align: center;
  margin-top: 2px;
}

.stat-divider {
  width: 1px;
  height: 36px;
  background: var(--border-color);
}

.profile-menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: var(--card-white);
  border-bottom: 1px solid var(--border-color);
}

.menu-item-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.menu-item-left image {
  width: 20px;
  height: 20px;
}

.menu-item-left text {
  font-size: 14px;
}

/* Reminder / Calendar shared */
.quick-action-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 4px;
  background: var(--card-white);
  border-radius: var(--radius-md);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.quick-action-btn:active { opacity: 0.8; }

.form-group {
  margin-bottom: 16px;
}

.form-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 6px;
  display: block;
}

.form-input {
  width: 100%;
  height: 42px;
  background: var(--card-white);
  border-radius: var(--radius-sm);
  padding: 0 14px;
  font-size: 14px;
  border: 1px solid var(--border-color);
}

.form-textarea {
  width: 100%;
  min-height: 100px;
  background: var(--card-white);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
  font-size: 14px;
  border: 1px solid var(--border-color);
  line-height: 1.6;
}

.load-more {
  text-align: center;
  padding: 16px 0;
}

.empty-state,
.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 24px;
  text-align: center;
}

.empty-state image,
.error-state image {
  width: 64px;
  height: 64px;
  margin-bottom: 16px;
}

.empty-title,
.error-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
}

.empty-desc,
.error-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 24px;
}

.primary-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 24px;
  background: var(--brand-green);
  color: white;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
}
</style>
