#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ShantenAI测试脚本

测试向听数AI的各项功能：
1. 向听数计算准确性
2. 牌效率分析
3. 与其他AI的对战表现
"""

import sys
import os
import time
import logging
from typing import List, Dict

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 禁用日志输出
logging.disable(logging.CRITICAL)

from game.tile import Tile, TileType, FengType, JianType
from game.player import Player, PlayerType
from game.game_engine import GameEngine, GameMode
from ai.shanten_ai import ShantenAI, ShantenCalculator, UkeireCalculator, TileEfficiencyAnalyzer
from ai.simple_ai import SimpleAI
from ai.aggressive_ai import AggressiveAI
from ai.mcts_ai import MctsAI

def create_test_tiles(tile_strings: List[str]) -> List[Tile]:
    """从字符串列表创建测试牌"""
    tiles = []
    for tile_str in tile_strings:
        if len(tile_str) == 2:
            value_str, type_str = tile_str[0], tile_str[1]
            if type_str == "万":
                tiles.append(Tile(TileType.WAN, int(value_str)))
            elif type_str == "筒":
                tiles.append(Tile(TileType.TONG, int(value_str)))
            elif type_str == "条":
                tiles.append(Tile(TileType.TIAO, int(value_str)))
        elif tile_str in ["东", "南", "西", "北"]:
            feng_map = {"东": FengType.DONG, "南": FengType.NAN, 
                       "西": FengType.XI, "北": FengType.BEI}
            tiles.append(Tile(TileType.FENG, feng_type=feng_map[tile_str]))
        elif tile_str in ["中", "发", "白"]:
            jian_map = {"中": JianType.ZHONG, "发": JianType.FA, "白": JianType.BAI}
            tiles.append(Tile(TileType.JIAN, jian_type=jian_map[tile_str]))
    return tiles

def test_shanten_calculation():
    """测试向听数计算"""
    print("🎯 [全面] 向听数计算测试 (门清手牌)")
    print("=" * 70)
    
    test_cases = [
        # 0向听 (听牌)
        #   标准型 (4面子+1雀头)
        (["1万","2万","3万","4万","5万","6万","7万","8万","9万","1筒","1筒","2筒","3筒"], 0, "0向听-标准型-两面听(1-4筒)", "general"),
        (["1万","1万","1万","2万","3万","4万","5万","6万","7万","8万","9万","1筒","1筒"], 0, "0向听-标准型-双碰听(1万,1筒)", "general"),
        (["1万","2万","3万","4万","5万","6万","7万","7万","7万","1筒","2筒","3筒","东"], 0, "0向听-标准型-单骑听(东)", "general"),
        (["1万","2万","3万","4万","5万","6万","8万", "9万","7条","8条","9条","中","中"], 0, "0向听-标准型-边张听(7万)", "general"),
        (["1万","2万","3万","4万","6万","1筒","2筒","3筒","发","发","发","白","白"], 0, "0向听-标准型-嵌张听(5万)", "general"),
        #   七对子
        (["1万","1万","2万","2万","3万","3万","4万","4万","5万","5万","6万","6万","7万"], 0, "0向听-七对子-听7万", "pairs"),
        (["东","东","南","南","西","西","北","北","中","中","发","发","白"], 0, "0向听-七对子-听白", "pairs"),
        #   国士无双 (当前算法不支持, 测试其行为)
        (["1万","9万","1筒","9筒","1条","9条","东","南","西","北","中","发","白"], 0, "0向听-国士无双13面(当前算法未支持)", "kokushi"),
        (["1万","1万","9万","1筒","9筒","1条","9条","东","南","西","北","中","发"], 0, "0向听-国士无双单骑(当前算法未支持)", "kokushi"),

        # 1向听 (一向听)
        #   标准型
        (["1万","2万","3万","4万","5万","6万","7万","8万","1筒","1筒","2筒","3筒","5筒"], 1, "1向听-标准型-差一张成搭", "general"),
        (["1万","1万","2万","3万","4万","5万","1筒","2筒","3筒","7条","8条","9条","东"], 1, "1向听-标准型-缺雀头", "general"),
        #   七对子
        (["1万","1万","2万","2万","3万","3万","4万","4万","5万","5万","6万","7万","8万"], 1, "1向听-七对子-5对子", "pairs"),
        #   国士无双
        (["1万","1万","9万","1筒","9筒","1条","9条","东","南","西","北","中","中"], 1, "1向听-国士无双(当前算法未支持)", "kokushi"),

        # 2向听 (二向听)
        #   标准型
        (["1万","3万","5万","7万","9万","1筒","2筒","3筒","5条","6条","7条","东","西"], 2, "2向听-标准型-2面子+2搭子", "general"),
        (["1万","1万","2万","3万","5万","6万","8万","9万","1筒","3筒","5筒","9筒","9筒"], 2, "2向听-标准型-搭子多", "general"),
        #   七对子
        (["1万","1万","2万","2万","3万","3万","4万","4万","5万","6万","7万","8万","9万"], 2, "2向听-七对子-4对子", "pairs"),

        # 3向听 (三向听)
        (["1万","3万","5万","7万","9万","2筒","4筒","6筒","8筒","1条","3条","5条","5条"], 3, "3向听-标准型-孤张多", "general"),
        (["1万","1万","2万","2万","3万","3万","4万","5万","6万","7万","8万","9万","东"], 3, "3向听-七对子-3对子", "pairs"),

        # 4向听 (四向听)
        (["1万","2万","7万","8万","1筒","2筒","7筒","1条","2条","7条","南","西","北"], 4, "4向听-标准型-较差", "general"),
        (["1万","1万","2万","2万","3万","4万","5万","6万","7万","8万","9万","东","南"], 4, "4向听-七对子-2对子", "pairs"),

        # 5向听 (五向听)
        (["1万","2万","7万","1筒","2筒","7筒","1条","2条","7条","东","南","西","北"], 5, "5向听-标准型-差", "general"),

        # 8向听 (八向听)
        (["1万","4万","7万","1筒","4筒","7筒","1条","4条","7条","东","南","西","北"], 8, "8向听-标准型-很差", "general"),
    ]
    
    for tiles_str, expected_shanten, description, shentan_type in test_cases:
        tiles = create_test_tiles(tiles_str)
        
        # 验证手牌数量
        if len(tiles) != 13:
            print(f"❌ {description}")
            print(f"   手牌数量错误: {len(tiles)}张，应该是13张")
            print(f"   手牌: {' '.join(str(t) for t in tiles)}")
            continue
            
        calculated_shanten = ShantenCalculator.calculate_shanten(tiles, shentan_type=shentan_type)
        
        status = "✅" if calculated_shanten == expected_shanten else "❌"
        print(f"{status} {description}")
        print(f"   手牌: {' '.join(str(t) for t in tiles)}")
        print(f"   期望向听数: {expected_shanten}, 计算结果: {calculated_shanten}")
        
        if calculated_shanten != expected_shanten:
            print(f"   ⚠️ 计算错误！期望{expected_shanten}向听，实际{calculated_shanten}向听")
        print()

def test_ukeire_calculation():
    """测试有效进张计算"""
    print("🎯 测试有效进张计算功能")
    print("=" * 50)
    
    # 测试一向听手牌的有效进张
    tiles = create_test_tiles(["1万", "2万", "3万", "4万", "5万", "6万", "7万", "8万", "9万", "1筒", "1筒", "4筒", "5筒"])
    
    ukeire = UkeireCalculator.calculate_ukeire(tiles)
    total_ukeire = sum(ukeire.values())
    
    print(f"测试手牌: {' '.join(str(t) for t in tiles)}")
    print(f"向听数: {ShantenCalculator.calculate_shanten(tiles)}")
    print(f"总有效进张: {total_ukeire}张")
    
    if ukeire:
        print("有效进张详情:")
        for (tile_type, value), count in ukeire.items():
            if tile_type in [TileType.WAN, TileType.TONG, TileType.TIAO]:
                tile_name = f"{value}{tile_type.value}"
            else:
                tile_name = f"{tile_type.value}"
            print(f"   {tile_name}: {count}张")
    else:
        print("   无有效进张")
    print()

def test_tile_efficiency_analysis():
    """测试牌效率分析"""
    print("🎯 测试牌效率分析功能")
    print("=" * 50)
    
    # 创建测试玩家
    player = Player("测试玩家", PlayerType.HUMAN, 0)
    # player.missing_suit = "万"  # 设置缺万
    player.missing_suit = None
    
    # 设置测试手牌 （打出前
    # 测试样例出自 https://www.bilibili.com/opus/282352017624252578
    # 测试时应观测打各牌进张数是否与链接中的一致
    hand_tiles = create_test_tiles([
        "2万", "2万", "4万", "2筒", "2筒", "4筒", "6筒", "7筒", "8筒", "3条", "4条", "6条", "6条", "8条"
    ])
    # hand_tiles = create_test_tiles([
    #     "1万", "9万", "1筒", "3筒", "4筒", "5筒", "7筒", "9筒", "3条", "4条", "6条", "6条", "7条", "9条"
    # ])
    player.hand_tiles = hand_tiles
    
    # 分析打牌效率
    efficiency_scores = TileEfficiencyAnalyzer.analyze_discard_efficiency(player, hand_tiles, use_peak_theory=True)
    
    print(f"测试手牌: {' '.join(str(t) for t in hand_tiles)}")
    print(f"缺门: {player.missing_suit}")
    print(f"向听数: {ShantenCalculator.calculate_shanten(hand_tiles)}")
    print()
    
    # 按效率排序
    sorted_tiles = sorted(efficiency_scores.items(), key=lambda x: x[1][0], reverse=True)
    
    print("打牌效率分析 (分数越高越应该打出):")
    for i, (tile, (score, ukeire)) in enumerate(sorted_tiles[:5]):
        print(f"   {i+1}. {tile}: {score:.2f}分, {sum(ukeire.values())}张进张")
    print()

def test_ai_decision_quality():
    """测试AI决策质量"""
    print("🎯 测试AI决策质量")
    print("=" * 50)
    
    # 创建ShantenAI
    shanten_ai = ShantenAI("hard")
    
    # 创建测试玩家
    player = Player("ShantenAI", PlayerType.AI_HARD, 0)
    player.missing_suit = "万"
    
    # 测试各种手牌情况下的决策
    test_hands = [
        (["1万", "9万", "2筒", "3筒", "4筒", "5条", "5条", "5条", "6条", "7条", "东", "南", "西"], "常规手牌"),
        (["1万", "1万", "2万", "2万", "3筒", "3筒", "4条", "4条", "5条", "5条", "6条", "6条", "7条"], "七对子倾向"),
        (["2筒", "3筒", "4筒", "5筒", "6筒", "7筒", "8筒", "1条", "2条", "3条", "4条", "5条", "6条"], "清一色倾向"),
    ]
    
    for hand_str, description in test_hands:
        hand_tiles = create_test_tiles(hand_str)
        player.hand_tiles = hand_tiles
        
        # AI选择打牌
        discard_tile = shanten_ai.choose_discard(player, hand_tiles)
        
        # 计算打牌后的向听数
        remaining_tiles = [t for t in hand_tiles if t != discard_tile]
        original_shanten = ShantenCalculator.calculate_shanten(hand_tiles)
        after_shanten = ShantenCalculator.calculate_shanten(remaining_tiles)
        
        print(f"{description}:")
        print(f"   手牌: {' '.join(str(t) for t in hand_tiles)}")
        print(f"   AI选择打出: {discard_tile}")
        print(f"   向听数变化: {original_shanten} → {after_shanten}")
        
        # 评估决策质量
        if after_shanten <= original_shanten:
            print(f"   ✅ 决策良好 (向听数未增加)")
        else:
            print(f"   ❌ 决策有问题 (向听数增加了)")
        
        print()

def test_ai_vs_ai_battle():
    """测试AI对战"""
    print("🎯 测试AI对战表现")
    print("=" * 50)
    
    # 创建不同的AI
    ais = {
        "ShantenAI": ShantenAI("hard"),
        "SimpleAI": SimpleAI("hard"),
        "AggressiveAI": AggressiveAI("aggressive")
    }
    
    print("进行快速对战测试...")
    
    # 简化的对战测试
    for ai_name, ai in ais.items():
        print(f"\n{ai_name} 特性测试:")
        
        # 创建测试玩家
        player = Player(ai_name, PlayerType.AI_HARD, 0)
        test_hand = create_test_tiles(["1万", "2万", "3万", "4筒", "5筒", "6筒", "7条", "8条", "9条", "东", "东", "南", "西"])
        player.hand_tiles = test_hand
        player.missing_suit = "万"
        
        # 测试缺门选择
        missing_suit = ai.choose_missing_suit(player)
        print(f"   缺门选择: {missing_suit}")
        
        # 测试出牌选择
        discard = ai.choose_discard(player, test_hand)
        print(f"   出牌选择: {discard}")
        
        # 如果是ShantenAI，显示分析
        if isinstance(ai, ShantenAI):
            analysis = ai.provide_analysis(player)
            print(f"   AI分析:\n{analysis}")

def run_performance_benchmark():
    """性能基准测试"""
    print("🎯 性能基准测试")
    print("=" * 50)
    
    # 测试向听数计算性能
    test_hand = create_test_tiles(["1万", "2万", "3万", "4万", "5万", "6万", "7万", "8万", "9万", "1筒", "2筒", "3筒", "5筒"])
    
    start_time = time.time()
    for _ in range(1000):
        ShantenCalculator.calculate_shanten(test_hand)
    end_time = time.time()
    
    avg_time = (end_time - start_time) / 1000 * 1000  # 转换为毫秒
    print(f"向听数计算性能: 平均 {avg_time:.3f} 毫秒/次")
    
    # 测试AI决策性能
    ai = ShantenAI("hard")
    player = Player("测试", PlayerType.AI_HARD, 0)
    player.hand_tiles = test_hand
    player.missing_suit = "万"
    
    start_time = time.time()
    for _ in range(100):
        ai.choose_discard(player, test_hand)
    end_time = time.time()
    
    avg_time = (end_time - start_time) / 100 * 1000  # 转换为毫秒
    print(f"AI决策性能: 平均 {avg_time:.3f} 毫秒/次")
    print()

def main():
    """主测试函数"""
    print("🀄 ShantenAI 功能测试")
    print("=" * 80)
    print("基于向听数和牌效率理论的麻将AI测试")
    print("=" * 80)
    print()
    
    try:
        # 基础功能测试
        test_shanten_calculation()
        test_ukeire_calculation()
        test_tile_efficiency_analysis()
        
        # AI决策测试
        test_ai_decision_quality()
        test_ai_vs_ai_battle()
        
        # 性能测试
        run_performance_benchmark()
        
        print("🎉 所有测试完成！")
        print("=" * 80)
        print("ShantenAI已成功集成到麻将游戏系统中")
        print("可以在demo_cli.py中选择'Expert (专家)'难度体验")
        print("可以在test_ai_battle.py中测试'shanten_hard'等配置")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # main() 
    test_tile_efficiency_analysis()