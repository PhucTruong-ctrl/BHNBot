"""
Werewolf Day Phase Handler
Xử lý ban ngày - thảo luận và bỏ phiếu
"""
import asyncio
import discord
import random
from typing import Optional, Dict
from datetime import datetime
from .models import GameWerewolf, GamePlayer, Role, Faction, GameState, ROLE_METADATA


def log(msg: str):
    """Log message"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [DayPhase] {msg}")


class DayPhaseHandler:
    """Xử lý ban ngày"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def run_day_phase(
        self,
        game: GameWerewolf,
        channel: discord.TextChannel,
        night_result: Dict
    ) -> Optional[int]:
        """
        Chạy ban ngày hoàn chỉnh.
        Return: user_id của người bị treo cổ, hoặc None
        """
        # Unlock chat
        await self._unmute_channel(channel)
        
        # Thông báo bắt đầu ban ngày
        embed = discord.Embed(
            title=f"DAY #{game.day_count}",
            description=night_result.get("message", "Buoi sang den roi!"),
            color=discord.Color.gold()
        )
        day_msg = await channel.send(embed=embed)
        
        log(f"Day {game.day_count} started")
        
        # Giai đoạn 1: Thảo luận (DAY_DISCUSS)
        game.state = GameState.DAY_DISCUSS
        discuss_duration = game.day_discuss_duration
        for countdown in range(int(discuss_duration), 0, -5):
            try:
                remaining = f"{countdown}s" if countdown >= 5 else "Kết thúc..."
                embed = discord.Embed(
                    title=f"DAY #{game.day_count}",
                    description=f"**Thảo luận** - còn lại: **{remaining}**",
                    color=discord.Color.gold()
                )
                await day_msg.edit(embed=embed)
            except:
                pass
            await asyncio.sleep(5)
        
        # Giai đoạn 2: Bỏ phiếu (DAY_VOTE)
        game.state = GameState.DAY_VOTE
        lynched_player = await self._run_voting_phase(game, channel)
        
        return lynched_player
    
    async def _run_voting_phase(self, game: GameWerewolf, channel: discord.TextChannel) -> Optional[int]:
        """
        Chạy giai đoạn bỏ phiếu - hiển thị ở game channel
        Supports early skip when all players vote
        """
        # Tạo single compact embed với danh sách người chơi + countdown
        alive_players = game.get_alive_players()
        player_list = "\n".join([f"{i+1}. <@{p.user_id}>" for i, p in enumerate(alive_players)])
        
        # Gửi voting view ở channel chính
        votes = {}  # voter_id -> voted_id
        
        # Tạo voting view để gửi trong channel
        from .views import VoteSelectView
        view = VoteSelectView(
            game=game,
            voter=None,  # None means it's a group vote
            on_vote=self._create_group_vote_callback(votes, game),
            timeout=game.day_vote_duration
        )
        
        # Send consolidated vote embed
        embed = discord.Embed(
            title="🗳️ BỎ PHIẾU TREO CỔ",
            description=f"**Chọn người để treo cổ từ menu bên dưới**\n\n**Người chơi:**\n{player_list}",
            color=discord.Color.dark_grey()
        )
        embed.add_field(name="Thời gian", value=f"Còn lại: {game.day_vote_duration}s", inline=False)
        
        vote_msg = await channel.send(embed=embed, view=view)
        
        # Vote countdown with early exit when all voted
        vote_duration = game.day_vote_duration
        
        for countdown in range(int(vote_duration), 0, -10):
            try:
                remaining = f"{countdown}s"
                # Update only the countdown field
                embed = discord.Embed(
                    title="🗳️ BỎ PHIẾU TREO CỔ",
                    description=f"**Chọn người để treo cổ từ menu bên dưới**\n\n**Người chơi:**\n{player_list}",
                    color=discord.Color.dark_grey()
                )
                embed.add_field(name="Thời gian", value=f"Còn lại: {remaining}", inline=False)
                await vote_msg.edit(embed=embed)
            except:
                pass
            
            # Check if all alive players have voted - if so, skip remaining time
            if len(votes) == len(alive_players):
                log(f"VOTE_EARLY_EXIT: All {len(alive_players)} players voted, skipping remaining time")
                embed = discord.Embed(
                    title="🗳️ BỎ PHIẾU TREO CỔ",
                    description=f"✅ Tất cả mọi người đã bỏ phiếu, kết thúc sớm!\n\n**Người chơi:**\n{player_list}",
                    color=discord.Color.green()
                )
                embed.add_field(name="Trạng thái", value="Hoàn thành", inline=False)
                await vote_msg.edit(embed=embed)
                break
            
            await asyncio.sleep(10)
        
        # Tính toán kết quả vote
        vote_counts = {}
        for voter_id, voted_id in votes.items():
            if voter_id in game.players:
                voter = game.players[voter_id]
                # Check if Alpha Wolf (double vote)
                weight = 2 if voter.role == Role.WOLF_ALPHA else 1
                vote_counts[voted_id] = vote_counts.get(voted_id, 0) + weight
        
        # Tìm người được vote nhiều nhất
        if not vote_counts:
            embed = discord.Embed(
                title="KHÔNG CÓ PHIẾU",
                description="Mọi người đều im lặng nên không ai chết!",
                color=discord.Color.dark_grey()
            )
            await channel.send(embed=embed)
            return None
        
        # Handle ties - if multiple players have same max votes, it's a draw (no one dies)
        max_votes = max(vote_counts.values())
        tied_players = [player_id for player_id, count in vote_counts.items() if count == max_votes]
        
        # If tie (multiple players with max votes), no one dies
        if len(tied_players) > 1:
            tie_names = ", ".join([game.players[pid].username for pid in tied_players])
            log(f"VOTE_TIE_DRAW: {len(tied_players)} players tied with {max_votes} votes each: {tie_names} - NO ONE DIES")
            
            vote_display = "\n".join([
                f"• {game.players[p].username}: {v} phiếu"
                for p, v in sorted(vote_counts.items(), key=lambda x: x[1], reverse=True)
            ])
            
            embed = discord.Embed(
                title="HOA PHIEU",
                description=f"**Hòa phiếu!** {tie_names} đều nhận được {max_votes} phiếu\n"
                           f"Không ai bị treo cổ!\n\n"
                           f"Kết quả bỏ phiếu:\n{vote_display}",
                color=discord.Color.gold()
            )
            await channel.send(embed=embed)
            return None
        
        # Single winner - apply lynch
        lynched_id = tied_players[0]
        lynched_player = game.players.get(lynched_id)
        
        if not lynched_player:
            return None
        
        # Apply lynch
        lynched_player.is_alive = False
        game.dead_players.append(lynched_id)
        game.lynched_player = lynched_id
        
        # Mute the dead player individually
        try:
            guild = channel.guild
            member = guild.get_member(lynched_id)
            if member:
                # Create deny overwrite for this member
                overwrite = discord.PermissionOverwrite(send_messages=False)
                await channel.set_permissions(member, overwrite=overwrite)
                log(f"MUTE [{lynched_player.username}] Muted in #{channel.name}")
        except Exception as e:
            log(f"WARN DEAD_MUTE_ERROR [{lynched_player.username}]: {e}")
        
        # Thông báo kết quả
        vote_display = "\n".join([
            f"• {game.players[p].username}: {v} phiếu"
            for p, v in sorted(vote_counts.items(), key=lambda x: x[1], reverse=True)
        ])
        
        embed = discord.Embed(
            title="TREO CO",
            description=f"**{lynched_player.username}** bị treo cổ!\n\n"
                       f"Kết quả bỏ phiếu:\n{vote_display}",
            color=discord.Color.red()
        )
        await channel.send(embed=embed)
        
        log(f"OK LYNCH: {lynched_player.username} lynched with {vote_counts[lynched_id]} votes")
        
        return lynched_id
    
    def _create_vote_callback(self, votes_dict: Dict, voter_id: int):
        """Factory để tạo vote callback"""
        async def callback(interaction: discord.Interaction, voter: GamePlayer, voted_id: int):
            votes_dict[voter_id] = voted_id
            voted_player = voter.game.players.get(voted_id)
            vote_name = voted_player.username if voted_player else "?"
            await interaction.response.send_message(
                f"Bạn đã vote cho {vote_name}",
                ephemeral=True
            )
        return callback
    
    def _create_group_vote_callback(self, votes_dict: Dict, game: GameWerewolf):
        """Factory để tạo group vote callback - dùng cho channel voting"""
        async def callback(interaction: discord.Interaction, voter_id: int, voted_id: int):
            voter = game.players.get(voter_id)
            voted_player = game.players.get(voted_id)
            
            # Validate voter is alive
            if not voter or not voter.is_alive:
                log(f"FAIL VOTE_INVALID [Dead voter {voter.username if voter else 'Unknown'}] Attempt to vote")
                await interaction.response.send_message(
                    f"FAIL Ban da chet, khong the vote!",
                    ephemeral=True
                )
                return
            
            # Validate target exists and is alive
            if not voted_player or not voted_player.is_alive:
                log(f"FAIL VOTE_INVALID [{voter.username}] Tried to vote dead player {voted_player.username if voted_player else 'Unknown'}")
                await interaction.response.send_message(
                    f"Bầu thất bại! Mục tiêu đã chết rồi!",
                    ephemeral=True
                )
                return
            
            # Validate not voting for self
            if voter_id == voted_id:
                log(f"FAIL VOTE_INVALID [{voter.username}] Self-vote attempted")
                await interaction.response.send_message(
                    f"Bầu thất bại! Không được vote cho chính mình!",
                    ephemeral=True
                )
                return
            
            # Validate voter hasn't already voted
            if voter_id in votes_dict:
                old_vote = votes_dict[voter_id]
                old_vote_player = game.players.get(old_vote)
                log(f"FAIL VOTE_INVALID [{voter.username}] Already voted for {old_vote_player.username if old_vote_player else 'Unknown'}")
                await interaction.response.send_message(
                    f"Bầu thất bại! Bạn đã vote rồi!",
                    ephemeral=True
                )
                return
            
            votes_dict[voter_id] = voted_id
            vote_name = voted_player.username
            voter_name = voter.username
            
            log(f"OK VOTE [{voter_name}] → [{vote_name}]")
            
            await interaction.response.send_message(
                f"OK {voter_name} đã bầu {vote_name}",
                ephemeral=False  # Show to everyone in channel
            )
        return callback
    
    async def _unmute_channel(self, channel: discord.TextChannel):
        """Unlock chat"""
        try:
            overwrite = channel.overwrites_for(channel.guild.default_role)
            overwrite.send_messages = None
            await channel.set_permissions(channel.guild.default_role, overwrite=overwrite)
        except Exception as e:
            log(f"Error unmuting channel: {e}")
    
    async def display_status(self, game: GameWerewolf, channel: discord.TextChannel):
        """Hiển thị trạng thái game"""
        alive = game.get_alive_players()
        dead = game.get_dead_players()
        
        embed = discord.Embed(
            title="📊 TRẠNG THÁI GAME",
            color=discord.Color.blue()
        )
        embed.add_field(name="👥 Còn sống", value=str(len(alive)), inline=True)
        embed.add_field(name="💀 Chết", value=str(len(dead)), inline=True)
        embed.add_field(name="🌙 Đêm", value=str(game.night_count), inline=True)
        embed.add_field(name="☀️ Ngày", value=str(game.day_count), inline=True)
        
        alive_list = ", ".join([p.username for p in alive])
        embed.add_field(name="Còn sống:", value=alive_list or "Không ai", inline=False)
        
        if dead:
            dead_list = ", ".join([p.username for p in dead])
            embed.add_field(name="Đã chết:", value=dead_list, inline=False)
        
        await channel.send(embed=embed)
