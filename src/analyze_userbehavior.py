#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# ================== 配置 ==================
DATA_PATH = r'D:\数据分析项目\2\UserBehavior_5M_sampled.parquet'
OUTPUT_DIR = r'D:\数据分析项目\2\analysis_output'
os.makedirs(OUTPUT_DIR, exist_ok=True)
# ==========================================

print("加载清洗后的数据...")
df = pd.read_parquet(DATA_PATH)
print(f"数据行数: {len(df):,}")
print(f"时间范围: {df['datetime'].min()} ~ {df['datetime'].max()}")

df['behavior_type'] = df['behavior_type'].astype('int8')

# ------------------ 2. 漏斗断点分析（修正版） ------------------
print("\n===== 漏斗断点分析 =====")

# 获取各行为的用户集合
pv_users = set(df[df['behavior_type'] == 1]['user_id'])
fav_users = set(df[df['behavior_type'] == 2]['user_id'])
cart_users = set(df[df['behavior_type'] == 3]['user_id'])
buy_users = set(df[df['behavior_type'] == 4]['user_id'])

# 路径A：浏览→收藏→（收藏且购买）
fav_buy_users = fav_users & buy_users   # 既收藏又购买的用户
# 路径B：浏览→加购→（加购且购买）
cart_buy_users = cart_users & buy_users

n_pv = len(pv_users)
n_fav = len(fav_users)
n_cart = len(cart_users)
n_fav_buy = len(fav_buy_users)
n_cart_buy = len(cart_buy_users)

# 构建漏斗数据
funnel_a = pd.DataFrame({
    'stage': ['浏览', '收藏', '收藏→购买'],
    'users': [n_pv, n_fav, n_fav_buy]
})
funnel_b = pd.DataFrame({
    'stage': ['浏览', '加购', '加购→购买'],
    'users': [n_pv, n_cart, n_cart_buy]
})

# 计算转化率
def calc_conv(funnel_df):
    conv = []
    for i in range(len(funnel_df)-1):
        rate = funnel_df.iloc[i+1]['users'] / funnel_df.iloc[i]['users'] * 100
        conv.append(rate)
    return conv

conv_a = calc_conv(funnel_a)
conv_b = calc_conv(funnel_b)

print(f"路径A（浏览→收藏→收藏&购买）：")
print(f"  浏览→收藏转化率: {conv_a[0]:.2f}%")
print(f"  收藏→（收藏&购买）转化率: {conv_a[1]:.2f}%")
print(f"  整体转化率（浏览→购买）: {n_fav_buy/n_pv*100:.2f}%")

print(f"\n路径B（浏览→加购→加购&购买）：")
print(f"  浏览→加购转化率: {conv_b[0]:.2f}%")
print(f"  加购→（加购&购买）转化率: {conv_b[1]:.2f}%")
print(f"  整体转化率（浏览→购买）: {n_cart_buy/n_pv*100:.2f}%")

# 绘制并排漏斗图
fig_funnel = make_subplots(rows=1, cols=2, subplot_titles=('浏览→收藏→购买', '浏览→加购→购买'))
fig_funnel.add_trace(go.Funnel(y=funnel_a['stage'], x=funnel_a['users'], textinfo="value+percent initial", name='收藏路径'), row=1, col=1)
fig_funnel.add_trace(go.Funnel(y=funnel_b['stage'], x=funnel_b['users'], textinfo="value+percent initial", name='加购路径'), row=1, col=2)
fig_funnel.update_layout(title_text="用户行为漏斗对比", height=500)
fig_funnel.write_html(os.path.join(OUTPUT_DIR, 'funnel_analysis.html'))
print(f"漏斗图已保存至 {OUTPUT_DIR}/funnel_analysis.html")

# ------------------ 3. 时间维度分析 ------------------
print("\n===== 时间维度分析 =====")
daily_stats = df.groupby('date').agg(
    pv=('behavior_type', lambda x: (x == 1).sum()),
    uv=('user_id', 'nunique'),
    buy=('behavior_type', lambda x: (x == 4).sum()),
    buy_users=('user_id', lambda x: df.loc[x.index, 'behavior_type'].eq(4).any())
).reset_index()
daily_stats['buy_rate'] = daily_stats['buy_users'] / daily_stats['uv'] * 100

hourly_stats = df.groupby('hour').agg(
    pv=('behavior_type', lambda x: (x == 1).sum()),
    uv=('user_id', 'nunique'),
    buy=('behavior_type', lambda x: (x == 4).sum())
).reset_index()
hourly_stats['buy_rate'] = hourly_stats['buy'] / hourly_stats['uv'] * 100

# 绘图（省略，同之前）
fig_time = make_subplots(rows=2, cols=1, subplot_titles=('每日流量与购买', '每小时流量与购买'))
fig_time.add_trace(go.Scatter(x=daily_stats['date'], y=daily_stats['uv'], mode='lines+markers', name='UV'), row=1, col=1)
fig_time.add_trace(go.Scatter(x=daily_stats['date'], y=daily_stats['buy_users'], mode='lines+markers', name='购买用户'), row=1, col=1)
fig_time.add_trace(go.Scatter(x=daily_stats['date'], y=daily_stats['buy_rate'], mode='lines+markers', name='购买转化率(%)', yaxis='y2'), row=1, col=1)
fig_time.update_layout(yaxis2=dict(overlaying='y', side='right'))
fig_time.add_trace(go.Bar(x=hourly_stats['hour'], y=hourly_stats['pv'], name='PV'), row=2, col=1)
fig_time.add_trace(go.Scatter(x=hourly_stats['hour'], y=hourly_stats['uv'], mode='lines+markers', name='UV', yaxis='y4'), row=2, col=1)
fig_time.add_trace(go.Scatter(x=hourly_stats['hour'], y=hourly_stats['buy_rate'], mode='lines+markers', name='购买转化率(%)', yaxis='y5'), row=2, col=1)
fig_time.update_layout(yaxis4=dict(overlaying='y', side='right'), yaxis5=dict(overlaying='y', side='right'))
fig_time.write_html(os.path.join(OUTPUT_DIR, 'time_analysis.html'))
print(f"时间趋势图已保存至 {OUTPUT_DIR}/time_analysis.html")

# ------------------ 4. 商品与类目分析（修正版） ------------------
print("\n===== 商品与类目分析 =====")

# 类目统计
category_stats = df.groupby('category_id').agg(
    pv=('behavior_type', lambda x: (x == 1).sum()),
    buy=('behavior_type', lambda x: (x == 4).sum()),
    uv_browse=('user_id', lambda x: (df.loc[x.index, 'behavior_type'] == 1).any()),
    uv_buy=('user_id', lambda x: (df.loc[x.index, 'behavior_type'] == 4).any())
).reset_index()
# 将布尔列转换为整数（0/1），以便除法
category_stats['uv_browse'] = category_stats['uv_browse'].astype(int)
category_stats['uv_buy'] = category_stats['uv_buy'].astype(int)
category_stats['buy_rate'] = category_stats['uv_buy'] / category_stats['uv_browse'] * 100

top_cat_pv = category_stats.nlargest(10, 'pv')
top_cat_rate = category_stats[category_stats['pv'] >= 100].nlargest(10, 'buy_rate')

# 商品统计
item_stats = df.groupby('item_id').agg(
    pv=('behavior_type', lambda x: (x == 1).sum()),
    buy=('behavior_type', lambda x: (x == 4).sum()),
    uv_browse=('user_id', lambda x: (df.loc[x.index, 'behavior_type'] == 1).any()),
    uv_buy=('user_id', lambda x: (df.loc[x.index, 'behavior_type'] == 4).any())
).reset_index()
item_stats['uv_browse'] = item_stats['uv_browse'].astype(int)
item_stats['uv_buy'] = item_stats['uv_buy'].astype(int)
item_stats['buy_rate'] = item_stats['uv_buy'] / item_stats['uv_browse'] * 100

top_item_pv = item_stats.nlargest(10, 'pv')
top_item_rate = item_stats[item_stats['pv'] >= 50].nlargest(10, 'buy_rate')

# 可视化
fig_cat = px.bar(top_cat_pv, x='category_id', y='pv', title='PV TOP10 类目')
fig_cat.write_html(os.path.join(OUTPUT_DIR, 'category_top_pv.html'))
fig_cat_rate = px.bar(top_cat_rate, x='category_id', y='buy_rate', title='购买转化率 TOP10 类目（PV≥100）')
fig_cat_rate.write_html(os.path.join(OUTPUT_DIR, 'category_top_rate.html'))
print(f"类目分析图已保存至 {OUTPUT_DIR}/category_*.html")
print(f"商品TOP10（PV）：\n{top_item_pv[['item_id', 'pv', 'buy_rate']]}")
print(f"商品TOP10（转化率）：\n{top_item_rate[['item_id', 'pv', 'buy_rate']]}")

# ------------------ 5. 用户价值分层（简化RFM） ------------------
print("\n===== 用户价值分层 =====")
user_features = df.groupby('user_id').agg(
    total_pv=('behavior_type', lambda x: (x == 1).sum()),
    total_fav=('behavior_type', lambda x: (x == 2).sum()),
    total_cart=('behavior_type', lambda x: (x == 3).sum()),
    total_buy=('behavior_type', lambda x: (x == 4).sum())
).reset_index()

# 行为得分
user_features['score'] = (user_features['total_buy'] * 10 +
                          user_features['total_cart'] * 3 +
                          user_features['total_fav'] * 2 +
                          user_features['total_pv'] * 0.1)

# 业务分层
def business_segment(row):
    if row['total_buy'] > 0:
        if row['total_buy'] >= 3:
            return '高频购买者'
        else:
            return '普通购买者'
    elif row['total_cart'] > 0:
        return '加购未购买'
    elif row['total_fav'] > 0:
        return '收藏未购买'
    else:
        return '仅浏览用户'

user_features['business_segment'] = user_features.apply(business_segment, axis=1)
segment_counts = user_features['business_segment'].value_counts().reset_index()
segment_counts.columns = ['segment', 'count']

fig_seg = px.bar(segment_counts, x='segment', y='count', title='用户业务分层')
fig_seg.write_html(os.path.join(OUTPUT_DIR, 'user_segments.html'))
print("用户分层分布：")
print(segment_counts)

# 购买次数分布
buy_dist = user_features[user_features['total_buy'] > 0]['total_buy'].value_counts().sort_index()
fig_buy_dist = px.bar(x=buy_dist.index, y=buy_dist.values, title='购买次数分布（购买用户）', labels={'x':'购买次数', 'y':'用户数'})
fig_buy_dist.write_html(os.path.join(OUTPUT_DIR, 'buy_distribution.html'))

print("\n所有分析已完成！图表保存至:", OUTPUT_DIR)