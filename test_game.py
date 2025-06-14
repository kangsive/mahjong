#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麻将游戏测试脚本
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_tiles():
    """测试麻将牌类"""
    print("测试麻将牌类...")
    
    from game.tile import Tile, TileType, FengType, JianType, create_tile_from_string
    
    # 测试数字牌
    wan1 = Tile(TileType.WAN, 1)
    print(f"1万: {wan1}")
    
    # 测试风牌
    dong = Tile(TileType.FENG, feng_type=FengType.DONG)
    print(f"东风: {dong}")
    
    # 测试箭牌
    zhong = Tile(TileType.JIAN, jian_type=JianType.ZHONG)
    print(f"红中: {zhong}")
    
    # 测试字符串创建
    tile_from_str = create_tile_from_string("9万")
    print(f"从字符串创建: {tile_from_str}")
    
    print("麻将牌类测试完成!\n")

def test_deck():
    """测试牌堆"""
    print("测试牌堆...")
    
    from game.deck import Deck
    
    # 测试四川麻将牌堆
    deck = Deck("sichuan")
    print(f"四川麻将牌堆总数: {deck.get_remaining_count()}")
    
    # 测试摸牌
    tiles = deck.draw_multiple(5)
    print(f"摸5张牌: {[str(t) for t in tiles]}")
    print(f"剩余牌数: {deck.get_remaining_count()}")
    
    print("牌堆测试完成!\n")

def test_player():
    """测试玩家"""
    print("测试玩家...")
    
    from game.player import Player, PlayerType
    from game.tile import create_tile_from_string
    
    player = Player("测试玩家", PlayerType.HUMAN)
    
    # 添加一些牌
    tiles = [
        create_tile_from_string("1万"),
        create_tile_from_string("2万"),
        create_tile_from_string("3万"),
        create_tile_from_string("东"),
        create_tile_from_string("东")
    ]
    
    player.add_tiles(tiles)
    print(f"玩家手牌: {[str(t) for t in player.hand_tiles]}")
    
    # 测试碰牌
    dong_tile = create_tile_from_string("东")
    can_peng = player.can_peng(dong_tile)
    print(f"能否碰东: {can_peng}")
    
    print("玩家测试完成!\n")

def test_rules():
    """测试规则"""
    print("测试规则...")
    
    from rules.sichuan_rule import SichuanRule
    from game.player import Player, PlayerType
    from game.tile import create_tile_from_string
    
    rule = SichuanRule()
    player = Player("测试玩家", PlayerType.HUMAN)
    
    # 测试缺门选择
    test_tiles = [
        create_tile_from_string("1万"),
        create_tile_from_string("2万"),
        create_tile_from_string("东"),
        create_tile_from_string("南"),
        create_tile_from_string("1筒")
    ]
    player.add_tiles(test_tiles)
    
    missing_suit = rule.choose_missing_suit(player)
    print(f"建议缺门: {missing_suit}")
    
    print("规则测试完成!\n")

def test_game_engine():
    """测试游戏引擎"""
    print("测试游戏引擎...")
    
    from game.game_engine import GameEngine, GameMode
    
    engine = GameEngine()
    engine.setup_game(GameMode.TRAINING, "sichuan")
    
    print(f"游戏模式: {engine.mode}")
    print(f"规则类型: {engine.rule_type}")
    print(f"玩家数量: {len(engine.players)}")
    
    # 测试开始游戏
    success = engine.start_new_game()
    print(f"游戏启动成功: {success}")
    
    if success:
        status = engine.get_game_status()
        print(f"游戏状态: {status['state']}")
        print(f"剩余牌数: {status['remaining_tiles']}")
    
    print("游戏引擎测试完成!\n")

def main():
    """主测试函数"""
    print("开始麻将游戏测试...\n")
    
    try:
        test_tiles()
        test_deck()
        test_player()
        test_rules()
        test_game_engine()
        
        print("✅ 所有测试通过!")
        print("\n游戏组件工作正常，可以运行主程序:")
        print("python main.py")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 