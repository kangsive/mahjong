#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试换三张功能
"""

from game.game_engine import GameEngine, GameState, GameMode
from rules.sichuan_rule import SichuanRule
from game.player import Player, PlayerType
from game.tile import Tile, TileType

def test_tile_exchange():
    """测试换三张功能"""
    print("=== 测试换三张功能 ===")
    
    # 创建游戏引擎
    engine = GameEngine()
    engine.setup_game(GameMode.TRAINING, 'sichuan')
    
    print(f"初始状态: {engine.state}")
    
    # 开始游戏
    success = engine.start_new_game()
    print(f"游戏启动: {success}")
    print(f"当前状态: {engine.state}")
    
    # 检查是否进入换三张阶段
    if engine.state == GameState.TILE_EXCHANGE:
        print("✅ 成功进入换三张阶段")
        
        # 显示玩家手牌
        for i, player in enumerate(engine.players):
            print(f"\n玩家{i+1}手牌: {[str(t) for t in player.hand_tiles]}")
            
            # 按花色分组显示
            suits = {}
            for tile in player.hand_tiles:
                if tile.tile_type not in suits:
                    suits[tile.tile_type] = []
                suits[tile.tile_type].append(tile)
            
            for suit_type, tiles in suits.items():
                print(f"  {suit_type.value}: {[str(t) for t in tiles]} ({len(tiles)}张)")
        
        # 模拟玩家选择换牌
        print("\n=== 模拟换牌选择 ===")
        
        for i, player in enumerate(engine.players):
            # 找到数量最多的花色的前三张牌
            suits = {}
            for tile in player.hand_tiles:
                if tile.tile_type not in suits:
                    suits[tile.tile_type] = []
                suits[tile.tile_type].append(tile)
            
            # 选择数量最多的花色
            max_suit = max(suits.keys(), key=lambda s: len(suits[s]))
            exchange_tiles = suits[max_suit][:3]
            
            print(f"玩家{i+1}选择换牌: {[str(t) for t in exchange_tiles]}")
            
            # 提交换牌
            success = engine.submit_exchange_tiles(i, exchange_tiles)
            print(f"  提交结果: {success}")
        
        # 检查状态变化
        print(f"\n换牌后状态: {engine.state}")
        
        if engine.state == GameState.MISSING_SUIT_SELECTION:
            print("✅ 成功进入选择缺一门阶段")
            
            # 显示换牌后的手牌
            print("\n=== 换牌后手牌 ===")
            for i, player in enumerate(engine.players):
                print(f"玩家{i+1}: {[str(t) for t in player.hand_tiles]}")
            
            # 模拟选择缺一门
            print("\n=== 模拟选择缺一门 ===")
            suits_list = [TileType.WAN, TileType.TONG, TileType.TIAO]
            
            for i, player in enumerate(engine.players):
                # 统计各花色数量，选择最少的
                suit_counts = {suit: 0 for suit in suits_list}
                for tile in player.hand_tiles:
                    if tile.tile_type in suit_counts:
                        suit_counts[tile.tile_type] += 1
                
                missing_suit = min(suit_counts.keys(), key=lambda s: suit_counts[s])
                print(f"玩家{i+1}选择缺{missing_suit.value} (有{suit_counts[missing_suit]}张)")
                
                success = engine.submit_missing_suit(i, missing_suit)
                print(f"  提交结果: {success}")
            
            print(f"\n最终状态: {engine.state}")
            
            if engine.state == GameState.PLAYING:
                print("✅ 成功进入游戏阶段")
                
                # 显示最终游戏状态
                game_state = engine.get_game_state()
                print(f"游戏状态信息: {game_state}")
                
                print("\n=== 最终手牌和缺门 ===")
                for i, player in enumerate(engine.players):
                    player_info = engine.get_player_info(i)
                    print(f"玩家{i+1}: 手牌{len(player.hand_tiles)}张, 缺{player_info['missing_suit']}")
            else:
                print(f"❌ 未能进入游戏阶段，当前状态: {engine.state}")
        else:
            print(f"❌ 未能进入选择缺一门阶段，当前状态: {engine.state}")
    else:
        print(f"❌ 未能进入换三张阶段，当前状态: {engine.state}")

if __name__ == "__main__":
    test_tile_exchange() 