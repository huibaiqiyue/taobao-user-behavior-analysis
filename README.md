# 📊 淘宝用户行为数据分析与漏斗转化研究

## 📝 项目简介
本项目基于阿里云天池提供的“淘宝用户行为数据集”（User Behavior Data from Taobao for Recommendation），对 **500万+** 条用户行为数据进行清洗、探索性分析（EDA）与漏斗模型构建。
旨在挖掘电商转化链路中的核心流失环节，分析大促预热期（双12）的用户行为规律，并为运营团队提供“促转化”与“防流失”的业务策略。

> 📖 **详细数据分析报告与业务洞察**：[[点击访问我的 CSDN 博客](https://blog.csdn.net/m0_73568782/article/details/162642791?fromshare=blogdetail&sharetype=blogdetail&sharerId=162642791&sharerefer=PC&sharesource=m0_73568782&sharefrom=from_link)]

## 📂 目录结构
为了保证项目的可读性与可复现性，本项目采用以下目录结构：

```text
.
├── src/                # 核心代码目录
│   ├── clean_userbehavior.py      # 数据清洗脚本 (处理时间戳异常、缺失值等)
│   └── analyze_userbehavior.py    # 漏斗分析与可视化脚本
├── assets/              # 可视化图表输出目录
│   ├── funnel_analysis.html     # 漏斗断点分析图
│   ├── time_analysis.html       # 时间维度趋势图
│   ├── category_top_pv.html     # 类目PV分析图
│   └── ...                      # 其他分析图表
├── requirements.txt     # 项目依赖环境
└── README.md            # 项目说明文档
🛠️ 环境依赖
本项目基于 Python 3.13 开发，运行前请确保安装以下依赖库：
pip install -r requirements.txt
🚀 如何运行
1.克隆本仓库到本地
2.将从tianchi.aliyun.com/dataset/649下载的原始数据集 UserBehavior.csv 放入 data/ 目录下。
按顺序执行 src/ 目录下的 Python 脚本：
运行 clean_userbehavior.py 进行数据预处理。
运行 analyze_userbehavior.py 生成漏斗及多维度的分析图表。
生成的交互式图表将自动保存在 assets/ 目录中。
💡 核心分析结论
漏斗断点：路径B（浏览→加购→购买）整体转化率高达 53.51%，远超路径A（收藏路径的28.13%），加购是核心转化引擎。
时间规律：双12预热期（12月1日-3日）流量呈指数级增长，且晚间 20:00-22:00 为全天转化双高峰。
商品策略：存在“高PV低转化”的引流款与“低PV高转化”的利润款，建议通过关联推荐提升客单价。
用户分层：精准识别出 10,411 名“加购未购买”的高意向用户，建议通过定向发券实现临门一脚的转化。
🤝 交流与反馈
如果你觉得这个项目对你有帮助，欢迎点个 Star ⭐ 支持一下！
如果有任何疑问或更好的优化建议，欢迎提 Issue 或与我交流。