import xml.etree.ElementTree as ET

def update_en(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    for message in root.iter('message'):
        source = message.find('source').text
        translation = message.find('translation')
        if translation is not None:
            translation.text = source
            if 'type' in translation.attrib:
                del translation.attrib['type']
    tree.write(file_path, encoding='utf-8', xml_declaration=True)

def update_zh(file_path):
    translations = {
        "AI Configuration": "AI 配置",
        "Configure AI provider and API key.": "配置 AI 提供商和 API 密钥。",
        "Provider:": "提供商:",
        "Base URL:": "基础 URL:",
        "Model:": "模型:",
        "API Key:": "API 密钥:",
        "Test Connection": "测试连接",
        "Testing...": "测试中...",
        "Connection Successful": "连接成功",
        "Connection Failed": "连接失败",
        "Language Settings": "语言设置",
        "Choose the interface language and target translation language.": "选择界面语言和目标翻译语言。",
        "Interface Language:": "界面语言:",
        "Target Language:": "目标语言:",
        "sublingo": "sublingo",
        "Ready": "就绪",
        "Home": "首页",
        "Tasks": "任务",
        "Settings": "设置",
        "Other Settings": "其他设置",
        "Configure cookies, output directory, and proxy.": "配置 Cookie、输出目录和代理。",
        "Cookie File:": "Cookie 文件:",
        "Text Files (*.txt)": "文本文件 (*.txt)",
        "Import": "导入",
        "Validate": "验证",
        "Output Directory:": "输出目录:",
        "Proxy:": "代理:",
        "Import Successful": "导入成功",
        "Cookie file imported.": "Cookie 文件已导入。",
        "Validation Passed": "验证通过",
        "Validation Failed": "验证失败",
        "Status: Not imported": "状态: 未导入",
        "Status: {} ({} bytes)": "状态: {} ({} 字节)",
        "Status: {}": "状态: {}",
        "Sublingo Setup Wizard": "Sublingo 设置向导",
        "< Back": "< 上一步",
        "Next >": "下一步 >",
        "Finish": "完成",
        "Cancel": "取消",
        "Batch Preview": "批处理预览",
        "Include": "包含",
        "Title": "标题",
        "Duration": "时长",
        "Subtitles Available": "字幕可用",
        "Unnamed Video": "未命名视频",
        "Yes": "有",
        "No": "无",
        "New Task": "新建任务",
        "Type:": "类型:",
        "Preview": "预览",
        "Create Task": "创建任务",
        "Active Tasks": "活动任务",
        "Enter video URL or YouTube playlist URL (one per line)": "输入视频 URL 或 YouTube 播放列表 URL (每行一个)",
        "URL:": "URL:",
        "Generate Transcript": "生成转录文本",
        "Subtitle File:": "字幕文件:",
        "Video File:": "视频文件:",
        "Font File (Optional):": "字体文件 (可选):",
        "Font File:": "字体文件:",
        "Error": "错误",
        "Please enter at least one URL": "请输入至少一个 URL",
        "Invalid Cookie File": "Cookie 文件无效",
        "Fetching video info...": "正在获取视频信息...",
        "Parsing URL ({current}/{total}):\n{url}": "正在解析 URL ({current}/{total}):\n{url}",
        "No videos found": "未找到任何视频",
        "Please select at least one video": "请至少选择一个视频",
        "Failed to fetch video info: {error}": "获取视频信息失败: {error}",
        "Please fill in all required fields": "请填写所有必填字段",
        "Continue": "继续",
        "Translation": "翻译",
        "Generate Transcript in Workflow": "全流程时生成转录",
        "Cookie": "Cookie",
        "Output Paths": "输出路径",
        "Project Working Directory:": "项目工作目录:",
        "Final Output Directory:": "最终输出目录:",
        "AI": "AI",
        "Segment Batch Size:": "断句批次:",
        "Translate Batch Size:": "翻译批次:",
        "Proofread Batch Size:": "校对批次:",
        "Max Retries:": "最大重试:",
        "Proxy Address:": "代理地址:",
        "Maintenance": "维护",
        "Enable Debug Mode (Show Detailed Logs)": "启用调试模式（显示详细日志）",
        "Reset All Settings": "重置所有设置",
        "Reset to Default": "重置为默认值",
        "Information": "提示",
        "Interface language saved. Restart the application to take effect.": "界面语言已保存，重启应用后生效。",
        "Cookie file updated": "Cookie 文件已更新",
        "Cookie Status: Not Imported": "Cookie 状态: 未导入",
        "Cookie Status: {} ({} bytes)": "Cookie 状态: {} ({} 字节)",
        "Cookie Status: {}": "Cookie 状态: {}",
        "Confirm Reset": "确认重置",
        "Are you sure you want to reset all settings? This will delete config.json and requires restarting the application.": "确定要重置所有设置吗？这将删除 config.json 并需要重启应用。",
        "Reset Complete": "已重置",
        "Settings have been reset. Please restart the application to take effect.": "设置已重置，请重启应用以生效。",
        "Task failed": "任务失败",
        "Failed to create task worker": "无法创建任务 worker",
        "Full Workflow": "完整工作流",
        "Download Only": "仅下载",
        "Translate Only": "仅翻译",
        "Softsub Only": "仅软字幕",
        "Hardsub Only": "仅硬字幕",
        "Transcript Only": "仅转录",
        "Font Subset Only": "仅字体子集化",
        "Download": "下载",
        "Translate": "翻译",
        "Font Subset": "字体子集",
        "Softsub": "软字幕",
        "Transcript": "转录",
        "Segment": "分段",
        "Proofread": "校对",
        "Hardsub": "硬字幕",
        "Complete": "完成",
        "Task": "任务",
        "Completed": "完成",
        "Failed": "失败",
        "Queued": "排队中",
        "GUI": "GUI"
    }
    tree = ET.parse(file_path)
    root = tree.getroot()
    for message in root.iter('message'):
        source = message.find('source').text
        translation = message.find('translation')
        if translation is not None:
            if source in translations:
                translation.text = translations[source]
                if 'type' in translation.attrib:
                    del translation.attrib['type']
            else:
                print(f"Missing translation for: {source}")
    tree.write(file_path, encoding='utf-8', xml_declaration=True)

update_en('src/sublingo/i18n/sublingo_en.ts')
update_zh('src/sublingo/i18n/sublingo_zh_Hans.ts')
