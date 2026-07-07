#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import time
import os

# ========================= 配置参数 ==========================
FILE_PATH = r'D:\\数据分析项目\\2\\UserBehavior.csv'
SAVE_PATH = r'D:\\数据分析项目\\2\\UserBehavior_5M_sampled.parquet'
TARGET_ROWS = 5_000_000
CHUNK_SIZE = 500_000
BEHAVIOR_MAP = {'pv': 1, 'fav': 2, 'cart': 3, 'buy': 4}
# 合法时间范围（天池数据集 2017-11-25 00:00:00 至 2017-12-03 23:59:59，UTC+8）
TIMESTAMP_MIN = 1511510400
TIMESTAMP_MAX = 1512345599
# 业务规则阈值：至少需要 PV 次数 > 0
MIN_PV = 1
# ============================================================

COLUMN_NAMES = ['user_id', 'item_id', 'category_id', 'behavior_type', 'timestamp']


def build_user_stats(file_path, chunk_size):
    """
    第一次扫描：过滤时间、映射行为、按用户汇总。
    统计字段：total_pv, has_fav, has_cart, has_buy, total_rows
    """
    print("开始第一次扫描：构建用户行为统计（含时间/行为过滤）...")
    start = time.time()
    user_stats_list = []

    for i, chunk in enumerate(pd.read_csv(
        FILE_PATH,
        names=COLUMN_NAMES,
        header=None,
        chunksize=chunk_size,
        low_memory=False,
    )):
        print(f"处理第 {i+1} 块，原始行数: {len(chunk):,}")

        # ---------- 业务规则1：时间范围过滤 ----------
        chunk = chunk[(chunk['timestamp'] >= TIMESTAMP_MIN) & (chunk['timestamp'] <= TIMESTAMP_MAX)]
        if len(chunk) == 0:
            continue

        # ---------- 业务规则2：行为枚举映射 ----------
        chunk['behavior_type'] = chunk['behavior_type'].map(BEHAVIOR_MAP)
        chunk = chunk.dropna(subset=['behavior_type'])
        chunk['behavior_type'] = chunk['behavior_type'].astype('int8')

        # 按用户聚合统计
        grouped = chunk.groupby('user_id').agg(
            total_pv=('behavior_type', lambda x: (x == 1).sum()),
            has_fav=('behavior_type', lambda x: (x == 2).any()),
            has_cart=('behavior_type', lambda x: (x == 3).any()),
            has_buy=('behavior_type', lambda x: (x == 4).any()),
            total_rows=('behavior_type', 'count')
        ).reset_index()

        user_stats_list.append(grouped)

    if not user_stats_list:
        raise ValueError("未读取到任何有效数据（可能时间过滤太严或行为映射失败）")

    user_stats = pd.concat(user_stats_list, ignore_index=True)
    # 再次汇总（因为同一用户可能出现在多个块中）
    user_stats = user_stats.groupby('user_id').agg(
        total_pv=('total_pv', 'sum'),
        has_fav=('has_fav', 'any'),
        has_cart=('has_cart', 'any'),
        has_buy=('has_buy', 'any'),
        total_rows=('total_rows', 'sum')
    ).reset_index()

    elapsed = time.time() - start
    print(f"用户统计完成，共 {len(user_stats):,} 个用户，耗时 {elapsed:.2f} 秒")
    return user_stats


def select_active_users(user_stats, target_rows):
    """
    剔除以下用户：
      - 僵尸用户：PV <= 3 且 无其他行为（原有逻辑）
      - 业务规则3：有购买但无任何PV（即 total_pv == 0 且 has_buy == True）
      - 扩展：完全无PV的用户（total_pv == 0）
    然后随机抽样用户，使累计行数接近目标。
    """
    print("\n应用业务规则，剔除无效用户...")
    original_count = len(user_stats)

    # 规则3：剔除无PV的购买用户 及 完全无PV的用户
    invalid_no_pv = (user_stats['total_pv'] == 0)
    # 且剔除僵尸（原有）
    is_zombie = (user_stats['total_pv'] <= 3) & \
                (~user_stats['has_fav']) & \
                (~user_stats['has_cart']) & \
                (~user_stats['has_buy'])

    # 合并无效条件
    invalid = invalid_no_pv | is_zombie
    active_users = user_stats[~invalid].copy()

    print(f"剔除无效用户 {invalid.sum():,} 个（无PV用户、僵尸用户）")
    print(f"活跃用户数: {len(active_users):,}")

    # 随机打乱（抽样用户）
    active_users = active_users.sample(frac=1, random_state=42).reset_index(drop=True)

    selected_users = []
    total_rows = 0
    for idx, row in active_users.iterrows():
        selected_users.append(row['user_id'])
        total_rows += row['total_rows']
        if total_rows >= target_rows:
            break

    print(f"选中 {len(selected_users):,} 个用户，总行数约 {total_rows:,}（目标 {target_rows:,}）")
    return selected_users


def extract_sampled_data(file_path, selected_users, chunk_size):
    """
    第二次扫描：提取选中用户的所有合法记录（再次应用过滤），并添加时间特征，优化类型。
    """
    print("\n第二次扫描：提取采样用户数据...")
    start = time.time()
    selected_set = set(selected_users)
    chunks = []
    total_rows = 0

    for i, chunk in enumerate(pd.read_csv(
        FILE_PATH,
        names=COLUMN_NAMES,
        header=None,
        chunksize=chunk_size,
        low_memory=False,
    )):
        # 应用时间过滤
        chunk = chunk[(chunk['timestamp'] >= TIMESTAMP_MIN) & (chunk['timestamp'] <= TIMESTAMP_MAX)]
        if len(chunk) == 0:
            continue

        chunk = chunk[chunk['user_id'].isin(selected_set)]
        if len(chunk) == 0:
            continue

        # 行为映射
        chunk['behavior_type'] = chunk['behavior_type'].map(BEHAVIOR_MAP)
        chunk = chunk.dropna(subset=['behavior_type'])
        chunk['behavior_type'] = chunk['behavior_type'].astype('int8')

        # 时间特征
        chunk['datetime'] = pd.to_datetime(chunk['timestamp'], unit='s')
        chunk['date'] = chunk['datetime'].dt.date
        chunk['hour'] = chunk['datetime'].dt.hour
        chunk['weekday'] = chunk['datetime'].dt.weekday

        # 类型优化（脱敏ID保留为 int32，不进行任何数学操作）
        chunk['user_id'] = chunk['user_id'].astype('int32')
        chunk['item_id'] = chunk['item_id'].astype('int32')
        chunk['category_id'] = chunk['category_id'].astype('int32')
        chunk['timestamp'] = chunk['timestamp'].astype('int64')

        chunks.append(chunk)
        total_rows += len(chunk)
        print(f"已提取 {total_rows:,} 行...")

    if not chunks:
        raise ValueError("未提取到任何数据，请检查所选用户或过滤条件")

    df = pd.concat(chunks, ignore_index=True)
    # 去重（可选）
    before = len(df)
    df.drop_duplicates(inplace=True)
    if len(df) < before:
        print(f"去重删除 {before - len(df):,} 行")

    elapsed = time.time() - start
    print(f"提取完成，最终行数: {len(df):,}，耗时 {elapsed:.2f} 秒")
    return df


def main():
    if not os.path.exists(FILE_PATH):
        print(f"错误：文件 {FILE_PATH} 不存在")
        return

    # 第一次扫描：统计
    user_stats = build_user_stats(FILE_PATH, CHUNK_SIZE)

    # 选择用户（含业务规则）
    selected_users = select_active_users(user_stats, TARGET_ROWS)

    # 第二次扫描：提取
    df_sampled = extract_sampled_data(FILE_PATH, selected_users, CHUNK_SIZE)

    # 概览
    print("\n采样数据概览：")
    print(f"行数: {len(df_sampled):,}")
    print(f"列数: {len(df_sampled.columns)}")
    print("行为类型分布：")
    print(df_sampled['behavior_type'].value_counts().sort_index())
    print(f"时间范围: {df_sampled['datetime'].min()} ～ {df_sampled['datetime'].max()}")

    # 保存
    print(f"\n开始保存数据到: {SAVE_PATH}")
    start = time.time()
    df_sampled.to_parquet(SAVE_PATH, index=False, compression='snappy')
    print(f"保存完成，耗时 {time.time()-start:.2f} 秒")
    print("\n全部完成！")


if __name__ == "__main__":
    main()