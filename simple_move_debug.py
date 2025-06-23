#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import requests

def test_move_api():
    """直接测试移动API调用"""
    
    # 从配置文件加载信息
    with open('feishu_oauth_tokens.json', 'r', encoding='utf-8') as f:
        oauth_config = json.load(f)
    
    with open('user_feishu_config.json', 'r', encoding='utf-8') as f:
        user_config = json.load(f)
    
    access_token = oauth_config['access_token']
    space_id = user_config['space_id']
    
    # 测试一个存在的云文档token（从之前的导入结果中获取）
    # 注意：这个token需要是真实存在的云文档token
    doc_token = "doxcnAbB7Y1dSm8jvoL8jXvPgoe"  # 使用一个示例token，实际需要替换
    
    # API URL
    url = f"https://open.feishu.cn/open-apis/wiki/v2/spaces/{space_id}/nodes/move_docs_to_wiki"
    
    # 请求头
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # 测试不同的obj_type值
    test_cases = [
        {"obj_type": "docx", "desc": "新版文档"},
        {"obj_type": "doc", "desc": "旧版文档"},
        {"obj_type": "docs", "desc": "文档（复数）"},
    ]
    
    print("🔍 开始测试移动云文档到知识库API")
    print("=" * 50)
    print(f"🌐 API URL: {url}")
    print(f"📍 space_id: {space_id}")
    print(f"🏷️ doc_token: {doc_token}")
    print("")
    
    for test_case in test_cases:
        obj_type = test_case["obj_type"]
        desc = test_case["desc"]
        
        print(f"🧪 测试 obj_type: {obj_type} ({desc})")
        print("-" * 30)
        
        payload = {
            "obj_token": doc_token,
            "obj_type": obj_type,
            # 不设置parent_wiki_token，转移到知识库根目录
        }
        
        print(f"📋 请求载荷: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            
            print(f"📊 HTTP状态码: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"📄 响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
                    
                    business_code = result.get('code')
                    business_msg = result.get('msg', '无消息')
                    
                    print(f"🏢 业务代码: {business_code}")
                    print(f"📝 业务消息: {business_msg}")
                    
                    if business_code == 0:
                        print(f"✅ 成功！obj_type={obj_type} 可用")
                        data = result.get('data', {})
                        if 'task_id' in data:
                            print(f"⏳ 任务ID: {data['task_id']}")
                        if 'wiki_token' in data:
                            print(f"📖 wiki_token: {data['wiki_token']}")
                        break
                    else:
                        print(f"❌ 失败！业务错误代码: {business_code}")
                        print(f"💡 错误说明: {business_msg}")
                        
                        # 详细错误分析
                        if business_code == 230005:
                            print("   → obj_type参数不正确或文档类型不支持")
                        elif business_code == 99991663:
                            print("   → 权限不足，无法移动云文档到知识库")
                        elif business_code == 1254050:
                            print("   → 文档不存在或已被删除")
                        elif business_code == 400:
                            print("   → 请求参数格式错误")
                        else:
                            print(f"   → 未知业务错误，请查阅API文档")
                        
                except json.JSONDecodeError as e:
                    print(f"❌ JSON解析失败: {e}")
                    print(f"📄 原始响应: {response.text}")
            else:
                print(f"❌ HTTP请求失败")
                print(f"📄 响应内容: {response.text}")
                
        except Exception as e:
            print(f"❌ 请求异常: {e}")
        
        print("")  # 空行分隔
    
    print("🎯 总结:")
    print("HTTP 200 ≠ 业务成功")
    print("需要检查响应中的 'code' 字段:")
    print("- code: 0 = 成功")
    print("- code: 230005 = obj_type错误")
    print("- code: 99991663 = 权限不足")
    print("- code: 1254050 = 文档不存在")

if __name__ == "__main__":
    test_move_api() 