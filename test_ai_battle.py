#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI对战测试脚本 - 支持多种测试模式

模式1：同水平对局 - 所有玩家使用相同AI类型，支持多种AI对比
模式2：混合水平对局 - 4个玩家使用不同AI类型组合

确保与demo_cli.py的游戏逻辑完全一致
"""

import sys
import os
import time
import logging
from collections import defaultdict, Counter
import traceback
from typing import Dict, List, Optional, Type, Tuple
from enum import Enum

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 禁用所有日志输出，避免干扰测试结果
logging.disable(logging.CRITICAL)
root_logger = logging.getLogger()
root_logger.disabled = True
root_logger.setLevel(logging.CRITICAL + 1)

from game.game_engine import GameEngine, GameMode, GameAction
from game.player import PlayerType, Player
from game.tile import Tile
from ai.simple_ai import SimpleAI
from ai.mcts_ai import MctsAI
from ai.aggressive_ai import AggressiveAI
from ai.shanten_ai import ShantenAI
from ai.base_ai import BaseAI
from rules.sichuan_rule import SichuanRule

class TestMode(Enum):
    """测试模式枚举"""
    SAME_LEVEL = "same_level"      # 同水平对局
    MIXED_LEVEL = "mixed_level"    # 混合水平对局

class AIConfig:
    """AI配置类"""
    def __init__(self, ai_class: Type[BaseAI], difficulty: str, name: str = None):
        self.ai_class = ai_class
        self.difficulty = difficulty
        self.name = name or f"{ai_class.__name__}-{difficulty}"
        
    def __str__(self):
        return self.name
    
    def create_ai(self, engine: GameEngine = None) -> BaseAI:
        """创建AI实例，为MctsAI特殊处理以传递engine"""
        if self.ai_class == MctsAI:
            return self.ai_class(difficulty=self.difficulty, engine=engine)
        return self.ai_class(self.difficulty)

# 预定义AI配置
AVAILABLE_AIS = {
    "simple_easy": AIConfig(SimpleAI, "easy", "SimpleAI-Easy"),
    "simple_medium": AIConfig(SimpleAI, "medium", "SimpleAI-Medium"), 
    "simple_hard": AIConfig(SimpleAI, "hard", "SimpleAI-Hard"),
    "mcts_hard": AIConfig(MctsAI, "hard", "MctsAI-Hard"),
    "aggressive": AIConfig(AggressiveAI, "aggressive", "AggressiveAI"),
    "shanten_easy": AIConfig(ShantenAI, "easy", "ShantenAI-Easy"),
    "shanten_medium": AIConfig(ShantenAI, "medium", "ShantenAI-Medium"),
    "shanten_hard": AIConfig(ShantenAI, "hard", "ShantenAI-Hard"),
}

# 同水平对局可选AI（simple和shanten系列）
SAME_LEVEL_AIS = {
    "simple_easy": AVAILABLE_AIS["simple_easy"],
    "simple_medium": AVAILABLE_AIS["simple_medium"],
    "simple_hard": AVAILABLE_AIS["simple_hard"],
    "shanten_easy": AVAILABLE_AIS["shanten_easy"],
    "shanten_medium": AVAILABLE_AIS["shanten_medium"],
    "shanten_hard": AVAILABLE_AIS["shanten_hard"],
}

class GameStats:
    """单次游戏统计"""
    def __init__(self):
        self.total_games = 0
        self.completed_games = 0
        self.draw_games = 0
        self.win_methods = Counter()  # 胜利方式计数
        self.player_wins = Counter()  # 各玩家胜利次数
        self.ai_type_wins = Counter()  # 各AI类型胜利次数
        self.game_lengths = []  # 游戏长度
        self.errors = []  # 错误记录
        self.player_scores = defaultdict(list)  # 各玩家分数记录
        self.player_win_methods = defaultdict(Counter)  # 各玩家胜利方式

class AIBattleSimulator:
    """AI对战模拟器 - 完全兼容demo_cli.py的游戏逻辑"""
    
    def __init__(self):
        self.stats = GameStats()
    
    def create_engine_with_ai_players(self, ai_configs: List[AIConfig]) -> GameEngine:
        """创建带有指定AI玩家的游戏引擎，确保与demo_cli.py逻辑一致"""
        if len(ai_configs) != 4:
            raise ValueError("必须指定4个AI配置")
        
        # 使用与demo_cli.py相同的初始化方式
        engine = GameEngine()
        engine.setup_game(GameMode.COMPETITIVE, "sichuan")
        
        # 替换玩家为AI，保持相同的初始化逻辑
        engine.players = []
        for i, ai_config in enumerate(ai_configs):
            player = Player(f"{ai_config.name}_{i+1}", PlayerType.AI_HARD, i)
            engine.players.append(player)
        
        return engine
    
    def simulate_ai_decision(self, player: Player, ai_config: AIConfig, engine: GameEngine, decision_type: str, **kwargs) -> any:
        """模拟AI决策，确保与demo_cli.py的AI调用方式一致"""
        ai = ai_config.create_ai(engine=engine)
        
        if decision_type == "exchange_tiles":
            if hasattr(ai, 'choose_exchange_tiles'):
                return ai.choose_exchange_tiles(player, kwargs.get('count', 3))
            else:
                # 默认换牌策略
                suits = {}
                for tile in player.hand_tiles:
                    if tile.tile_type not in suits:
                        suits[tile.tile_type] = []
                    suits[tile.tile_type].append(tile)
                
                if suits:
                    max_suit = max(suits.keys(), key=lambda s: len(suits[s]))
                    return suits[max_suit][:kwargs.get('count', 3)]
                return player.hand_tiles[:kwargs.get('count', 3)]
        
        elif decision_type == "missing_suit":
            if hasattr(ai, 'choose_missing_suit'):
                return ai.choose_missing_suit(player)
            else:
                return SimpleAI("medium").choose_missing_suit(player)
        
        elif decision_type == "discard":
            available_tiles = kwargs.get('available_tiles', [])
            return ai.choose_discard(player, available_tiles)
        
        elif decision_type == "action":
            available_actions = kwargs.get('available_actions', [])
            context = kwargs.get('context', {})
            return ai.decide_action(player, available_actions, context)
        
        return None
    
    def simulate_single_game(self, ai_configs: List[AIConfig], game_id: int) -> Dict:
        """模拟单局游戏，完全复制demo_cli.py的游戏流程"""
        try:
            # 1. 创建游戏引擎（与demo_cli.py相同）
            engine = self.create_engine_with_ai_players(ai_configs)
            
            # 2. 开始游戏（与demo_cli.py相同）
            if not engine.start_new_game():
                return {'completed': False, 'error': 'Failed to start game'}
            
            turn_count = 0
            max_turns = 1000
            
            # 3. 换三张阶段（与demo_cli.py相同的处理方式）
            if engine.state.value == 'tile_exchange':
                for player in engine.players:
                    if player.player_id not in engine.exchange_tiles:
                        ai_config = ai_configs[player.player_id]
                        selected_tiles = self.simulate_ai_decision(
                            player, ai_config, engine, "exchange_tiles", count=3
                        )
                        engine.submit_exchange_tiles(player.player_id, selected_tiles)
                
                # 等待换牌阶段完成
                while engine.state.value == 'tile_exchange' and turn_count < 10:
                    time.sleep(0.001)
                    turn_count += 1
            
            # 4. 选择缺门阶段（与demo_cli.py相同）
            if engine.state.value == 'missing_suit_selection':
                for player in engine.players:
                    if not player.missing_suit:
                        ai_config = ai_configs[player.player_id]
                        missing_suit = self.simulate_ai_decision(
                            player, ai_config, engine, "missing_suit"
                        )
                        engine.set_player_missing_suit(player, missing_suit)
                
                if engine.state.value != 'playing':
                    engine._start_playing()
            
            # 5. 主游戏循环（完全复制demo_cli.py的逻辑）
            turn_count = 0
            last_discarder = None
            
            while not engine.is_game_over() and turn_count < max_turns:
                turn_count += 1
                
                current_player = engine.get_current_player()
                if not current_player:
                    break
                
                if getattr(current_player, 'is_winner', False):
                    engine.next_turn()
                    continue
                
                game_state = engine.get_game_status()['state']
                
                # 5a. 响应阶段处理（与demo_cli.py相同的优先级处理）
                print(f"current_player {current_player.name} hand tiles before response: {current_player.hand_tiles}, melds: {[tile for meld in current_player.melds for tile in meld.tiles]}")
                if game_state == 'waiting_action' and last_discarder:
                    action_taken = self._handle_response_phase(engine, ai_configs, last_discarder)
                    if action_taken:
                        last_discarder = None
                    else:
                        # 没有人响应，继续游戏
                        player_to_pass = next((p for p in engine.players if p != last_discarder), None)
                        if player_to_pass:
                            engine.execute_player_action(player_to_pass, None)
                        last_discarder = None
                    continue
                print(f"current_player {current_player.name} hand tiles after response: {current_player.hand_tiles}, melds: {[tile for meld in current_player.melds for tile in meld.tiles]}")
                
                # 5b. 出牌阶段（与demo_cli.py相同）
                if game_state == 'playing':
                    success = self._handle_playing_phase(engine, ai_configs, current_player)
                    if not success:
                        break
                    last_discarder = current_player
                print(f"current_player {current_player.name} hand tiles after playing: {current_player.hand_tiles}, melds: {[tile for meld in current_player.melds for tile in meld.tiles]}")
            
            # 6. 收集游戏结果（与demo_cli.py相同的结果处理）
            return self._collect_game_result(engine, ai_configs, turn_count)
            
        except Exception as e:
            traceback.print_exc()
            return {'completed': False, 'error': f"Exception: {str(e)}"}
    
    def _handle_response_phase(self, engine: GameEngine, ai_configs: List[AIConfig], last_discarder: Player) -> bool:
        """处理响应阶段，与demo_cli.py的逻辑完全一致"""
        if not engine.last_discarded_tile:
            return False
        
        actions = []
        
        # 收集所有可能的响应动作（与demo_cli.py相同的检查顺序）
        for player in engine.players:
            if player == last_discarder or getattr(player, 'is_winner', False):
                continue
            
            available_actions = []
            
            # 按照与demo_cli.py相同的优先级检查
            if engine.can_player_action(player, GameAction.WIN):
                available_actions.append(GameAction.WIN)
            if engine.can_player_action(player, GameAction.GANG):
                available_actions.append(GameAction.GANG)
            if engine.can_player_action(player, GameAction.PENG):
                available_actions.append(GameAction.PENG)
            
            if available_actions:
                available_actions.append(GameAction.PASS) # 总是可以Pass
                ai_config = ai_configs[player.player_id]
                context = {
                    "last_discarded_tile": engine.last_discarded_tile,
                    "discard_pool": engine.discard_pool,
                    "remaining_tiles": engine.deck.get_remaining_count() if engine.deck else 0,
                    "engine": engine
                }
                
                chosen_action = self.simulate_ai_decision(
                    player, ai_config, engine, "action", 
                    available_actions=available_actions, context=context
                )
                
                if chosen_action and chosen_action != GameAction.PASS:
                    # 与demo_cli.py相同的优先级设置
                    priority = 3 if chosen_action == GameAction.WIN else (2 if chosen_action == GameAction.GANG else 1)
                    actions.append({'player': player, 'action': chosen_action, 'priority': priority})
        
        if not actions:
            return False
        
        # 执行最高优先级的动作（与demo_cli.py相同）
        max_priority = max(a['priority'] for a in actions)
        best_actions = [a for a in actions if a['priority'] == max_priority]
        
        if best_actions:
            chosen_action_data = best_actions[0]  # 选择第一个最高优先级动作
            actor = chosen_action_data['player']
            action = chosen_action_data['action']
            
            success = engine.execute_player_action(actor, action)
            return success
        
        return False
    
    def _handle_playing_phase(self, engine: GameEngine, ai_configs: List[AIConfig], current_player: Player) -> bool:
        """处理出牌阶段，与demo_cli.py的逻辑完全一致"""
        
        # 1. 检查自摸
        if engine.can_player_action(current_player, GameAction.WIN):
            success = engine.execute_player_action(current_player, GameAction.WIN)
            return True # 无论是否成功，都结束当前回合
        
        # 2. 决定出牌
        ai_config = ai_configs[current_player.player_id]
        available_tiles = [t for t in current_player.hand_tiles if engine.rule.can_discard(current_player, t)]
        if not available_tiles:
            return False # 游戏卡住
        
        context = {"engine": engine}
        tile_to_discard = self.simulate_ai_decision(
            current_player, ai_config, engine, "discard", 
            available_tiles=available_tiles, context=context
        )
        
        if tile_to_discard:
            return engine.execute_player_action(current_player, GameAction.DISCARD, tile_to_discard)
        
        return False # 未能选择出牌
    
    def _collect_game_result(self, engine: GameEngine, ai_configs: List[AIConfig], turn_count: int) -> Dict:
        """收集游戏结果，与demo_cli.py相同的结果处理"""
        winners = [p for p in engine.players if getattr(p, 'is_winner', False)]
        
        result = {
            'completed': True,
            'winners': [],
            'final_scores': {p.name: p.score for p in engine.players},
            'game_length': turn_count,
            'remaining_tiles': engine.deck.get_remaining_count() if engine.deck else 0,
            'ai_configs': [str(config) for config in ai_configs]  # 记录AI配置
        }
        
        # 分析胜利情况（与demo_cli.py相同的胜利检测逻辑）
        for winner in winners:
            win_method = "自摸"  # 默认自摸
            
            # 检查是否是点炮胡牌（与demo_cli.py相同的检测方式）
            if (engine.last_discarded_tile and 
                hasattr(engine, 'last_discard_player') and engine.last_discard_player and 
                engine.last_discard_player != winner):
                win_method = "点炮"
            
            result['winners'].append({
                'player_name': winner.name,
                'player_id': winner.player_id,
                'ai_type': str(ai_configs[winner.player_id]),
                'method': win_method,
                'score': winner.score
            })
        
        return result
    
    def run_same_level_test(self, ai_types: List[str], num_games: int = 50) -> Dict:
        """运行同水平对局测试"""
        results = {}
        
        for ai_type in ai_types:
            if ai_type not in SAME_LEVEL_AIS:
                print(f"⚠️ 未知AI类型: {ai_type}")
                continue
            
            ai_config = SAME_LEVEL_AIS[ai_type]
            ai_configs = [ai_config] * 4  # 4个相同的AI
            
            print(f"\n{'='*60}")
            print(f"🤖 测试AI类型: {ai_config.name}")
            print(f"{'='*60}")
            
            stats = GameStats()
            start_time = time.time()
            
            for game_id in range(1, num_games + 1):
                print(f"\r正在进行第 {game_id}/{num_games} 场游戏...", end="", flush=True)
                
                result = self.simulate_single_game(ai_configs, game_id)
                print(result)
                self._update_stats(stats, result, ai_configs)
                
                if game_id % 10 == 0:
                    self._print_progress(game_id, num_games, stats)
            
            elapsed = time.time() - start_time
            print(f"\n\n✅ 测试完成！耗时 {elapsed:.2f} 秒")
            print(f"平均每场游戏: {elapsed/num_games:.3f} 秒")
            
            results[ai_type] = self._print_stats_summary(stats, ai_config.name)
        
        return results
    
    def run_mixed_level_test(self, ai_pattern: List[str], num_games: int = 50) -> Dict:
        """运行混合水平对局测试"""
        if len(ai_pattern) != 4:
            raise ValueError("AI模式必须包含4个AI类型")
        
        ai_configs = []
        for i, ai_type in enumerate(ai_pattern):
            if ai_type not in AVAILABLE_AIS:
                raise ValueError(f"未知AI类型: {ai_type}")
            ai_configs.append(AVAILABLE_AIS[ai_type])
        
        pattern_name = " vs ".join([config.name for config in ai_configs])
        print(f"\n{'='*80}")
        print(f"⚔️ 混合水平对局测试: {pattern_name}")
        print(f"{'='*80}")
        
        stats = GameStats()
        start_time = time.time()
        
        for game_id in range(1, num_games + 1):
            print(f"\r正在进行第 {game_id}/{num_games} 场游戏...", end="", flush=True)
            
            result = self.simulate_single_game(ai_configs, game_id)
            self._update_stats(stats, result, ai_configs)
            
            if game_id % 10 == 0:
                self._print_progress(game_id, num_games, stats)
        
        elapsed = time.time() - start_time
        print(f"\n\n✅ 测试完成！耗时 {elapsed:.2f} 秒")
        print(f"平均每场游戏: {elapsed/num_games:.3f} 秒")
        
        return self._print_mixed_stats_summary(stats, ai_configs)
    
    def _update_stats(self, stats: GameStats, result: Dict, ai_configs: List[AIConfig]):
        """更新统计数据"""
        stats.total_games += 1
        
        if result['completed']:
            stats.completed_games += 1
            
            # 记录所有玩家的分数
            for player_name, score in result['final_scores'].items():
                stats.player_scores[player_name].append(score)
            
            if result['winners']:
                for winner_info in result['winners']:
                    stats.win_methods[winner_info['method']] += 1
                    stats.player_wins[winner_info['player_name']] += 1
                    stats.ai_type_wins[winner_info['ai_type']] += 1
                    stats.player_win_methods[winner_info['player_name']][winner_info['method']] += 1
            else:
                stats.draw_games += 1
            
            stats.game_lengths.append(result['game_length'])
        else:
            stats.errors.append(result.get('error', 'Unknown error'))
    
    def _print_progress(self, current: int, total: int, stats: GameStats):
        """打印进度"""
        completed = stats.completed_games
        draw = stats.draw_games
        errors = len(stats.errors)
        print(f"\r进度 {current}/{total} - 完成:{completed} 流局:{draw} 错误:{errors}")
    
    def _print_stats_summary(self, stats: GameStats, ai_name: str) -> Dict:
        """打印统计摘要"""
        print(f"\n{'='*80}")
        print(f"🀄 {ai_name} 测试结果总结 (共{stats.total_games}场游戏)")
        print(f"{'='*80}")
        
        # 基础统计
        print(f"\n📊 基础统计:")
        completion_rate = stats.completed_games / stats.total_games * 100
        draw_rate = stats.draw_games / stats.total_games * 100
        error_rate = len(stats.errors) / stats.total_games * 100
        
        print(f"  ✅ 正常完成游戏: {stats.completed_games} 场 ({completion_rate:.1f}%)")
        print(f"  🤝 流局: {stats.draw_games} 场 ({draw_rate:.1f}%)")
        print(f"  ❌ 错误/未完成: {len(stats.errors)} 场 ({error_rate:.1f}%)")
        
        # 胜利方式统计
        if stats.win_methods:
            print(f"\n🏆 胜利方式统计:")
            total_wins = sum(stats.win_methods.values())
            for method, count in stats.win_methods.most_common():
                percentage = count / total_wins * 100
                method_name = {"自摸": "自摸胡牌", "点炮": "点炮胡牌"}.get(method, method)
                print(f"  {method_name}: {count} 次 ({percentage:.1f}%)")
        
        # 各个玩家详细统计
        if stats.player_wins:
            print(f"\n👤 各玩家详细统计:")
            for player_name in sorted(stats.player_wins.keys()):
                wins = stats.player_wins[player_name]
                win_rate = wins / stats.completed_games * 100 if stats.completed_games > 0 else 0
                scores = stats.player_scores[player_name]
                avg_score = sum(scores) / len(scores) if scores else 0
                
                print(f"\n  📋 {player_name}:")
                print(f"    胜局: {wins} 场 (胜率: {win_rate:.1f}%)")
                print(f"    平均分数: {avg_score:.1f}")
                
                # 胜利方式分布
                win_methods = stats.player_win_methods[player_name]
                if win_methods:
                    print(f"    胜利方式分布:")
                    for method, count in win_methods.items():
                        method_rate = count / wins * 100 if wins > 0 else 0
                        method_name = {"自摸": "自摸", "点炮": "点炮"}.get(method, method)
                        print(f"      {method_name}: {count} 次 ({method_rate:.1f}%)")
        
        # 游戏长度统计
        if stats.game_lengths:
            avg_length = sum(stats.game_lengths) / len(stats.game_lengths)
            min_length = min(stats.game_lengths)
            max_length = max(stats.game_lengths)
            print(f"\n⏱️ 游戏长度统计:")
            print(f"  平均出牌次数: {avg_length:.1f}")
            print(f"  最短游戏: {min_length} 次出牌")
            print(f"  最长游戏: {max_length} 次出牌")
        
        return {
            'completion_rate': completion_rate,
            'draw_rate': draw_rate,
            'win_rate': (stats.total_games - stats.draw_games) / stats.total_games * 100,
            'avg_game_length': sum(stats.game_lengths) / len(stats.game_lengths) if stats.game_lengths else 0,
            'error_rate': error_rate
        }
    
    def _print_mixed_stats_summary(self, stats: GameStats, ai_configs: List[AIConfig]) -> Dict:
        """打印混合对局统计摘要"""
        print(f"\n{'='*80}")
        print(f"🀄 混合水平对局测试结果总结 (共{stats.total_games}场游戏)")
        print(f"{'='*80}")
        
        # 基础统计
        completion_rate = stats.completed_games / stats.total_games * 100
        draw_rate = stats.draw_games / stats.total_games * 100
        
        print(f"\n📊 基础统计:")
        print(f"  ✅ 正常完成游戏: {stats.completed_games} 场 ({completion_rate:.1f}%)")
        print(f"  🤝 流局: {stats.draw_games} 场 ({draw_rate:.1f}%)")
        print(f"  ❌ 错误/未完成: {len(stats.errors)} 场 ({len(stats.errors)/stats.total_games*100:.1f}%)")
        
        # AI类型胜利统计
        if stats.ai_type_wins:
            print(f"\n🤖 各AI类型胜利统计:")
            total_wins = sum(stats.ai_type_wins.values())
            for ai_type, wins in stats.ai_type_wins.most_common():
                percentage = wins / total_wins * 100
                print(f"  {ai_type}: {wins} 次 ({percentage:.1f}%)")
        
        # 各个玩家详细统计
        print(f"\n👤 各玩家详细统计:")
        for i, ai_config in enumerate(ai_configs):
            player_names = [name for name in stats.player_wins.keys() if name.endswith(f'_{i+1}')]
            if player_names:
                player_name = player_names[0]
                wins = stats.player_wins[player_name]
                win_rate = wins / stats.completed_games * 100 if stats.completed_games > 0 else 0
                scores = stats.player_scores[player_name]
                avg_score = sum(scores) / len(scores) if scores else 0
                
                print(f"\n  📋 位置{i+1} - {ai_config.name}:")
                print(f"    胜局: {wins} 场 (胜率: {win_rate:.1f}%)")
                print(f"    平均分数: {avg_score:.1f}")
                
                # 胜利方式分布
                win_methods = stats.player_win_methods[player_name]
                if win_methods:
                    print(f"    胜利方式分布:")
                    for method, count in win_methods.items():
                        method_rate = count / wins * 100 if wins > 0 else 0
                        method_name = {"自摸": "自摸", "点炮": "点炮"}.get(method, method)
                        print(f"      {method_name}: {count} 次 ({method_rate:.1f}%)")
            else:
                print(f"\n  📋 位置{i+1} - {ai_config.name}:")
                print(f"    胜局: 0 场 (胜率: 0.0%)")
                print(f"    平均分数: 0.0")
        
        # 胜利方式统计
        if stats.win_methods:
            print(f"\n🏆 胜利方式统计:")
            total_wins = sum(stats.win_methods.values())
            for method, count in stats.win_methods.most_common():
                percentage = count / total_wins * 100
                method_name = {"自摸": "自摸胡牌", "点炮": "点炮胡牌"}.get(method, method)
                print(f"  {method_name}: {count} 次 ({percentage:.1f}%)")
        
        # 游戏长度统计
        if stats.game_lengths:
            avg_length = sum(stats.game_lengths) / len(stats.game_lengths)
            min_length = min(stats.game_lengths)
            max_length = max(stats.game_lengths)
            print(f"\n⏱️ 游戏长度统计:")
            print(f"  平均出牌次数: {avg_length:.1f}")
            print(f"  最短游戏: {min_length} 次出牌")
            print(f"  最长游戏: {max_length} 次出牌")
        
        return {
            'completion_rate': completion_rate,
            'draw_rate': draw_rate,
            'ai_type_performance': dict(stats.ai_type_wins),
            'avg_game_length': sum(stats.game_lengths) / len(stats.game_lengths) if stats.game_lengths else 0
        }

def print_main_menu():
    """打印主菜单"""
    print("\n" + "="*80)
    print("🀄 AI对战测试模拟器")
    print("="*80)
    print("\n请选择测试模式:")
    print("  1. 同水平对局 - 所有玩家使用相同AI类型")
    print("  2. 混合水平对局 - 4个玩家使用不同AI类型组合")
    print("  0. 退出")

def print_same_level_menu():
    """打印同水平对局AI选择菜单"""
    print("\n" + "="*60)
    print("🤖 同水平对局 - 可选AI类型")
    print("="*60)
    print("\nSimple AI系列:")
    print("  1. SimpleAI-Easy    - 简单AI（容易难度）")
    print("  2. SimpleAI-Medium  - 简单AI（中等难度）")
    print("  3. SimpleAI-Hard    - 简单AI（困难难度）")
    print("\nShanten AI系列:")
    print("  4. ShantenAI-Easy   - 向听数AI（容易难度）")
    print("  5. ShantenAI-Medium - 向听数AI（中等难度）")
    print("  6. ShantenAI-Hard   - 向听数AI（困难难度）")
    print("\n  0. 返回主菜单")

def print_mixed_level_menu():
    """打印混合水平对局AI选择菜单"""
    print("\n" + "="*60)
    print("⚔️ 混合水平对局 - 可选AI类型")
    print("="*60)
    print("  1. SimpleAI-Easy    - 简单AI（容易难度）")
    print("  2. SimpleAI-Medium  - 简单AI（中等难度）")
    print("  3. SimpleAI-Hard    - 简单AI（困难难度）")
    print("  4. MctsAI-Hard      - MCTS AI（困难难度）")
    print("  5. AggressiveAI     - 激进AI")
    print("  6. ShantenAI-Easy   - 向听数AI（容易难度）")
    print("  7. ShantenAI-Medium - 向听数AI（中等难度）")
    print("  8. ShantenAI-Hard   - 向听数AI（困难难度）")

def get_same_level_ai_choice():
    """获取同水平对局AI选择"""
    ai_mapping = {
        1: "simple_easy",
        2: "simple_medium", 
        3: "simple_hard",
        4: "shanten_easy",
        5: "shanten_medium",
        6: "shanten_hard"
    }
    
    while True:
        try:
            choice = int(input("\n请选择AI类型 (1-6): "))
            if choice == 0:
                return None
            elif choice in ai_mapping:
                return ai_mapping[choice]
            else:
                print("❌ 无效选择，请输入1-6之间的数字")
        except ValueError:
            print("❌ 请输入有效的数字")
        except EOFError:
            return None

def get_mixed_level_ai_choices():
    """获取混合水平对局AI选择"""
    ai_mapping = {
        1: "simple_easy",
        2: "simple_medium",
        3: "simple_hard", 
        4: "mcts_hard",
        5: "aggressive",
        6: "shanten_easy",
        7: "shanten_medium",
        8: "shanten_hard"
    }
    
    ai_pattern = []
    positions = ["第一个", "第二个", "第三个", "第四个"]
    
    for i in range(4):
        while True:
            try:
                choice = int(input(f"\n请选择{positions[i]}玩家的AI类型 (1-8): "))
                if choice in ai_mapping:
                    ai_pattern.append(ai_mapping[choice])
                    selected_ai = AVAILABLE_AIS[ai_mapping[choice]].name
                    print(f"✅ 已选择: {selected_ai}")
                    break
                else:
                    print("❌ 无效选择，请输入1-8之间的数字")
            except ValueError:
                print("❌ 请输入有效的数字")
            except EOFError:
                return None
    
    return ai_pattern

def get_game_count():
    """获取游戏局数"""
    while True:
        try:
            count = int(input("\n请输入测试局数 (建议10-100): "))
            if count > 0:
                return count
            else:
                print("❌ 游戏局数必须大于0")
        except ValueError:
            print("❌ 请输入有效的数字")
        except EOFError:
            return 10  # 默认返回10局

def main():
    """主函数，用于执行测试"""
    simulator = AIBattleSimulator()
    
    while True:
        print_main_menu()
        
        try:
            mode_choice = int(input("\n请选择模式 (0-2): "))
            
            if mode_choice == 0:
                print("\n👋 谢谢使用，再见！")
                break
            
            elif mode_choice == 1:
                # 同水平对局
                while True:
                    print_same_level_menu()
                    ai_choice = get_same_level_ai_choice()
                    
                    if ai_choice is None:
                        break
                    
                    game_count = get_game_count()
                    
                    print(f"\n🚀 开始同水平对局测试...")
                    print(f"AI类型: {SAME_LEVEL_AIS[ai_choice].name}")
                    print(f"测试局数: {game_count}")
                    print("-" * 60)
                    
                    simulator.run_same_level_test([ai_choice], game_count)
                    
                    # 询问是否继续
                    continue_choice = input("\n是否继续测试其他AI? (y/n): ").lower()
                    if continue_choice != 'y':
                        break
            
            elif mode_choice == 2:
                # 混合水平对局
                print_mixed_level_menu()
                
                print("\n请依次选择4个玩家的AI类型:")
                ai_pattern = get_mixed_level_ai_choices()
                
                game_count = get_game_count()
                
                print(f"\n🚀 开始混合水平对局测试...")
                print("AI配置:")
                for i, ai_key in enumerate(ai_pattern):
                    print(f"  玩家{i+1}: {AVAILABLE_AIS[ai_key].name}")
                print(f"测试局数: {game_count}")
                print("-" * 60)
                
                simulator.run_mixed_level_test(ai_pattern, game_count)
                
                # 询问是否继续
                continue_choice = input("\n是否继续测试其他组合? (y/n): ").lower()
                if continue_choice != 'y':
                    break
            
            else:
                print("❌ 无效选择，请输入0-2之间的数字")
                
        except ValueError:
            print("❌ 请输入有效的数字")
        except KeyboardInterrupt:
            print("\n\n👋 测试被用户中断，再见！")
            break
        except EOFError:
            print("\n\n👋 检测到输入结束，程序退出！")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")

if __name__ == "__main__":
    main() 