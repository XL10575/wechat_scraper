# 🚀 GitHub Actions 免费部署指南

## 📋 部署概述

使用GitHub Actions可以实现完全免费的自动化部署，每月提供2000分钟的免费执行时间，足够每天执行一次RO自动更新任务。

## 🔧 部署步骤

### 1. 推送代码到GitHub仓库

**如果还没有GitHub仓库：**

```bash
# 初始化Git仓库
git init

# 添加所有文件
git add .

# 提交代码
git commit -m "Initial commit: WeChat scraper with auto-update"

# 连接到GitHub远程仓库（替换为你的仓库地址）
git remote add origin https://github.com/YOUR_USERNAME/wechat-scraper.git

# 推送代码
git push -u origin main
```

### 2. 配置GitHub Secrets

在GitHub仓库页面：

1. **进入Settings**
   - 点击仓库顶部的 `Settings` 标签

2. **添加Secrets**
   - 左侧菜单选择 `Secrets and variables` → `Actions`
   - 点击 `New repository secret`

3. **添加以下Secrets：**

| Secret名称 | 值 | 说明 |
|-----------|---|------|
| `FEISHU_APP_ID` | `cli_a7fb1459aafb500c` | 飞书应用ID |
| `FEISHU_APP_SECRET` | `4gFlh7eaUSkYvEFCTp1xZgGe4BHRZ0jn` | 飞书应用密钥 |
| `FEISHU_ACCESS_TOKEN` | `fILxBrgv1ejWQ3rmYHQSpQ4l5q.h04EhNq20ggSawCW8` | 飞书访问令牌 |
| `FEISHU_REFRESH_TOKEN` | 从`feishu_oauth_tokens.json`获取 | 刷新令牌 |
| `FEISHU_SPACE_TOKEN` | `Dql8w6MlxiLJLTkzpFGcPv2Fnzd` | 知识库Token |
| `FEISHU_SPACE_ID` | `7511922459407450115` | 知识库ID |

**获取令牌的具体步骤：**

从你的 `feishu_oauth_tokens.json` 文件中复制：
```json
{
  "access_token": "这里的值复制到FEISHU_ACCESS_TOKEN",
  "refresh_token": "这里的值复制到FEISHU_REFRESH_TOKEN"
}
```

从你的 `user_feishu_config.json` 文件中复制：
```json
{
  "space_token": "这里的值复制到FEISHU_SPACE_TOKEN",
  "space_id": "这里的值复制到FEISHU_SPACE_ID"
}
```

### 3. 启用GitHub Actions

1. **检查Actions状态**
   - 进入仓库的 `Actions` 标签
   - 如果显示需要启用，点击绿色按钮启用

2. **确认工作流文件**
   - 确保 `.github/workflows/auto-update.yml` 文件存在
   - GitHub会自动检测并显示工作流

### 4. 测试部署

**手动触发测试：**

1. 进入 `Actions` 标签
2. 选择 `🤖 RO文章自动更新` 工作流
3. 点击右侧的 `Run workflow` 按钮
4. 选择是否强制更新，然后点击 `Run workflow`

**查看执行日志：**
- 点击正在运行或已完成的工作流实例
- 查看每个步骤的详细日志
- 下载生成的日志文件

## ⏰ 执行时间安排

### 默认执行时间
- **每天北京时间上午10:00** 自动执行
- 对应UTC时间：02:00

### 自定义执行时间

如需修改执行时间，编辑 `.github/workflows/auto-update.yml` 文件：

```yaml
schedule:
  # 修改这行的时间（使用UTC时间）
  - cron: '0 2 * * *'  # 北京时间10:00 = UTC 02:00
```

**常用时间对照：**
- 北京时间 08:00 = UTC 00:00 → `'0 0 * * *'`
- 北京时间 12:00 = UTC 04:00 → `'0 4 * * *'`
- 北京时间 18:00 = UTC 10:00 → `'0 10 * * *'`
- 北京时间 22:00 = UTC 14:00 → `'0 14 * * *'`

## 🔧 功能特性

### ✅ 自动化功能
- **定时执行**：每天自动运行，无需人工干预
- **增量更新**：只处理新发布的文章，避免重复下载
- **智能重试**：失败时自动重试，提高成功率
- **日志记录**：详细的执行日志，便于问题诊断

### ✅ 资源优化
- **无头模式**：在Linux服务器上无界面运行
- **资源限制**：设置30分钟超时，避免资源浪费
- **缓存优化**：利用GitHub Actions的pip缓存功能

### ✅ 监控告警
- **执行状态**：GitHub Actions面板显示执行状态
- **日志下载**：自动保存执行日志，保留7天
- **失败通知**：执行失败时在Actions面板显示

## 🔍 监控和维护

### 查看执行状态
1. 进入GitHub仓库的 `Actions` 标签
2. 查看最近的工作流运行记录
3. 绿色✅表示成功，红色❌表示失败

### 下载执行日志
1. 点击具体的工作流运行实例
2. 滚动到底部的 `Artifacts` 部分
3. 下载 `auto-update-logs-xxx` 文件

### 手动触发更新
1. 进入 `Actions` → `🤖 RO文章自动更新`
2. 点击 `Run workflow`
3. 可选择"强制更新"来处理更多历史文章

## 🛠️ 故障排除

### 常见问题

**1. 飞书令牌过期**
- **现象**：执行失败，日志显示认证错误
- **解决**：更新GitHub Secrets中的令牌信息

**2. 工作流未触发**
- **现象**：到了执行时间但没有运行
- **解决**：检查cron表达式是否正确，确保仓库是公开的

**3. 下载文章失败**
- **现象**：收集到文章但下载失败
- **解决**：可能是网络问题，通常会自动重试

### 调试步骤

1. **检查Secrets配置**
   ```bash
   # 确保所有必需的Secrets都已配置
   FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_ACCESS_TOKEN, 
   FEISHU_REFRESH_TOKEN, FEISHU_SPACE_TOKEN, FEISHU_SPACE_ID
   ```

2. **查看详细日志**
   - 展开失败的步骤查看具体错误信息
   - 关注网络连接和认证相关的错误

3. **手动测试**
   - 使用"手动触发"功能测试
   - 启用"强制更新"获取更多日志信息

## 💰 成本分析

### 完全免费！
- **GitHub Actions**：每月2000分钟免费额度
- **每次执行时间**：约5-15分钟（取决于文章数量）
- **每月消耗**：约150-450分钟（每天执行一次）
- **剩余额度**：足够支持其他项目使用

### 对比其他方案
| 方案 | 月费用 | 优缺点 |
|-----|--------|-------|
| GitHub Actions | 🆓 免费 | ✅ 零成本，✅ 稳定，❌ 有时间限制 |
| VPS服务器 | ¥30-100 | ✅ 无限制，❌ 需要成本，❌ 需要运维 |
| 云函数 | ¥5-20 | ✅ 按需付费，❌ 冷启动慢 |

## 🎉 部署完成

完成上述步骤后，你的RO自动更新系统就已经部署完成了！

### 验证部署成功的标志：
1. ✅ GitHub Actions显示工作流已激活
2. ✅ 手动触发测试执行成功
3. ✅ 飞书知识库中能看到新上传的文章
4. ✅ 执行日志显示完整的处理流程

### 日常使用：
- **无需任何操作**：系统每天自动运行
- **查看结果**：在飞书知识库查看新文章
- **监控状态**：偶尔查看GitHub Actions执行状态
- **手动补充**：如有需要可手动触发更新

**🎊 恭喜！你现在拥有了一个完全自动化的、零成本的微信文章收集系统！** 