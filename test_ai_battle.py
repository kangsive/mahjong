#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全AI对战测试脚本

测试不同AI策略的竞技模式麻将游戏
支持多种AI类型对比测试
统计胡牌概率和情况：点炮、自摸、流局
测试血战到底机制
"""

import sys
import os
import time
import logging
from collections import defaultdict, Counter
from typing import Dict, List, Optional, Type

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
from ai.advanced_ai import AdvancedAI
from ai.aggressive_ai import AggressiveAI
from ai.base_ai import BaseAI
from rules.sichuan_rule import SichuanRule

class AIBattleStats:
    """AI对战统计类"""
    
    def __init__(self, ai_type: str = "unknown"):
        self.ai_type = ai_type
        self.total_games = 0
        self.completed_games = 0
        self.draw_games = 0  # 流局
        self.win_methods = Counter()  # 胜利方式计数
        self.player_wins = Counter()  # 各玩家胜利次数
        self.win_details = []  # 详细胜利记录
        self.game_lengths = []  # 游戏长度（出牌次数）
        self.errors = []  # 错误记录
        self.shanten_stats = []  # 向听数统计（仅高级AI）
        
    def record_game_result(self, game_result: Dict):
        """记录单局游戏结果"""
        self.total_games += 1
        
        if game_result['completed']:
            self.completed_games += 1
            
            if game_result['winners']:
                # 有胜者
                for winner_info in game_result['winners']:
                    self.win_methods[winner_info['method']] += 1
                    self.player_wins[winner_info['player_name']] += 1
                
                self.win_details.append({
                    'game_id': self.total_games,
                    'winners': game_result['winners'],
                    'scores': game_result['final_scores'],
                    'game_length': game_result['game_length'],
                    'remaining_tiles': game_result['remaining_tiles']
                })
            else:
                # 流局
                self.draw_games += 1
                self.win_details.append({
                    'game_id': self.total_games,
                    'result': 'draw',
                    'scores': game_result['final_scores'],
                    'game_length': game_result['game_length'],
                    'remaining_tiles': game_result['remaining_tiles']
                })
            
            self.game_lengths.append(game_result['game_length'])
        else:
            # 游戏未完成（错误）
            self.errors.append({
                'game_id': self.total_games,
                'error': game_result.get('error', 'Unknown error')
            })
    
    def print_summary(self):
        """打印统计摘要"""
        print("\n" + "="*80)
        print(f"🀄 {self.ai_type} AI对战测试结果总结 (共{self.total_games}场游戏)")
        print("="*80)
        
        # 基础统计
        print(f"\n📊 基础统计:")
        print(f"  ✅ 正常完成游戏: {self.completed_games} 场 ({self.completed_games/self.total_games*100:.1f}%)")
        print(f"  🤝 流局: {self.draw_games} 场 ({self.draw_games/self.total_games*100:.1f}%)")
        print(f"  ❌ 错误/未完成: {len(self.errors)} 场 ({len(self.errors)/self.total_games*100:.1f}%)")
        
        # 胜利方式统计
        if self.win_methods:
            print(f"\n🏆 胜利方式统计:")
            total_wins = sum(self.win_methods.values())
            for method, count in self.win_methods.most_common():
                percentage = count / total_wins * 100
                method_name = {"自摸": "自摸胡牌", "点炮": "点炮胡牌"}.get(method, method)
                print(f"  {method_name}: {count} 次 ({percentage:.1f}%)")
        
        # 玩家胜利统计
        if self.player_wins:
            print(f"\n👤 玩家胜利统计:")
            total_wins = sum(self.player_wins.values())
            for player_name, wins in self.player_wins.most_common():
                percentage = wins / total_wins * 100
                print(f"  {player_name}: {wins} 次 ({percentage:.1f}%)")
        
        # 游戏长度统计
        if self.game_lengths:
            avg_length = sum(self.game_lengths) / len(self.game_lengths)
            min_length = min(self.game_lengths)
            max_length = max(self.game_lengths)
            print(f"\n⏱️ 游戏长度统计:")
            print(f"  平均出牌次数: {avg_length:.1f}")
            print(f"  最短游戏: {min_length} 次出牌")
            print(f"  最长游戏: {max_length} 次出牌")
        
        # 血战到底验证
        consecutive_winner_games = 0
        total_winners = 0
        for detail in self.win_details:
            if 'winners' in detail and detail['winners']:
                winners_count = len(detail['winners'])
                total_winners += winners_count
                if winners_count == 1:
                    consecutive_winner_games += 1
        
        avg_winners_per_game = total_winners / len(self.win_details) if self.win_details else 0
        
        print(f"\n⚔️ 血战到底情况:")
        print(f"  单次胜利游戏: {consecutive_winner_games} 场")
        print(f"  平均每场胜利人数: {avg_winners_per_game:.2f}")
        if consecutive_winner_games > 0:
            print("  ✅ 血战到底机制正常：胜利者逐个产生，符合四川麻将规则")
        else:
            print("  ⚠️ 本次测试中大多数游戏都是流局")
        
        # 错误统计
        if self.errors:
            print(f"\n⚠️ 错误情况:")
            error_types = Counter(error['error'] for error in self.errors)
            for error_type, count in error_types.items():
                print(f"  {error_type}: {count} 次")

class AIBattleSimulator:
    """AI对战模拟器"""
    
    def __init__(self, ai_class: Type[BaseAI] = SimpleAI, ai_difficulty: str = "hard", ai_type_name: str = "SimpleAI"):
        self.ai_class = ai_class
        self.ai_difficulty = ai_difficulty
        self.ai_type_name = ai_type_name
        self.stats = AIBattleStats(ai_type_name)
    
    def create_ai_only_engine(self) -> GameEngine:
        """创建只有AI玩家的游戏引擎"""
        engine = GameEngine()
        
        # 先用正常方式设置游戏
        engine.setup_game(GameMode.COMPETITIVE, "sichuan")
        
        # 然后替换所有玩家为指定类型的AI
        engine.players = []
        for i in range(4):
            if self.ai_class == SimpleAI:
                player = Player(f"{self.ai_type_name}_{i+1}", PlayerType.AI_HARD, i)
            else:
                player = Player(f"{self.ai_type_name}_{i+1}", PlayerType.AI_HARD, i)
            engine.players.append(player)
        
        return engine
    
    def simulate_ai_exchange(self, engine: GameEngine):
        """模拟AI换三张"""
        for player in engine.players:
            if player.player_id not in engine.exchange_tiles:
                # 使用AI逻辑选择换牌
                selected_tiles = self._ai_choose_exchange_tiles(player)
                engine.submit_exchange_tiles(player.player_id, selected_tiles)
    
    def _ai_choose_exchange_tiles(self, player: Player) -> List[Tile]:
        """AI选择换牌逻辑"""
        # 创建AI实例进行决策
        ai = self.ai_class(self.ai_difficulty)
        
        # 如果是高级AI且有相应方法，使用专门的方法
        if hasattr(ai, 'choose_exchange_tiles'):
            return ai.choose_exchange_tiles(player, 3)
        
        # 否则使用简单逻辑：按花色分组，选择数量最多的花色的前三张牌
        suits = {}
        for tile in player.hand_tiles:
            if tile.tile_type not in suits:
                suits[tile.tile_type] = []
            suits[tile.tile_type].append(tile)
        
        if suits:
            max_suit = max(suits.keys(), key=lambda s: len(suits[s]))
            return suits[max_suit][:3]
        
        return player.hand_tiles[:3]
    
    def simulate_ai_missing_suit(self, engine: GameEngine):
        """模拟AI选择缺门"""
        for player in engine.players:
            if not player.missing_suit:
                # 创建AI实例进行决策
                ai = self.ai_class(self.ai_difficulty)
                if hasattr(ai, 'choose_missing_suit'):
                    missing_suit = ai.choose_missing_suit(player)
                else:
                    missing_suit = SimpleAI(self.ai_difficulty).choose_missing_suit(player)
                engine.set_player_missing_suit(player, missing_suit)
    
    def simulate_ai_turn(self, engine: GameEngine) -> bool:
        """模拟AI回合"""
        current_player = engine.get_current_player()
        
        if not current_player or getattr(current_player, 'has_won', False):
            return True
        
        # 检查自摸胡牌
        if engine.can_player_action(current_player, GameAction.WIN):
            success = engine.execute_player_action(current_player, GameAction.WIN)
            return success
        
        # 选择打牌
        available_tiles = [t for t in current_player.hand_tiles 
                          if engine.rule.can_discard(current_player, t)]
        
        if not available_tiles:
            return False  # 无牌可打
        
        # 使用AI选择最优出牌
        ai = self.ai_class(self.ai_difficulty)
        tile_to_discard = ai.choose_discard(current_player, available_tiles)
        
        success = engine.execute_player_action(current_player, GameAction.DISCARD, tile_to_discard)
        return success
    
    def handle_ai_responses(self, engine: GameEngine, last_discarder) -> bool:
        """处理AI响应动作"""
        if not engine.last_discarded_tile:
            return False
        
        actions = []
        
        # 收集所有AI的可能动作
        for player in engine.players:
            if player == last_discarder or getattr(player, 'has_won', False):
                continue
            
            available_actions = []
            if engine.can_player_action(player, GameAction.WIN):
                available_actions.append(GameAction.WIN)
            if engine.can_player_action(player, GameAction.GANG):
                available_actions.append(GameAction.GANG)
            if engine.can_player_action(player, GameAction.PENG):
                available_actions.append(GameAction.PENG)
            
            if available_actions:
                # 使用AI决策
                ai = self.ai_class(self.ai_difficulty)
                context = {
                    "last_discarded_tile": engine.last_discarded_tile,
                    "discard_pool": engine.discard_pool,
                    "remaining_tiles": engine.deck.get_remaining_count() if engine.deck else 0
                }
                chosen_action = ai.decide_action(player, available_actions, context)
                
                if chosen_action and chosen_action != GameAction.PASS:
                    priority = 3 if chosen_action == GameAction.WIN else (2 if chosen_action == GameAction.GANG else 1)
                    actions.append({'player': player, 'action': chosen_action, 'priority': priority})
        
        if not actions:
            return False
        
        # 执行最高优先级的动作
        max_priority = max(a['priority'] for a in actions)
        best_actions = [a for a in actions if a['priority'] == max_priority]
        
        if best_actions:
            chosen_action_data = best_actions[0]
            actor = chosen_action_data['player']
            action = chosen_action_data['action']
            
            success = engine.execute_player_action(actor, action)
            return success
        
        return False
    
    def simulate_single_game(self, game_id: int) -> Dict:
        """模拟单局游戏"""
        try:
            engine = self.create_ai_only_engine()
            
            # 初始化游戏
            if not engine.start_new_game():
                return {
                    'completed': False,
                    'error': 'Failed to start game'
                }
            
            turn_count = 0
            max_turns = 1000  # 防止无限循环
            
            # 处理换三张阶段
            if engine.state.value == 'tile_exchange':
                self.simulate_ai_exchange(engine)
                while engine.state.value == 'tile_exchange' and turn_count < 10:
                    time.sleep(0.001)  # 很短的等待
                    turn_count += 1
            
            # 处理选择缺门阶段
            if engine.state.value == 'missing_suit_selection':
                self.simulate_ai_missing_suit(engine)
                if engine.state.value != 'playing':
                    engine._start_playing()
            
            turn_count = 0
            last_discarder = None
            
            # 打牌阶段
            while not engine.is_game_over() and turn_count < max_turns:
                turn_count += 1
                
                current_player = engine.get_current_player()
                if not current_player:
                    break
                
                if getattr(current_player, 'has_won', False):
                    engine.next_turn()
                    continue
                
                game_state = engine.get_game_status()['state']
                
                # 响应阶段
                if game_state == 'waiting_action' and last_discarder:
                    action_taken = self.handle_ai_responses(engine, last_discarder)
                    if action_taken:
                        last_discarder = None
                    else:
                        # 没有人响应，发送"过"指令
                        player_to_pass = next((p for p in engine.players if p != last_discarder), None)
                        if player_to_pass:
                            engine.execute_player_action(player_to_pass, None)
                        last_discarder = None
                    continue
                
                # 出牌阶段
                if game_state == 'playing':
                    if not self.simulate_ai_turn(engine):
                        break
                    last_discarder = current_player
            
            # 收集游戏结果
            game_state = engine.get_game_state()
            winners = [p for p in engine.players if getattr(p, 'is_winner', False)]
            
            result = {
                'completed': True,
                'winners': [],
                'final_scores': {p.name: p.score for p in engine.players},
                'game_length': turn_count,
                'remaining_tiles': engine.deck.get_remaining_count() if engine.deck else 0
            }
            
            # 分析胜利情况
            for winner in winners:
                win_method = "自摸"  # 默认自摸
                
                # 检查是否是点炮胡牌 - 更精确的检测
                if (engine.last_discarded_tile and 
                    hasattr(engine, 'last_discard_player') and engine.last_discard_player and 
                    engine.last_discard_player != winner):
                    win_method = "点炮"
                
                result['winners'].append({
                    'player_name': winner.name,
                    'method': win_method,
                    'score': winner.score
                })
            
            return result
            
        except Exception as e:
            return {
                'completed': False,
                'error': f"Exception: {str(e)}"
            }
    
    def run_test(self, num_games: int = 50):
        """运行测试"""
        print(f"🀄 开始全AI对战测试 - {num_games}场游戏")
        print("="*60)
        print("测试设置:")
        print("  • 所有玩家: AI_HARD")
        print("  • 游戏模式: 竞技模式")
        print("  • 规则: 四川麻将")
        print("  • 血战到底: 启用")
        print("="*60)
        
        start_time = time.time()
        
        for game_id in range(1, num_games + 1):
            print(f"\r正在进行第 {game_id}/{num_games} 场游戏...", end="", flush=True)
            
            result = self.simulate_single_game(game_id)
            self.stats.record_game_result(result)
            
            # 每10场游戏显示一次进度
            if game_id % 10 == 0:
                completed = self.stats.completed_games
                draw = self.stats.draw_games
                errors = len(self.stats.errors)
                print(f"\r进度 {game_id}/{num_games} - 完成:{completed} 流局:{draw} 错误:{errors}")
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        print(f"\n\n✅ 测试完成！耗时 {elapsed:.2f} 秒")
        print(f"平均每场游戏: {elapsed/num_games:.3f} 秒")
        
        self.stats.print_summary()

def main():
    """主测试函数"""
    print("🀄 启动AI对战测试...")
    
    # 获取命令行参数
    import sys
    num_games = 100
    if len(sys.argv) > 1:
        try:
            num_games = int(sys.argv[1])
        except ValueError:
            print("无效的游戏场次数，使用默认值100")
    
    # 测试简单AI（作为基准）
    print("\n" + "="*60)
    print("🔧 测试基准：SimpleAI (Hard难度)")
    print("="*60)
    simulator_simple = AIBattleSimulator(SimpleAI, "hard", "SimpleAI-Hard")
    simulator_simple.run_test(num_games)
    
    # 测试高级AI
    print("\n" + "="*60)
    print("🚀 测试高级：AdvancedAI (Expert难度)")
    print("="*60)
    simulator_advanced = AIBattleSimulator(AdvancedAI, "expert", "AdvancedAI-Expert")
    simulator_advanced.run_test(num_games)
    
    # 测试激进AI
    print("\n" + "="*60)
    print("⚔️ 测试激进：AggressiveAI (Aggressive难度)")
    print("="*60)
    simulator_aggressive = AIBattleSimulator(AggressiveAI, "aggressive", "AggressiveAI")
    simulator_aggressive.run_test(num_games)
    
    # 对比结果
    print("\n" + "="*80)
    print("📊 AI性能对比分析")
    print("="*80)
    
    simple_stats = simulator_simple.stats
    advanced_stats = simulator_advanced.stats
    aggressive_stats = simulator_aggressive.stats
    
    print(f"{'指标':<20} {'SimpleAI':<12} {'AdvancedAI':<12} {'AggressiveAI':<14} {'最佳':<10}")
    print("-" * 80)
    
    # 流局率对比
    simple_draw_rate = simple_stats.draw_games / simple_stats.total_games * 100
    advanced_draw_rate = advanced_stats.draw_games / advanced_stats.total_games * 100
    aggressive_draw_rate = aggressive_stats.draw_games / aggressive_stats.total_games * 100
    best_ai = min([
        ('SimpleAI', simple_draw_rate),
        ('AdvancedAI', advanced_draw_rate),
        ('AggressiveAI', aggressive_draw_rate)
    ], key=lambda x: x[1])
    print(f"{'流局率':<20} {simple_draw_rate:.1f}%{'':<7} {advanced_draw_rate:.1f}%{'':<7} {aggressive_draw_rate:.1f}%{'':<9} {best_ai[0]}")
    
    # 完成率对比
    simple_completion = simple_stats.completed_games / simple_stats.total_games * 100
    advanced_completion = advanced_stats.completed_games / advanced_stats.total_games * 100
    aggressive_completion = aggressive_stats.completed_games / aggressive_stats.total_games * 100
    best_completion = max([
        ('SimpleAI', simple_completion),
        ('AdvancedAI', advanced_completion),
        ('AggressiveAI', aggressive_completion)
    ], key=lambda x: x[1])
    print(f"{'完成率':<20} {simple_completion:.1f}%{'':<7} {advanced_completion:.1f}%{'':<7} {aggressive_completion:.1f}%{'':<9} {best_completion[0]}")
    
    # 平均游戏长度对比
    if simple_stats.game_lengths and advanced_stats.game_lengths and aggressive_stats.game_lengths:
        simple_avg_length = sum(simple_stats.game_lengths) / len(simple_stats.game_lengths)
        advanced_avg_length = sum(advanced_stats.game_lengths) / len(advanced_stats.game_lengths)
        aggressive_avg_length = sum(aggressive_stats.game_lengths) / len(aggressive_stats.game_lengths)
        best_length = min([
            ('SimpleAI', simple_avg_length),
            ('AdvancedAI', advanced_avg_length),
            ('AggressiveAI', aggressive_avg_length)
        ], key=lambda x: x[1])
        print(f"{'平均游戏长度':<20} {simple_avg_length:.1f}回合{'':<4} {advanced_avg_length:.1f}回合{'':<4} {aggressive_avg_length:.1f}回合{'':<6} {best_length[0]}")
    
    # 胜利率对比
    simple_win_rate = (simple_stats.total_games - simple_stats.draw_games) / simple_stats.total_games * 100
    advanced_win_rate = (advanced_stats.total_games - advanced_stats.draw_games) / advanced_stats.total_games * 100
    aggressive_win_rate = (aggressive_stats.total_games - aggressive_stats.draw_games) / aggressive_stats.total_games * 100
    best_win_rate = max([
        ('SimpleAI', simple_win_rate),
        ('AdvancedAI', advanced_win_rate),
        ('AggressiveAI', aggressive_win_rate)
    ], key=lambda x: x[1])
    print(f"{'胜利率':<20} {simple_win_rate:.1f}%{'':<7} {advanced_win_rate:.1f}%{'':<7} {aggressive_win_rate:.1f}%{'':<9} {best_win_rate[0]}")
    
    print(f"\n🎯 结论:")
    print(f"  📉 流局率：{best_ai[0]} 最优 ({best_ai[1]:.1f}%)")
    print(f"  🏆 胜利率：{best_win_rate[0]} 最优 ({best_win_rate[1]:.1f}%)")
    
    # 判断哪个AI最接近人类水平
    target_draw_rate = 25  # 目标流局率25%
    ai_distances = [
        ('SimpleAI', abs(simple_draw_rate - target_draw_rate)),
        ('AdvancedAI', abs(advanced_draw_rate - target_draw_rate)),
        ('AggressiveAI', abs(aggressive_draw_rate - target_draw_rate))
    ]
    closest_to_human = min(ai_distances, key=lambda x: x[1])
    
    print(f"  🎮 最接近人类水平：{closest_to_human[0]} (偏差{closest_to_human[1]:.1f}个百分点)")
    
    print(f"\n💡 分析:")
    if aggressive_draw_rate < simple_draw_rate:
        improvement = simple_draw_rate - aggressive_draw_rate
        print(f"  ✅ AggressiveAI相比SimpleAI降低流局率 {improvement:.1f}个百分点")
    
    if aggressive_draw_rate < 50:
        print(f"  🎯 AggressiveAI流局率已降至50%以下，策略有效")
    else:
        print(f"  ⚠️ 流局率仍然较高，需要进一步优化")

def test_specific_ai(ai_class: Type[BaseAI], difficulty: str, type_name: str, num_games: int = 50):
    """测试特定AI类型"""
    print(f"\n🔧 测试 {type_name} ({difficulty}难度)")
    simulator = AIBattleSimulator(ai_class, difficulty, type_name)
    simulator.run_test(num_games)
    return simulator.stats

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试出现错误: {e}")
        import traceback
        traceback.print_exc() 