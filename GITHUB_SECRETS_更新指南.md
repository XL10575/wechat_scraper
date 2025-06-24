# GitHub Secrets 更新指南

## 🔑 需要更新的Secrets值

基于最新的飞书OAuth认证，请在GitHub仓库中更新以下Secrets：

### 📋 Secrets列表

| Secret名称 | 值 |
|-----------|-----|
| `FEISHU_APP_ID` | `cli_a8c822312a75901c` |
| `FEISHU_APP_SECRET` | `NDbCyKEwEIA8CZo2KHyqueIOlcafErko` |
| `FEISHU_ACCESS_TOKEN` | `u-dvl9QYTD96HrM8m5gGG8jf00iaIlg48rjy00g4U82afk` |
| `FEISHU_REFRESH_TOKEN` | `ur-cEtq.lDsJ77GSEnMpn_8Z100i8Klg40hqO00l0E82efh` |
| `FEISHU_SPACE_TOKEN` | `Dql8w6MlxiLJLTkzpFGcPv2Fnzd` |
| `FEISHU_SPACE_ID` | `7511922459407450115` |

### 📝 更新步骤

1. **访问GitHub仓库设置**
   - 打开您的GitHub仓库
   - 点击 `Settings` 标签
   - 在左侧菜单中选择 `Secrets and variables` → `Actions`

2. **更新现有Secrets**
   - 对于每个已存在的Secret，点击 `Update` 按钮
   - 粘贴上表中对应的新值
   - 点击 `Update secret` 保存

3. **添加新的Secrets**（如果不存在）
   - 点击 `New repository secret` 按钮
   - 输入Secret名称和对应的值
   - 点击 `Add secret` 保存

## 🔄 验证更新

更新完成后，您可以：

1. **手动触发workflow**
   - 进入 `Actions` 标签
   - 选择 `Auto Update RO Articles Enhanced` workflow
   - 点击 `Run workflow` 按钮

2. **检查运行结果**
   - 查看workflow运行日志
   - 确认没有认证错误
   - 验证文章收集和上传功能正常

## ⚠️ 重要提醒

- **不要泄露Secrets值**：这些值包含敏感信息，请勿在公开场合分享
- **定期更新**：access token有一定的有效期，如果再次出现认证错误，请重新运行OAuth流程
- **备份配置**：建议保存这些值的备份，以防需要重新配置

## 🆘 故障排除

如果更新后仍然出现认证错误：

1. 检查Secret名称是否完全匹配（区分大小写）
2. 确认Secret值没有多余的空格或换行符
3. 重新运行 `python feishu_oauth_client.py` 获取新的token
4. 联系技术支持获取帮助

## 📞 技术支持

如果遇到问题，请提供：
- 错误信息的完整日志
- workflow运行的时间戳
- 已更新的Secrets列表

---

*最后更新时间：2025-06-24 12:28:25* 