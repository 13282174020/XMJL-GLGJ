# -*- coding: utf-8 -*-
"""
章节内容优化器

功能：
1. 章节类型识别（列表型、描述型、表格型）
2. Few-shot 示例管理
3. 内容去重检查

使用方式：
    optimizer = ContentOptimizer()
    type_info = optimizer.identify_section_type('项目概况')
    few_shot = optimizer.get_few_shot_prompt('项目概况')
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any


# =============================================================================
# Few-shot 示例定义
# =============================================================================

@dataclass
class SectionExample:
    """章节示例"""
    section_type: str           # 章节类型：列表型、描述型、表格型
    section_title: str          # 章节标题
    description: str            # 描述
    format_features: List[str]   # 格式特征
    example_content: str         # 示例内容
    tips: List[str]             # 撰写要点


FEW_SHOT_EXAMPLES: Dict[str, SectionExample] = {
    # ========== 列表型章节 ==========
    'list_policy': SectionExample(
        section_type='列表型',
        section_title='政策法规依据',
        description='列举相关的法律法规、政策文件',
        format_features=[
            '使用数字编号列表（1. 2. 3.）',
            '每条包含标准编号和名称',
            '编号格式如：GB/T、DB33/T、ISO 等',
            '每条后附简短说明'
        ],
        example_content="""1. 《中华人民共和国网络安全法》（2017 年 7 月 1 日施行）
   - 为网络安全提供了法律保障，要求关键信息基础设施运营者履行安全保护义务

2. 《中华人民共和国数据安全法》（2021 年 9 月 1 日施行）
   - 规范数据处理活动，保障数据安全，促进数据开发利用

3. GB/T 22239-2019《信息安全技术 网络安全等级保护基本要求》
   - 规定了网络安全等级保护的基本要求，适用于网络运营者""",
        tips=[
            '优先列出国家法律法规',
            '包含行业标准和技术规范',
            '每条注明发布时间和核心要点'
        ]
    ),

    'list_tech_standard': SectionExample(
        section_type='列表型',
        section_title='技术规范标准',
        description='列举项目需遵循的技术标准和规范',
        format_features=[
            '使用数字编号列表',
            '标准编号在前，名称在后',
            '包含国家标准、行业标准、地方标准'
        ],
        example_content="""1. GB 50348-2018《安全防范工程技术标准》
   - 规定了安全防范工程的设计、施工、检验和验收要求

2. GB/T 28181-2016《公共安全视频监控联网系统信息传输、交换、控制技术要求》
   - 规范了视频监控系统之间的互联互通

3. DB33/T 1234-2020《智慧社区建设规范》（浙江省地方标准）
   - 规定了智慧社区的总体要求、基础设施、应用系统等要求""",
        tips=[
            '按重要性排序，国家标准优先',
            '注明标准编号和完整名称',
            '简要说明标准适用范围'
        ]
    ),

    'list_problems': SectionExample(
        section_type='列表型',
        section_title='现状问题分析',
        description='列举当前存在的问题和痛点',
        format_features=[
            '使用数字编号列表',
            '每条先概括问题，再具体描述',
            '可包含数据支撑'
        ],
        example_content="""1. 监控设备老化严重，存在安全隐患
   - 现有监控摄像头多为 5 年前的模拟设备，清晰度低、故障率高
   - 覆盖率不足，小区出入口、地下车库等关键区域存在盲区
   - 设备完好率仅约 60%，无法满足日常安防需求

2. 电瓶车管理困难，盗窃事件频发
   - 缺乏统一的电瓶车登记管理系统
   - 充电桩数量不足，私拉电线现象普遍
   - 年内发生电瓶车盗窃案件 15 起，居民反映强烈

3. 流动人口管理手段落后
   - 依赖人工登记，信息更新不及时
   - 出租房屋管理不到位，人员流动性大
   - 当前登记流动人口约 3500 人，实际可能超过 5000 人""",
        tips=[
            '问题描述要具体，有数据支撑',
            '按严重程度排序',
            '可引用居民反馈或案件数据'
        ]
    ),

    'list_requirements': SectionExample(
        section_type='列表型',
        section_title='项目建设需求',
        description='列举项目的具体建设需求',
        format_features=[
            '使用数字编号列表',
            '每条需求明确具体',
            '可分类组织（功能需求、性能需求等）'
        ],
        example_content="""1. 视频监控全覆盖需求
   - 在小区主次出入口、单元门口、电梯轿厢等关键位置部署高清摄像头
   - 支持人脸识别、车辆识别等智能分析功能
   - 视频存储时间不少于 30 天

2. 电瓶车安全管理需求
   - 建设电瓶车出入识别系统，实现自动登记和轨迹追踪
   - 部署智能充电桩，支持扫码充电、过载保护
   - 建立电瓶车数据库，实现防盗预警

3. 流动人口管理需求
   - 建设流动人口信息采集平台，支持多渠道申报
   - 实现与公安系统的数据对接，实时比对预警
   - 提供出租房屋管理功能，实现房主、租客双向管理""",
        tips=[
            '需求要具体可量化',
            '区分功能需求和性能需求',
            '与痛点问题相呼应'
        ]
    ),

    # ========== 描述型章节 ==========
    'desc_project_overview': SectionExample(
        section_type='描述型',
        section_title='项目概况',
        description='对项目进行整体概述',
        format_features=[
            '开篇点明项目名称和建设单位',
            '简述建设地点、规模、投资等关键信息',
            '语言简洁，信息密集'
        ],
        example_content="""项目名称：智慧社区管理平台建设项目

项目建设单位：XX 科技有限公司

建设地点：XX 市 XX 区 XX 街道 XX 社区

建设规模：覆盖社区总人口约 1.1 万人，总户数 3000 多户，部署各类智能设备约 500 台（套）

建设工期：12 个月（2026 年 1 月至 2026 年 12 月）

总投资：500 万元，资金来源为财政拨款

编制单位：XX 工程咨询有限公司""",
        tips=[
            '信息准确，与需求文档保持一致',
            '使用简洁的陈述句',
            '关键数据突出显示'
        ]
    ),

    'desc_project_background': SectionExample(
        section_type='描述型',
        section_title='项目背景',
        description='阐述项目提出的背景和必要性',
        format_features=[
            '从宏观政策背景切入',
            '结合本地实际情况',
            '说明项目提出的原因和紧迫性'
        ],
        example_content="""随着城镇化进程加快和居民生活品质提升，传统社区管理模式已难以满足现代社会治理需求。国家《"十四五"城乡社区服务体系建设规划》明确提出，要推进智慧社区建设，依托数字技术提升社区服务效能。

XX 社区作为典型的混合型社区，既有老旧小区，又有新建商品房小区，人口结构复杂，管理难度大。当前社区安防设施老化、管理手段落后等问题日益突出，居民对安全、便捷、智能的社区环境需求迫切。

在此背景下，XX 科技有限公司提出建设智慧社区管理平台，旨在通过引入先进的信息技术，构建覆盖社区全域的智能化管理体系，提升社区治理现代化水平，增强居民获得感、幸福感、安全感。""",
        tips=[
            '从宏观到微观，层次清晰',
            '引用政策文件增强说服力',
            '突出项目的必要性和紧迫性'
        ]
    ),

    'desc_construction_objectives': SectionExample(
        section_type='描述型',
        section_title='项目建设目标',
        description='阐述项目预期达到的目标',
        format_features=[
            '分总体目标和具体目标两个层次',
            '目标要可量化、可考核',
            '包含社会效益和经济效益'
        ],
        example_content="""【总体目标】

通过 12 个月的建设，建成覆盖 XX 社区全域的智慧社区管理平台，实现社区安防智能化、管理服务精细化、居民生活便捷化，打造全市智慧社区建设标杆。

【具体目标】

1. 安防能力提升：视频监控覆盖率达到 100%，重点区域智能分析覆盖率超过 80%，可防性案件发案率下降 50% 以上

2. 管理效率提升：流动人口信息登记率提升至 95% 以上，出租房屋备案率达到 90%，事件处置响应时间缩短至 30 分钟内

3. 服务水平提升：居民办事"最多跑一次"事项占比超过 80%，社区服务满意度提升至 90% 以上

4. 示范效应：形成可复制、可推广的智慧社区建设经验，年内接待参观交流不少于 10 批次""",
        tips=[
            '目标要 SMART（具体、可衡量、可实现、相关、有时限）',
            '定量目标与定性目标结合',
            '体现项目的创新性和示范性'
        ]
    ),

    'desc_technical_solution': SectionExample(
        section_type='描述型',
        section_title='技术方案概述',
        description='对项目技术方案进行整体描述',
        format_features=[
            '说明技术路线和总体架构',
            '介绍核心技术选型',
            '阐述技术优势'
        ],
        example_content="""本项目采用"云 - 边 - 端"协同的技术架构，构建智慧社区管理平台。

【总体架构】

平台采用"1+3+N"架构：
- "1"个数据中心：部署于政务云，实现数据集中存储和管理
- "3"个中台：业务中台、数据中台、AI 中台，提供共性能力支撑
- "N"个应用：面向不同用户群体提供 N 个业务应用

【技术路线】

1. 前端感知层：采用高清网络摄像机、物联网传感器等设备，实现社区全域数据采集
2. 网络传输层：依托电子政务外网和互联网，实现数据安全可靠传输
3. 平台层：基于微服务架构，采用容器化部署，支持弹性扩展
4. 应用层：采用 B/S 架构，支持 PC 端和移动端访问

【核心技术】

- 人工智能：采用深度学习算法，实现人脸识别、车辆识别、行为分析等功能
- 大数据：采用分布式存储和计算框架，支持海量数据实时处理
- 物联网：采用 NB-IoT、LoRa 等技术，实现设备互联互通""",
        tips=[
            '架构描述要层次清晰',
            '技术选型要说明理由',
            '突出技术的先进性和成熟度'
        ]
    ),

    # ========== 表格型章节 ==========
    'table_investment': SectionExample(
        section_type='表格型',
        section_title='投资估算',
        description='列出项目投资估算',
        format_features=[
            '使用表格形式呈现',
            '分类列明各项投资',
            '包含金额和占比'
        ],
        example_content="""| 序号 | 项目名称 | 金额（万元） | 占比（%） | 备注 |
|------|----------|--------------|-----------|------|
| 1 | 硬件设备购置费 | 280 | 56.0 | 含监控设备、服务器、网络设备等 |
| 2 | 软件开发费 | 120 | 24.0 | 含平台开发、系统集成等 |
| 3 | 安装工程费 | 50 | 10.0 | 含管线敷设、设备安装等 |
| 4 | 工程建设其他费 | 30 | 6.0 | 含设计费、监理费、检测费等 |
| 5 | 预备费 | 20 | 4.0 | 基本预备费 |
| 合计 | - | 500 | 100.0 | - |""",
        tips=[
            '分类要清晰合理',
            '金额计算要准确',
            '备注说明要简洁'
        ]
    ),

    'table_schedule': SectionExample(
        section_type='表格型',
        section_title='建设进度计划',
        description='列出项目建设进度安排',
        format_features=[
            '使用表格形式呈现',
            '按阶段划分任务',
            '明确时间节点和成果'
        ],
        example_content="""| 阶段 | 时间安排 | 主要任务 | 预期成果 |
|------|----------|----------|----------|
| 第一阶段 | 第 1-2 月 | 需求调研、方案设计 | 需求规格说明书、总体设计方案 |
| 第二阶段 | 第 3-5 月 | 平台开发、设备采购 | 平台原型系统、设备采购合同 |
| 第三阶段 | 第 6-9 月 | 设备安装、系统部署 | 设备安装完成、系统上线运行 |
| 第四阶段 | 第 10-11 月 | 系统测试、试运行 | 测试报告、试运行报告 |
| 第五阶段 | 第 12 月 | 项目验收、培训交付 | 验收报告、用户培训完成 |""",
        tips=[
            '阶段划分要合理',
            '任务安排要具体',
            '成果要可交付可验收'
        ]
    ),
}


# =============================================================================
# 章节类型映射
# =============================================================================

# 章节标题关键词 -> 示例键 的映射
# 注意：顺序很重要！更具体的规则应该放在前面
CHAPTER_TYPE_MAP = {
    # 描述型 - 技术方案（需要优先匹配）
    'desc_technical_solution': ['方案', '架构', '设计'],

    # 列表型
    'list_policy': ['政策', '法规', '依据', '规范', '标准'],
    'list_tech_standard': ['技术', '标准', '规范'],
    'list_problems': ['问题', '痛点', '现状', '困难', '挑战'],
    'list_requirements': ['需求', '要求'],

    # 描述型
    'desc_project_overview': ['概况', '概述', '基本信息'],
    'desc_project_background': ['背景', '必要性', '意义'],
    'desc_construction_objectives': ['目标', '目的', '预期'],

    # 表格型
    'table_investment': ['投资', '估算', '预算', '资金'],
    'table_schedule': ['进度', '计划', '工期', '安排'],
}


# =============================================================================
# 内容优化器
# =============================================================================

class ContentOptimizer:
    """章节内容优化器

    识别章节类型，提供 Few-shot 示例，优化生成内容。

    使用方式：
        optimizer = ContentOptimizer()

        # 识别章节类型
        type_info = optimizer.identify_section_type('项目概况')
        print(type_info['type'])  # 'desc'

        # 获取示例
        few_shot = optimizer.get_few_shot_prompt('项目概况')
        print(few_shot)

        # 添加已生成内容
        optimizer.add_generated_content('项目概况', '生成的内容...')

        # 检查重复
        result = optimizer.check_duplicate('新内容...')
        print(result['is_duplicate'])
    """

    def __init__(self):
        """初始化优化器"""
        self._generated_content_history: List[tuple] = []

    # ========== Few-shot 功能 ==========

    def get_example_for_section(self, section_title: str) -> Optional[SectionExample]:
        """获取章节对应的示例

        Args:
            section_title: 章节标题

        Returns:
            SectionExample 或 None
        """
        type_key = self._match_type_key(section_title)
        if type_key:
            return FEW_SHOT_EXAMPLES.get(type_key)
        return None

    def get_few_shot_prompt(self, section_title: str) -> str:
        """构建 Few-shot 提示

        Args:
            section_title: 章节标题

        Returns:
            Few-shot 提示文本
        """
        example = self.get_example_for_section(section_title)

        if not example:
            return ""

        prompt_parts = [
            f"\n【参考示例】",
            f"以下是「{example.section_title}」的示例，请参考其格式和风格：",
            "",
            example.example_content,
            ""
        ]

        if example.tips:
            prompt_parts.append("【示例要点】")
            for tip in example.tips:
                prompt_parts.append(f"- {tip}")
            prompt_parts.append("")

        return "\n".join(prompt_parts)

    def get_all_examples(self) -> Dict[str, SectionExample]:
        """获取所有示例"""
        return FEW_SHOT_EXAMPLES.copy()

    def _match_type_key(self, section_title: str) -> Optional[str]:
        """匹配章节类型键"""
        for type_key, keywords in CHAPTER_TYPE_MAP.items():
            if any(kw in section_title for kw in keywords):
                return type_key
        return None

    # ========== 章节类型识别 ==========

    def identify_section_type(self, section_title: str) -> Dict[str, Any]:
        """识别章节类型

        Args:
            section_title: 章节标题

        Returns:
            {
                'section_title': str,       # 原始标题
                'type': str,                # 类型：list/desc/table/unknown
                'subtype': str,             # 子类型键
                'format_strategy': str,     # 格式策略
                'prompt_guidance': str,     # Prompt 指导
                'matched_keywords': list,   # 匹配的关键词
            }
        """
        result = {
            'section_title': section_title,
            'type': 'unknown',
            'subtype': '',
            'format_strategy': '',
            'prompt_guidance': '',
            'matched_keywords': []
        }

        # 遍历映射表
        for type_key, keywords in CHAPTER_TYPE_MAP.items():
            matched = [kw for kw in keywords if kw in section_title]

            if matched:
                result['matched_keywords'] = matched

                if type_key.startswith('list_'):
                    result['type'] = 'list'
                    result['subtype'] = type_key
                    result['format_strategy'] = '使用数字编号列表（1. 2. 3.），每条内容清晰分明'
                elif type_key.startswith('desc_'):
                    result['type'] = 'desc'
                    result['subtype'] = type_key
                    result['format_strategy'] = '使用连贯的段落描述，语言简洁专业'
                elif type_key.startswith('table_'):
                    result['type'] = 'table'
                    result['subtype'] = type_key
                    result['format_strategy'] = '使用表格形式呈现，数据清晰易读'

                # 获取指导
                example = FEW_SHOT_EXAMPLES.get(type_key)
                if example:
                    result['prompt_guidance'] = self._build_type_guidance(example)

                break

        # 默认类型
        if result['type'] == 'unknown':
            result['type'] = 'desc'
            result['format_strategy'] = '使用连贯的段落描述，语言简洁专业'

        return result

    def _build_type_guidance(self, example: SectionExample) -> str:
        """构建类型指导文本"""
        guidance_parts = [
            f"\n【格式指导】",
            f"本章属于「{example.section_type}」，参考示例：{example.section_title}",
            ""
        ]

        if example.format_features:
            guidance_parts.append("格式特征：")
            for feature in example.format_features:
                guidance_parts.append(f"- {feature}")
            guidance_parts.append("")

        return "\n".join(guidance_parts)

    def get_type_guidance(self, section_title: str) -> str:
        """获取章节类型指导"""
        type_info = self.identify_section_type(section_title)

        if type_info['type'] == 'unknown':
            return ""

        guidance = f"\n【章节类型识别】{type_info['type']}型"

        if type_info['format_strategy']:
            guidance += f"\n格式策略：{type_info['format_strategy']}"

        if type_info['prompt_guidance']:
            guidance += type_info['prompt_guidance']

        return guidance

    # ========== 内容去重功能 ==========

    def add_generated_content(self, section_title: str, content: str) -> None:
        """添加已生成的内容到历史"""
        if content:
            self._generated_content_history.append((section_title, content))

    def check_duplicate(self, new_content: str, threshold: float = 0.6) -> Dict[str, Any]:
        """检查新内容与历史内容的重复度

        Args:
            new_content: 新内容
            threshold: 重复度阈值（0-1）

        Returns:
            {
                'is_duplicate': bool,
                'duplicate_rate': float,
                'similar_section': str or None,
            }
        """
        import difflib

        result = {
            'is_duplicate': False,
            'duplicate_rate': 0.0,
            'similar_section': None,
        }

        if not new_content:
            return result

        # 比较所有历史内容
        for section_title, old_content in self._generated_content_history:
            if not old_content:
                continue

            # 计算相似度
            seq = difflib.SequenceMatcher(None, new_content, old_content)
            similarity = seq.ratio()

            if similarity > result['duplicate_rate']:
                result['duplicate_rate'] = similarity
                result['similar_section'] = section_title

        result['is_duplicate'] = result['duplicate_rate'] >= threshold

        return result

    def reset(self) -> None:
        """重置历史记录"""
        self._generated_content_history.clear()
