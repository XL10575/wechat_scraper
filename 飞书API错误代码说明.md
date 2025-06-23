# 飞书移动云文档到知识库API错误代码说明

## 重要提醒 ⚠️

**HTTP 200状态码 ≠ 业务成功**

飞书API的特点是即使业务逻辑失败，也会返回HTTP 200状态码。真正的成功/失败状态需要检查响应JSON中的`code`字段。

## API格式

```
POST https://open.feishu.cn/open-apis/wiki/v2/spaces/{space_id}/nodes/move_docs_to_wiki
```

## 正确的成功判断

```json
{
    "code": 0,  // 0表示成功，非0表示失败
    "msg": "success",
    "data": {
        "task_id": "7536...",  // 异步任务ID
        // 或者
        "wiki_token": "wiki..."  // 直接返回的wiki令牌
    }
}
```

## 常见错误代码及解决方案

### 1. 错误代码：230005
**含义**：obj_type参数不正确或文档类型不支持
**HTTP状态码**：200 ✅
**业务状态**：失败 ❌

**可能原因**：
- `obj_type`参数值错误
- 云文档类型与指定的obj_type不匹配
- 文档token无效

**解决方案**：
```python
# 按顺序尝试不同的obj_type值
obj_types = ["docx", "doc", "docs"]
for obj_type in obj_types:
    payload = {
        "obj_token": doc_token,
        "obj_type": obj_type,
        "parent_wiki_token": parent_node_token  # 可选
    }
    # 发送请求...
    if result.get('code') == 0:
        break  # 成功就停止尝试
```

### 2. 错误代码：99991663
**含义**：权限不足
**HTTP状态码**：200 ✅
**业务状态**：失败 ❌

**可能原因**：
- 应用缺少"移动云文档到知识库"权限
- 用户对目标知识库没有写入权限
- OAuth令牌权限范围不足

**解决方案**：
1. 检查应用权限配置
2. 确认用户对知识库有管理权限
3. 重新获取包含所需权限的OAuth令牌

### 3. 错误代码：1254050
**含义**：文档不存在或已被删除
**HTTP状态码**：200 ✅
**业务状态**：失败 ❌

**可能原因**：
- doc_token无效或已过期
- 云文档已被删除
- token格式错误

**解决方案**：
1. 验证doc_token的有效性
2. 重新生成云文档并获取新的token
3. 检查token提取逻辑是否正确

### 4. 错误代码：400
**含义**：请求参数格式错误
**HTTP状态码**：200 ✅
**业务状态**：失败 ❌

**可能原因**：
- space_id格式不正确
- parent_wiki_token格式错误
- 请求JSON格式有误

**解决方案**：
1. 验证space_id格式（通常是数字字符串）
2. 检查parent_wiki_token格式
3. 确认JSON载荷格式正确

## 正确的错误处理代码

```python
response = requests.post(url, json=payload, headers=headers)

# 第一步：检查HTTP状态码
if response.status_code != 200:
    print(f"HTTP请求失败: {response.status_code}")
    return None

# 第二步：检查业务状态码
try:
    result = response.json()
    business_code = result.get('code')
    
    if business_code == 0:
        # 业务成功
        data = result.get('data', {})
        if 'task_id' in data:
            return data['task_id']  # 异步任务
        elif 'wiki_token' in data:
            return data['wiki_token']  # 直接成功
    else:
        # 业务失败，处理具体错误
        error_msg = result.get('msg', '未知错误')
        print(f"业务失败: code={business_code}, msg={error_msg}")
        
        if business_code == 230005:
            # 尝试其他obj_type
            pass
        elif business_code == 99991663:
            # 检查权限
            pass
        # ... 其他错误处理
        
except json.JSONDecodeError:
    print("响应不是有效的JSON格式")
    return None
```

## 推荐的obj_type测试顺序

基于官方文档和实际测试，推荐的测试顺序：

1. **docx** - 新版文档（推荐）
2. **doc** - 旧版文档
3. **docs** - 文档复数形式（某些情况下有效）

## 异步任务处理

如果返回`task_id`，需要查询任务状态：

```python
task_url = f"https://open.feishu.cn/open-apis/wiki/v2/tasks/{task_id}"
# 定期查询直到任务完成
```

## 总结

1. **永远检查business_code而不是HTTP状态码**
2. **HTTP 200 + code != 0 = 业务失败**
3. **根据具体错误代码采取对应的解决方案**
4. **测试多种obj_type值以提高成功率**
5. **正确处理异步任务结果** 