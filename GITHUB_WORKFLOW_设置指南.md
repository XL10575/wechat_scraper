# GitHub Actions 自动更新设置指南

## 问题现状
你的workflow已经创建成功，但运行失败了，因为缺少微信登录状态。

## 解决方案

### 第一步：获取微信登录状态
运行设置助手脚本：
```bash
python setup_github_secrets.py
```

这个脚本会：
1. 打开浏览器显示微信二维码
2. 你扫码登录微信
3. 自动搜索"仙境传说RO新启航"公众号
4. 保存登录状态
5. 生成GitHub Secrets所需的值

### 第二步：设置GitHub Secrets
脚本运行成功后，会输出两个Secret值，你需要将它们添加到GitHub仓库中：

1. 打开你的GitHub仓库页面
2. 点击 **Settings** 标签
3. 在左侧菜单中点击 **Secrets and variables** -> **Actions**
4. 点击 **New repository secret** 按钮
5. 添加以下两个secrets：

```
Secret名称: WECHAT_COOKIES_B64
Secret值: [脚本输出的长字符串]

Secret名称: WECHAT_USER_AGENT  
Secret值: [脚本输出的User-Agent字符串]
```

### 第三步：手动触发workflow测试
设置完Secrets后：

1. 打开你的GitHub仓库页面
2. 点击 **Actions** 标签
3. 在左侧找到 **"🤖 RO文章自动更新"** workflow
4. 点击右侧的 **"Run workflow"** 按钮
5. 在弹出窗口中：
   - 选择分支（通常是`main`）
   - ✅ 勾选 **"强制执行更新（忽略日期检查）"**
   - 点击绿色的 **"Run workflow"** 按钮

## 自动执行
设置完成后，workflow会：
- 每天北京时间上午10:00自动执行
- 自动收集新文章并上传到飞书
- 你也可以随时手动触发

## 故障排除

### 如果workflow仍然失败：
1. 检查是否所有飞书相关的Secrets都已设置：
   - `FEISHU_APP_ID`
   - `FEISHU_APP_SECRET`
   - `FEISHU_ACCESS_TOKEN`
   - `FEISHU_REFRESH_TOKEN`
   - `FEISHU_SPACE_TOKEN`
   - `FEISHU_SPACE_ID`

2. 检查微信登录状态Secrets：
   - `WECHAT_COOKIES_B64`
   - `WECHAT_USER_AGENT`

### 如果需要重新获取微信登录状态：
重新运行 `python setup_github_secrets.py` 并更新GitHub Secrets。

## 查看执行日志
在GitHub Actions页面可以查看每次执行的详细日志，帮助诊断问题。 